"""
Phase 4: Security monitoring and anomaly detection
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from database import User, UserSession, LoginActivity, SecurityAudit
from utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """
    Monitor security events and detect suspicious patterns.
    """

    @staticmethod
    def check_for_threats(user_id: int, ip_address: str, db: Session) -> Dict[str, Any]:
        """
        Check for security threats for a user and IP.

        Args:
            user_id: User ID to check
            ip_address: Current IP address
            db: Database session

        Returns:
            Dictionary with threat assessment
        """
        threats = []
        risk_score = 0

        # Check for multiple failed logins
        failed_login_count = SecurityMonitor._check_failed_logins(user_id, db)
        if failed_login_count >= 5:
            threats.append(
                {
                    "type": "multiple_failed_logins",
                    "severity": "high",
                    "count": failed_login_count,
                    "message": f"{failed_login_count} failed login attempts detected",
                }
            )
            risk_score += 40

        # Check for login from new location
        is_new_location = SecurityMonitor._is_new_location(user_id, ip_address, db)
        if is_new_location:
            threats.append(
                {
                    "type": "new_location",
                    "severity": "medium",
                    "ip_address": ip_address,
                    "message": "Login from new IP address",
                }
            )
            risk_score += 20

        # Check for concurrent sessions
        concurrent_count = SecurityMonitor._check_concurrent_sessions(user_id, db)
        if concurrent_count >= 3:
            threats.append(
                {
                    "type": "multiple_sessions",
                    "severity": "medium",
                    "count": concurrent_count,
                    "message": f"{concurrent_count} active sessions detected",
                }
            )
            risk_score += 15

        # Check for rapid API key changes
        rapid_changes = SecurityMonitor._check_rapid_api_key_changes(user_id, db)
        if rapid_changes:
            threats.append(
                {
                    "type": "rapid_api_key_changes",
                    "severity": "high",
                    "count": rapid_changes,
                    "message": f"{rapid_changes} API key changes in short time",
                }
            )
            risk_score += 30

        return {
            "risk_score": min(risk_score, 100),
            "risk_level": SecurityMonitor._calculate_risk_level(risk_score),
            "threats": threats,
            "requires_action": risk_score >= 50,
        }

    @staticmethod
    def _check_failed_logins(user_id: int, db: Session, window_minutes: int = 30) -> int:
        """Check for failed login attempts in time window"""
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

        return (
            db.query(LoginActivity)
            .filter(
                LoginActivity.user_id == user_id,
                LoginActivity.action == "login",
                LoginActivity.success == False,
                LoginActivity.created_at >= window_start,
            )
            .count()
        )

    @staticmethod
    def _is_new_location(user_id: int, ip_address: str, db: Session, days: int = 30) -> bool:
        """Check if IP address is new for this user"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Check if this IP has been used before
        previous_use = (
            db.query(LoginActivity)
            .filter(
                LoginActivity.user_id == user_id,
                LoginActivity.ip_address == ip_address,
                LoginActivity.success == True,
                LoginActivity.created_at >= cutoff,
            )
            .first()
        )

        return previous_use is None

    @staticmethod
    def _check_concurrent_sessions(user_id: int, db: Session) -> int:
        """Count active sessions for user"""
        now = datetime.utcnow()

        return (
            db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.expires_at > now)
            .count()
        )

    @staticmethod
    def _check_rapid_api_key_changes(user_id: int, db: Session, window_minutes: int = 60) -> int:
        """Check for rapid API key changes"""
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

        return (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.user_id == user_id,
                SecurityAudit.event_type.in_(
                    ["api_key_created", "api_key_updated", "api_key_deleted"]
                ),
                SecurityAudit.created_at >= window_start,
            )
            .count()
        )

    @staticmethod
    def _calculate_risk_level(risk_score: int) -> str:
        """Calculate risk level from score"""
        if risk_score >= 70:
            return "high"
        elif risk_score >= 40:
            return "medium"
        else:
            return "low"

    @staticmethod
    def get_security_metrics(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Get comprehensive security metrics for a user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dictionary with security metrics
        """
        now = datetime.utcnow()
        last_30_days = now - timedelta(days=30)

        # Count active sessions
        active_sessions = (
            db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.expires_at > now)
            .count()
        )

        # Count failed logins
        failed_logins = (
            db.query(LoginActivity)
            .filter(
                LoginActivity.user_id == user_id,
                LoginActivity.action == "login",
                LoginActivity.success == False,
                LoginActivity.created_at >= last_30_days,
            )
            .count()
        )

        # Count successful logins
        successful_logins = (
            db.query(LoginActivity)
            .filter(
                LoginActivity.user_id == user_id,
                LoginActivity.action == "login",
                LoginActivity.success == True,
                LoginActivity.created_at >= last_30_days,
            )
            .count()
        )

        # Get unique login locations
        unique_ips = (
            db.query(LoginActivity.ip_address)
            .filter(
                LoginActivity.user_id == user_id,
                LoginActivity.action == "login",
                LoginActivity.success == True,
                LoginActivity.created_at >= last_30_days,
                LoginActivity.ip_address.isnot(None),
            )
            .distinct()
            .count()
        )

        # Count security events
        security_events = (
            db.query(SecurityAudit)
            .filter(SecurityAudit.user_id == user_id, SecurityAudit.created_at >= last_30_days)
            .count()
        )

        high_risk_events = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.user_id == user_id,
                SecurityAudit.risk_level == "high",
                SecurityAudit.created_at >= last_30_days,
            )
            .count()
        )

        return {
            "active_sessions": active_sessions,
            "failed_logins_30d": failed_logins,
            "successful_logins_30d": successful_logins,
            "unique_locations_30d": unique_ips,
            "security_events_30d": security_events,
            "high_risk_events_30d": high_risk_events,
            "last_checked": now.isoformat(),
        }

    @staticmethod
    def analyze_login_patterns(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Analyze user's login patterns for anomalies.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Analysis results
        """
        last_30_days = datetime.utcnow() - timedelta(days=30)

        # Get login activities
        logins = (
            db.query(LoginActivity)
            .filter(
                LoginActivity.user_id == user_id,
                LoginActivity.action == "login",
                LoginActivity.success == True,
                LoginActivity.created_at >= last_30_days,
            )
            .all()
        )

        if not logins:
            return {"pattern": "insufficient_data", "anomalies": []}

        # Analyze time patterns
        login_hours = [login.created_at.hour for login in logins]
        avg_hour = sum(login_hours) / len(login_hours) if login_hours else 0

        # Analyze location patterns
        ip_addresses = [login.ip_address for login in logins if login.ip_address]
        unique_ips = len(set(ip_addresses))

        # Analyze user agent patterns
        user_agents = [login.user_agent for login in logins if login.user_agent]
        unique_agents = len(set(user_agents))

        anomalies = []

        # Check for unusual number of locations
        if unique_ips > 5:
            anomalies.append(
                {
                    "type": "multiple_locations",
                    "value": unique_ips,
                    "message": f"Logged in from {unique_ips} different locations",
                }
            )

        # Check for unusual number of devices
        if unique_agents > 3:
            anomalies.append(
                {
                    "type": "multiple_devices",
                    "value": unique_agents,
                    "message": f"Logged in from {unique_agents} different devices",
                }
            )

        return {
            "pattern": "normal" if not anomalies else "anomalous",
            "total_logins": len(logins),
            "unique_locations": unique_ips,
            "unique_devices": unique_agents,
            "average_login_hour": avg_hour,
            "anomalies": anomalies,
        }

    @staticmethod
    def get_system_wide_threats(db: Session, hours: int = 24) -> Dict[str, Any]:
        """
        Get system-wide security threats.

        Args:
            db: Database session
            hours: Time window in hours

        Returns:
            System-wide threat analysis
        """
        window_start = datetime.utcnow() - timedelta(hours=hours)

        # Count high-risk events
        high_risk_count = (
            db.query(SecurityAudit)
            .filter(SecurityAudit.risk_level == "high", SecurityAudit.created_at >= window_start)
            .count()
        )

        # Get top threat IPs
        threat_ips = (
            db.query(SecurityAudit.ip_address, func.count(SecurityAudit.id).label("count"))
            .filter(
                SecurityAudit.risk_level == "high",
                SecurityAudit.created_at >= window_start,
                SecurityAudit.ip_address.isnot(None),
            )
            .group_by(SecurityAudit.ip_address)
            .order_by(func.count(SecurityAudit.id).desc())
            .limit(10)
            .all()
        )

        # Count failed login attempts
        failed_logins = (
            db.query(LoginActivity)
            .filter(
                LoginActivity.action == "login",
                LoginActivity.success == False,
                LoginActivity.created_at >= window_start,
            )
            .count()
        )

        return {
            "time_window_hours": hours,
            "high_risk_events": high_risk_count,
            "failed_login_attempts": failed_logins,
            "threat_ips": [{"ip_address": ip, "event_count": count} for ip, count in threat_ips],
            "requires_attention": high_risk_count > 10,
        }
