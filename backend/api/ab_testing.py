"""
A/B Testing API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import logging

from database import get_db, ABExperiment, ABAssignment, ABConversion, User
from utils.auth import get_current_user_optional

router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic models
class ExperimentResponse(BaseModel):
    """Response model for experiment data"""

    id: int
    name: str
    description: Optional[str]
    variants: List[str]
    traffic_allocation: Optional[Dict[str, float]]
    is_active: bool
    start_date: datetime
    end_date: Optional[datetime]

    class Config:
        from_attributes = True


class AssignmentRequest(BaseModel):
    """Request model for variant assignment"""

    experiment_name: str
    session_id: Optional[str] = None


class AssignmentResponse(BaseModel):
    """Response model for variant assignment"""

    experiment_name: str
    variant: str
    is_new_assignment: bool


class ConversionRequest(BaseModel):
    """Request model for tracking conversion"""

    experiment_name: str
    session_id: Optional[str] = None
    event_name: str
    properties: Optional[Dict[str, Any]] = None


class ConversionResponse(BaseModel):
    """Response model for conversion tracking"""

    success: bool
    message: str


class VariantStats(BaseModel):
    """Statistics for a single variant"""

    variant: str
    participants: int
    conversions: int
    conversion_rate: float
    improvement: Optional[float] = None


class ExperimentResults(BaseModel):
    """Experiment results with statistics"""

    experiment_name: str
    total_participants: int
    variants: List[VariantStats]
    statistical_significance: Optional[float] = None
    recommended_winner: Optional[str] = None


class CreateExperimentRequest(BaseModel):
    """Request model for creating experiment"""

    name: str
    description: Optional[str] = None
    variants: List[str]
    traffic_allocation: Optional[Dict[str, float]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Experiment name cannot be empty")
        return v.strip()

    @field_validator("variants")
    @classmethod
    def validate_variants(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError("Must have at least 2 variants")
        if len(set(v)) != len(v):
            raise ValueError("Variants must be unique")
        return v


# Helper functions
def get_or_create_session_id(request: Request) -> str:
    """Generate a session ID from client fingerprint"""
    # Use combination of IP and User-Agent to create consistent session ID
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    fingerprint = f"{ip}:{user_agent}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()[:64]


def assign_variant(experiment: ABExperiment, identifier: str) -> str:
    """Assign variant using consistent hashing"""
    # Use traffic allocation if specified, otherwise equal distribution
    variants = experiment.variants

    if experiment.traffic_allocation:
        # Weighted random assignment based on hash
        hash_value = int(hashlib.sha256(f"{experiment.name}:{identifier}".encode()).hexdigest(), 16)
        rand_value = (hash_value % 10000) / 10000.0  # 0.0 to 1.0

        cumulative = 0.0
        for variant in variants:
            weight = experiment.traffic_allocation.get(variant, 1.0 / len(variants))
            cumulative += weight
            if rand_value <= cumulative:
                return variant
        return variants[-1]  # Fallback
    else:
        # Equal distribution using hash
        hash_value = int(hashlib.sha256(f"{experiment.name}:{identifier}".encode()).hexdigest(), 16)
        return variants[hash_value % len(variants)]


def calculate_chi_squared(variant_stats: List[Dict]) -> Optional[float]:
    """Calculate chi-squared test for statistical significance"""
    if len(variant_stats) < 2:
        return None

    try:
        # Chi-squared test for independence
        total_participants = sum(v["participants"] for v in variant_stats)
        total_conversions = sum(v["conversions"] for v in variant_stats)

        if total_participants == 0 or total_conversions == 0:
            return None

        expected_rate = total_conversions / total_participants
        chi_squared = 0.0

        for v in variant_stats:
            expected_conversions = v["participants"] * expected_rate
            if expected_conversions > 0:
                chi_squared += (
                    (v["conversions"] - expected_conversions) ** 2
                ) / expected_conversions

        # Degrees of freedom = variants - 1
        df = len(variant_stats) - 1

        # Critical values for 95% confidence
        critical_values = {1: 3.841, 2: 5.991, 3: 7.815, 4: 9.488}
        critical = critical_values.get(df, 9.488)

        # Return p-value estimate (simplified)
        if chi_squared >= critical:
            return 0.95  # 95% confidence
        elif chi_squared >= critical * 0.7:
            return 0.90  # 90% confidence
        else:
            return 0.80  # Not significant

    except Exception as e:
        logger.error(f"Error calculating chi-squared: {e}")
        return None


# API Endpoints
@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(active_only: bool = True, db: Session = Depends(get_db)):
    """
    List all A/B testing experiments

    Args:
        active_only: If True, only return active experiments
        db: Database session

    Returns:
        List of experiments
    """
    try:
        query = db.query(ABExperiment)
        if active_only:
            query = query.filter(ABExperiment.is_active == True)

        experiments = query.order_by(ABExperiment.created_at.desc()).all()
        return experiments

    except Exception as e:
        logger.error(f"Error listing experiments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list experiments"
        )


@router.post("/assign", response_model=AssignmentResponse)
async def assign_variant_endpoint(
    request_data: AssignmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Assign user/session to a variant for an experiment

    Args:
        request_data: Assignment request with experiment name and optional session_id
        request: FastAPI request for session fingerprinting
        db: Database session
        current_user: Current user if authenticated

    Returns:
        Assigned variant and whether it's a new assignment
    """
    try:
        # Get experiment
        experiment = (
            db.query(ABExperiment)
            .filter(
                ABExperiment.name == request_data.experiment_name, ABExperiment.is_active == True
            )
            .first()
        )

        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active experiment '{request_data.experiment_name}' not found",
            )

        # Determine identifier (user_id or session_id)
        user_id = current_user.id if current_user else None
        session_id = request_data.session_id or get_or_create_session_id(request)

        # Check for existing assignment
        query = db.query(ABAssignment).filter(ABAssignment.experiment_id == experiment.id)

        if user_id:
            query = query.filter(ABAssignment.user_id == user_id)
        else:
            query = query.filter(ABAssignment.session_id == session_id)

        existing = query.first()

        if existing:
            return AssignmentResponse(
                experiment_name=experiment.name, variant=existing.variant, is_new_assignment=False
            )

        # Assign new variant
        identifier = str(user_id) if user_id else session_id
        variant = assign_variant(experiment, identifier)

        # Create assignment
        assignment = ABAssignment(
            experiment_id=experiment.id,
            user_id=user_id,
            session_id=session_id if not user_id else None,
            variant=variant,
        )

        db.add(assignment)
        db.commit()

        logger.info(
            f"Assigned variant '{variant}' for experiment '{experiment.name}' to {'user:' + str(user_id) if user_id else 'session:' + session_id}"
        )

        return AssignmentResponse(
            experiment_name=experiment.name, variant=variant, is_new_assignment=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning variant: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign variant"
        )


@router.post("/conversion", response_model=ConversionResponse)
async def track_conversion(
    request_data: ConversionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Track a conversion event for an experiment

    Args:
        request_data: Conversion request with experiment, event, and properties
        request: FastAPI request for session fingerprinting
        db: Database session
        current_user: Current user if authenticated

    Returns:
        Success response
    """
    try:
        # Get experiment
        experiment = (
            db.query(ABExperiment)
            .filter(
                ABExperiment.name == request_data.experiment_name, ABExperiment.is_active == True
            )
            .first()
        )

        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active experiment '{request_data.experiment_name}' not found",
            )

        # Find assignment
        user_id = current_user.id if current_user else None
        session_id = request_data.session_id or get_or_create_session_id(request)

        query = db.query(ABAssignment).filter(ABAssignment.experiment_id == experiment.id)

        if user_id:
            query = query.filter(ABAssignment.user_id == user_id)
        else:
            query = query.filter(ABAssignment.session_id == session_id)

        assignment = query.first()

        if not assignment:
            # User not assigned yet - auto-assign them
            identifier = str(user_id) if user_id else session_id
            variant = assign_variant(experiment, identifier)

            assignment = ABAssignment(
                experiment_id=experiment.id,
                user_id=user_id,
                session_id=session_id if not user_id else None,
                variant=variant,
            )
            db.add(assignment)
            db.flush()  # Get assignment ID

        # Create conversion event
        conversion = ABConversion(
            experiment_id=experiment.id,
            assignment_id=assignment.id,
            event_name=request_data.event_name,
            properties=request_data.properties,
        )

        db.add(conversion)
        db.commit()

        logger.info(
            f"Tracked conversion '{request_data.event_name}' for experiment '{experiment.name}'"
        )

        return ConversionResponse(
            success=True, message=f"Conversion '{request_data.event_name}' tracked successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking conversion: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to track conversion"
        )


@router.get("/results/{experiment_name}", response_model=ExperimentResults)
async def get_experiment_results(
    experiment_name: str, conversion_event: str = "signup_completed", db: Session = Depends(get_db)
):
    """
    Get results and statistics for an experiment

    Args:
        experiment_name: Name of the experiment
        conversion_event: Event name to measure (default: signup_completed)
        db: Database session

    Returns:
        Experiment results with statistics
    """
    try:
        # Get experiment
        experiment = db.query(ABExperiment).filter(ABExperiment.name == experiment_name).first()

        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment '{experiment_name}' not found",
            )

        # Get variant statistics
        variant_stats = []
        control_rate = None

        for variant in experiment.variants:
            # Count participants
            participants = (
                db.query(func.count(ABAssignment.id))
                .filter(
                    ABAssignment.experiment_id == experiment.id, ABAssignment.variant == variant
                )
                .scalar()
                or 0
            )

            # Count conversions
            conversions = (
                db.query(func.count(ABConversion.id))
                .join(ABAssignment)
                .filter(
                    ABAssignment.experiment_id == experiment.id,
                    ABAssignment.variant == variant,
                    ABConversion.event_name == conversion_event,
                )
                .scalar()
                or 0
            )

            conversion_rate = (conversions / participants * 100) if participants > 0 else 0.0

            # Calculate improvement vs control (variant A)
            improvement = None
            if variant == "A":
                control_rate = conversion_rate
            elif control_rate is not None and control_rate > 0:
                improvement = ((conversion_rate - control_rate) / control_rate) * 100

            variant_stats.append(
                VariantStats(
                    variant=variant,
                    participants=participants,
                    conversions=conversions,
                    conversion_rate=round(conversion_rate, 2),
                    improvement=round(improvement, 2) if improvement is not None else None,
                )
            )

        total_participants = sum(v.participants for v in variant_stats)

        # Calculate statistical significance
        stats_dict = [
            {"participants": v.participants, "conversions": v.conversions} for v in variant_stats
        ]
        significance = calculate_chi_squared(stats_dict)

        # Determine recommended winner (highest conversion rate with significance)
        recommended_winner = None
        if significance and significance >= 0.95 and total_participants >= 100:
            winner = max(variant_stats, key=lambda v: v.conversion_rate)
            if winner.conversion_rate > (control_rate or 0):
                recommended_winner = winner.variant

        return ExperimentResults(
            experiment_name=experiment.name,
            total_participants=total_participants,
            variants=variant_stats,
            statistical_significance=significance,
            recommended_winner=recommended_winner,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting experiment results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get experiment results",
        )


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(request_data: CreateExperimentRequest, db: Session = Depends(get_db)):
    """
    Create a new A/B testing experiment

    Args:
        request_data: Experiment details
        db: Database session

    Returns:
        Created experiment
    """
    try:
        # Check if experiment already exists
        existing = db.query(ABExperiment).filter(ABExperiment.name == request_data.name).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Experiment '{request_data.name}' already exists",
            )

        # Validate traffic allocation if provided
        if request_data.traffic_allocation:
            total_weight = sum(request_data.traffic_allocation.values())
            if not (0.99 <= total_weight <= 1.01):  # Allow small floating point errors
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Traffic allocation weights must sum to 1.0",
                )

        # Create experiment
        experiment = ABExperiment(
            name=request_data.name,
            description=request_data.description,
            variants=request_data.variants,
            traffic_allocation=request_data.traffic_allocation,
            is_active=True,
        )

        db.add(experiment)
        db.commit()
        db.refresh(experiment)

        logger.info(f"Created experiment: {experiment.name}")

        return experiment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating experiment: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create experiment"
        )


@router.patch("/experiments/{experiment_name}/toggle")
async def toggle_experiment(experiment_name: str, db: Session = Depends(get_db)):
    """
    Toggle experiment active status

    Args:
        experiment_name: Name of the experiment
        db: Database session

    Returns:
        Updated experiment status
    """
    try:
        experiment = db.query(ABExperiment).filter(ABExperiment.name == experiment_name).first()

        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment '{experiment_name}' not found",
            )

        experiment.is_active = not experiment.is_active
        experiment.updated_at = datetime.utcnow()

        if not experiment.is_active:
            experiment.end_date = datetime.utcnow()

        db.commit()

        logger.info(
            f"Toggled experiment '{experiment_name}' to {'active' if experiment.is_active else 'inactive'}"
        )

        return {
            "success": True,
            "experiment_name": experiment.name,
            "is_active": experiment.is_active,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling experiment: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to toggle experiment"
        )
