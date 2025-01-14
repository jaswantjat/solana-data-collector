"""Alert management system"""
import logging
from typing import Dict, Any, List
from datetime import datetime
import asyncio
from dataclasses import dataclass

from ..database.models import Alert
from ..database.connection import db_manager
from ..events.event_manager import event_manager

logger = logging.getLogger(__name__)

@dataclass
class AlertConfig:
    """Alert configuration"""
    enabled: bool = True
    min_severity: float = 0.5
    channels: List[str] = None
    cooldown: int = 300  # seconds

class AlertManager:
    """Manages system alerts and notifications"""

    def __init__(self, config: AlertConfig = None):
        self.config = config or AlertConfig()
        self.alert_cache = {}
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup event handlers"""
        event_manager.on("suspicious_activity", self.handle_suspicious_activity)
        event_manager.on("price_alert", self.handle_price_alert)
        event_manager.on("system_error", self.handle_system_error)

    async def handle_suspicious_activity(self, event: Dict[str, Any]):
        """Handle suspicious activity alerts"""
        try:
            if not self.config.enabled:
                return

            severity = event.get("severity", 0.0)
            if severity < self.config.min_severity:
                return

            # Check cooldown
            token_id = event.get("token_id")
            if token_id in self.alert_cache:
                last_alert = self.alert_cache[token_id]
                if (datetime.utcnow() - last_alert).total_seconds() < self.config.cooldown:
                    logger.debug(f"Alert for token {token_id} is in cooldown")
                    return

            # Create alert
            alert = Alert(
                token_id=token_id,
                alert_type="suspicious_activity",
                severity=severity,
                details=event.get("details", {}),
                timestamp=datetime.utcnow()
            )

            # Save to database
            async with db_manager.session() as session:
                session.add(alert)
                await session.commit()

            # Update cache
            self.alert_cache[token_id] = datetime.utcnow()

            # Emit notification event
            await event_manager.emit("notification", {
                "type": "alert",
                "data": alert.to_dict()
            })

        except Exception as e:
            logger.error(f"Error handling suspicious activity: {str(e)}")

    async def handle_price_alert(self, event: Dict[str, Any]):
        """Handle price alerts"""
        try:
            if not self.config.enabled:
                return

            severity = event.get("severity", 0.0)
            if severity < self.config.min_severity:
                return

            token_id = event.get("token_id")
            alert = Alert(
                token_id=token_id,
                alert_type="price_change",
                severity=severity,
                details=event.get("details", {}),
                timestamp=datetime.utcnow()
            )

            # Save to database
            async with db_manager.session() as session:
                session.add(alert)
                await session.commit()

            # Emit notification event
            await event_manager.emit("notification", {
                "type": "alert",
                "data": alert.to_dict()
            })

        except Exception as e:
            logger.error(f"Error handling price alert: {str(e)}")

    async def handle_system_error(self, event: Dict[str, Any]):
        """Handle system error alerts"""
        try:
            if not self.config.enabled:
                return

            # System errors are always high severity
            alert = Alert(
                token_id=None,
                alert_type="system_error",
                severity=1.0,
                details=event.get("details", {}),
                timestamp=datetime.utcnow()
            )

            # Save to database
            async with db_manager.session() as session:
                session.add(alert)
                await session.commit()

            # Emit notification event
            await event_manager.emit("notification", {
                "type": "alert",
                "data": alert.to_dict()
            })

        except Exception as e:
            logger.error(f"Error handling system error: {str(e)}")

    async def get_alerts(
        self,
        alert_type: str = None,
        min_severity: float = None,
        start_time: datetime = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get alerts with filtering"""
        try:
            query = "SELECT * FROM alerts WHERE 1=1"
            params = {}

            if alert_type:
                query += " AND alert_type = :alert_type"
                params["alert_type"] = alert_type

            if min_severity is not None:
                query += " AND severity >= :min_severity"
                params["min_severity"] = min_severity

            if start_time:
                query += " AND timestamp >= :start_time"
                params["start_time"] = start_time

            query += " ORDER BY timestamp DESC LIMIT :limit"
            params["limit"] = limit

            async with db_manager.session() as session:
                result = await session.execute(query, params)
                alerts = result.fetchall()

            return [Alert.from_row(row).to_dict() for row in alerts]

        except Exception as e:
            logger.error(f"Error getting alerts: {str(e)}")
            return []

    def start(self):
        """Start the alert manager"""
        logger.info("Alert manager started")

    async def shutdown(self):
        """Shutdown the alert manager"""
        logger.info("Alert manager shutting down")
