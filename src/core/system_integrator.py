"""System integrator for managing all components"""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

from src.events.event_manager import event_manager
from src.notifications.notification_manager import NotificationManager
from src.analysis.token_analysis import TokenAnalyzer
from src.analysis.holder_analysis import HolderAnalyzer
from src.analysis.deployer_analysis import DeployerAnalyzer
from src.monitoring.token_monitor import TokenMonitor
from src.database.connection import db_manager

logger = logging.getLogger(__name__)

class SystemIntegrator:
    """Integrates and manages all system components"""
    def __init__(self):
        self.notification_manager = NotificationManager()
        self.token_monitor = None
        self.token_analyzer = None
        self.holder_analyzer = None
        self.deployer_analyzer = None
        self.is_initialized = False
        self.is_running = False
        self.background_tasks = []

    async def initialize(self) -> None:
        """Initialize all system components"""
        if self.is_initialized:
            return

        try:
            # Initialize analyzers
            self.token_analyzer = TokenAnalyzer()
            self.holder_analyzer = HolderAnalyzer()
            self.deployer_analyzer = DeployerAnalyzer()
            
            # Initialize token monitor
            self.token_monitor = TokenMonitor(
                token_analyzer=self.token_analyzer,
                holder_analyzer=self.holder_analyzer,
                deployer_analyzer=self.deployer_analyzer
            )

            # Set up event handlers
            event_manager.on("token_updated", self._handle_token_update)
            event_manager.on("holder_updated", self._handle_holder_update)
            event_manager.on("suspicious_activity", self._handle_suspicious_activity)
            event_manager.on("system_error", self._handle_system_error)

            self.is_initialized = True
            await event_manager.emit("system_initialized", {
                "timestamp": datetime.now().isoformat(),
                "components": [
                    "token_monitor",
                    "token_analyzer",
                    "holder_analyzer",
                    "deployer_analyzer"
                ]
            })

        except Exception as e:
            logger.error(f"Error initializing system: {str(e)}")
            raise

    async def start(self) -> None:
        """Start system operations"""
        if not self.is_initialized:
            await self.initialize()

        if self.is_running:
            return

        try:
            # Start token monitoring
            monitor_task = asyncio.create_task(self.token_monitor.start())
            self.background_tasks.append(monitor_task)

            self.is_running = True
            await event_manager.emit("system_started", {
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error starting system: {str(e)}")
            raise

    async def shutdown(self) -> None:
        """Shutdown system operations"""
        if not self.is_running:
            return

        try:
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self.background_tasks.clear()
            self.is_running = False

            # Clear event handlers
            event_manager.clear_handlers()

            await event_manager.emit("system_shutdown", {
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            raise

    async def _handle_token_update(self, event: Dict) -> None:
        """Handle token update events"""
        try:
            await self.notification_manager.process_alert({
                "title": "Token Update",
                "description": f"Token {event.data['address']} updated",
                "fields": event.data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling token update: {str(e)}")

    async def _handle_holder_update(self, event: Dict) -> None:
        """Handle holder update events"""
        try:
            await self.notification_manager.process_alert({
                "title": "Holder Update",
                "description": f"Holder {event.data['address']} updated",
                "fields": event.data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling holder update: {str(e)}")

    async def _handle_suspicious_activity(self, event: Dict) -> None:
        """Handle suspicious activity events"""
        try:
            await self.notification_manager.process_alert({
                "title": "Suspicious Activity Detected",
                "description": event.data.get("description", ""),
                "fields": event.data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling suspicious activity: {str(e)}")

    async def _handle_system_error(self, event: Dict) -> None:
        """Handle system error events"""
        try:
            error_data = event.data
            needs_recovery = error_data.get("needs_recovery", False)

            if needs_recovery:
                await self._attempt_recovery(error_data)
            else:
                await self.notification_manager.process_alert({
                    "title": "System Error",
                    "description": error_data.get("error", "Unknown error"),
                    "fields": error_data,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Error handling system error: {str(e)}")

    async def _attempt_recovery(self, error_data: Dict) -> None:
        """Attempt system recovery"""
        try:
            component = error_data.get("component")
            if component == "token_monitor":
                await self.token_monitor.restart()
            elif component == "database":
                await db_manager.reconnect()

            await event_manager.emit("recovery_complete", {
                "component": component,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error during recovery attempt: {str(e)}")
            raise

# Create singleton instance
system = SystemIntegrator()
