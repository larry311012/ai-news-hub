"""
Analytics API endpoints for tracking user behavior and conversion funnel
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import hashlib

from database import get_db, User

router = APIRouter()


# Request/Response Models
class AnalyticsEvent(BaseModel):
    """Analytics event model"""

    event_name: str = Field(..., max_length=100)
    properties: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


class AnalyticsEventResponse(BaseModel):
    """Analytics event response"""

    event_id: int
    message: str


class FunnelMetrics(BaseModel):
    """Conversion funnel metrics"""

    total_visitors: int
    guest_browsing: int
    auth_modal_shown: int
    signup_started: int
    signup_completed: int
    onboarding_completed: int
    first_post_generated: int
    conversion_rates: Dict[str, str]


class EventSummary(BaseModel):
    """Event summary statistics"""

    event_name: str
    count: int
    unique_users: int
    unique_sessions: int


class AnalyticsSummary(BaseModel):
    """Key analytics summary"""

    total_events: int
    total_users: int
    total_sessions: int
    date_range: Dict[str, str]
    top_events: List[EventSummary]


# Helper functions
def anonymize_ip(ip_address: str) -> str:
    """Anonymize IP address by masking last octet (GDPR compliant)"""
    if not ip_address:
        return None

    parts = ip_address.split(".")
    if len(parts) == 4:
        # IPv4: Mask last octet
        parts[-1] = "0"
        return ".".join(parts)
    else:
        # IPv6: Hash it
        return hashlib.sha256(ip_address.encode()).hexdigest()[:16]


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for proxy headers first
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct connection
    if request.client:
        return request.client.host

    return "unknown"


def check_dnt(request: Request) -> bool:
    """Check if Do Not Track is enabled"""
    dnt = request.headers.get("DNT") or request.headers.get("dnt")
    return dnt == "1"


def get_current_user_id(request: Request, db: Session) -> Optional[int]:
    """Get current user ID from auth token if available"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.replace("Bearer ", "")

        # Query session to get user_id
        result = db.execute(
            text("SELECT user_id FROM sessions WHERE token = :token AND expires_at > :now"),
            {"token": token, "now": datetime.utcnow()},
        ).fetchone()

        if result:
            return result[0]

        return None
    except Exception as e:
        print(f"Error getting user ID: {e}")
        return None


# API Endpoints
@router.post("/events", response_model=AnalyticsEventResponse)
async def track_event(event: AnalyticsEvent, request: Request, db: Session = Depends(get_db)):
    """
    Track an analytics event
    """
    try:
        # Check DNT header
        if check_dnt(request):
            # User has Do Not Track enabled - still log event but don't store identifying info
            return AnalyticsEventResponse(event_id=0, message="Event received (DNT respected)")

        # Get user ID if authenticated
        user_id = get_current_user_id(request, db)

        # Get session ID from properties or generate anonymous one
        session_id = None
        if event.properties and "session_id" in event.properties:
            session_id = event.properties["session_id"]

        # Get request metadata
        user_agent = request.headers.get("User-Agent", "")
        ip_address = anonymize_ip(get_client_ip(request))
        referrer = request.headers.get("Referer", "")
        page_url = event.properties.get("page_url", "") if event.properties else ""

        # Convert properties to JSON
        properties_json = json.dumps(event.properties) if event.properties else None

        # Insert event
        result = db.execute(
            text(
                """
                INSERT INTO analytics_events
                (event_name, user_id, session_id, properties, user_agent, ip_address, referrer, page_url, created_at)
                VALUES (:event_name, :user_id, :session_id, :properties, :user_agent, :ip_address, :referrer, :page_url, :created_at)
            """
            ),
            {
                "event_name": event.event_name,
                "user_id": user_id,
                "session_id": session_id,
                "properties": properties_json,
                "user_agent": user_agent[:500] if user_agent else None,
                "ip_address": ip_address[:45] if ip_address else None,
                "referrer": referrer[:500] if referrer else None,
                "page_url": page_url[:500] if page_url else None,
                "created_at": event.timestamp or datetime.utcnow(),
            },
        )
        db.commit()

        event_id = result.lastrowid

        return AnalyticsEventResponse(event_id=event_id, message="Event tracked successfully")

    except Exception as e:
        db.rollback()
        print(f"Error tracking event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")


@router.get("/funnel", response_model=FunnelMetrics)
async def get_funnel_metrics(
    start_date: Optional[str] = None, end_date: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    Get conversion funnel metrics
    """
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        else:
            start = datetime.utcnow() - timedelta(days=30)

        if end_date:
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        else:
            end = datetime.utcnow()

        # Count unique sessions/users for each funnel stage
        def count_events(event_name: str) -> int:
            result = db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT COALESCE(session_id, CAST(user_id AS TEXT), ip_address))
                    FROM analytics_events
                    WHERE event_name = :event_name
                    AND created_at BETWEEN :start AND :end
                """
                ),
                {"event_name": event_name, "start": start, "end": end},
            ).fetchone()
            return result[0] if result else 0

        # Get metrics for each stage
        total_visitors = count_events("page_view")
        guest_browsing = total_visitors  # All page views are guest browsing initially
        auth_modal_shown = count_events("auth_modal_shown")
        signup_started = count_events("signup_started")
        signup_completed = count_events("signup_completed")
        onboarding_completed = count_events("onboarding_completed")
        first_post_generated = count_events("post_generation_completed")

        # Calculate conversion rates
        def calc_rate(numerator: int, denominator: int) -> str:
            if denominator == 0:
                return "0%"
            return f"{(numerator / denominator * 100):.1f}%"

        conversion_rates = {
            "visitor_to_auth_modal": calc_rate(auth_modal_shown, total_visitors),
            "auth_modal_to_signup": calc_rate(signup_started, auth_modal_shown),
            "signup_to_completion": calc_rate(signup_completed, signup_started),
            "signup_to_onboarding": calc_rate(onboarding_completed, signup_completed),
            "onboarding_to_first_post": calc_rate(first_post_generated, onboarding_completed),
            "visitor_to_signup": calc_rate(signup_completed, total_visitors),
            "visitor_to_first_post": calc_rate(first_post_generated, total_visitors),
        }

        return FunnelMetrics(
            total_visitors=total_visitors,
            guest_browsing=guest_browsing,
            auth_modal_shown=auth_modal_shown,
            signup_started=signup_started,
            signup_completed=signup_completed,
            onboarding_completed=onboarding_completed,
            first_post_generated=first_post_generated,
            conversion_rates=conversion_rates,
        )

    except Exception as e:
        print(f"Error getting funnel metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get funnel metrics: {str(e)}")


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    start_date: Optional[str] = None, end_date: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    Get analytics summary with key metrics
    """
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        else:
            start = datetime.utcnow() - timedelta(days=30)

        if end_date:
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        else:
            end = datetime.utcnow()

        # Total events
        result = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM analytics_events
                WHERE created_at BETWEEN :start AND :end
            """
            ),
            {"start": start, "end": end},
        ).fetchone()
        total_events = result[0] if result else 0

        # Unique users
        result = db.execute(
            text(
                """
                SELECT COUNT(DISTINCT user_id)
                FROM analytics_events
                WHERE user_id IS NOT NULL
                AND created_at BETWEEN :start AND :end
            """
            ),
            {"start": start, "end": end},
        ).fetchone()
        total_users = result[0] if result else 0

        # Unique sessions
        result = db.execute(
            text(
                """
                SELECT COUNT(DISTINCT session_id)
                FROM analytics_events
                WHERE session_id IS NOT NULL
                AND created_at BETWEEN :start AND :end
            """
            ),
            {"start": start, "end": end},
        ).fetchone()
        total_sessions = result[0] if result else 0

        # Top events
        results = db.execute(
            text(
                """
                SELECT
                    event_name,
                    COUNT(*) as count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT session_id) as unique_sessions
                FROM analytics_events
                WHERE created_at BETWEEN :start AND :end
                GROUP BY event_name
                ORDER BY count DESC
                LIMIT 10
            """
            ),
            {"start": start, "end": end},
        ).fetchall()

        top_events = [
            EventSummary(
                event_name=row[0],
                count=row[1],
                unique_users=row[2] or 0,
                unique_sessions=row[3] or 0,
            )
            for row in results
        ]

        return AnalyticsSummary(
            total_events=total_events,
            total_users=total_users,
            total_sessions=total_sessions,
            date_range={"start": start.isoformat(), "end": end.isoformat()},
            top_events=top_events,
        )

    except Exception as e:
        print(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics summary: {str(e)}")


@router.get("/events")
async def get_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_name: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get analytics events with optional filtering
    """
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        else:
            start = datetime.utcnow() - timedelta(days=7)

        if end_date:
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        else:
            end = datetime.utcnow()

        # Build query
        query = """
            SELECT
                id,
                event_name,
                user_id,
                session_id,
                properties,
                user_agent,
                referrer,
                page_url,
                created_at
            FROM analytics_events
            WHERE created_at BETWEEN :start AND :end
        """
        params = {"start": start, "end": end, "limit": limit}

        if event_name:
            query += " AND event_name = :event_name"
            params["event_name"] = event_name

        query += " ORDER BY created_at DESC LIMIT :limit"

        results = db.execute(text(query), params).fetchall()

        events = []
        for row in results:
            properties = json.loads(row[4]) if row[4] else {}
            events.append(
                {
                    "id": row[0],
                    "event_name": row[1],
                    "user_id": row[2],
                    "session_id": row[3],
                    "properties": properties,
                    "user_agent": row[5],
                    "referrer": row[6],
                    "page_url": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                }
            )

        return {
            "events": events,
            "count": len(events),
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        }

    except Exception as e:
        print(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get events: {str(e)}")


@router.get("/test")
async def test_analytics():
    """Test endpoint to verify analytics API is working"""
    return {
        "status": "ok",
        "message": "Analytics API is operational",
        "timestamp": datetime.utcnow().isoformat(),
    }
