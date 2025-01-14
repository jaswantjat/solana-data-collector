"""Token monitoring module for tracking token metrics and changes"""
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os

from src.integrations.bitquery import BitqueryAPI
from src.integrations.helius import HeliusAPI
from src.integrations.shyft import ShyftAPI
from src.events.event_manager import event_manager
from src.test.mock_data import get_mock_token, should_use_mock_data

logger = logging.getLogger(__name__)

class TokenMonitor:
    """Monitors token metrics and changes"""
    def __init__(self, token_analyzer=None, holder_analyzer=None, deployer_analyzer=None, activity_analyzer=None):
        self.bitquery = BitqueryAPI()
        self.helius = HeliusAPI()
        self.shyft = ShyftAPI()
        self.token_analyzer = token_analyzer
        self.holder_analyzer = holder_analyzer
        self.deployer_analyzer = deployer_analyzer
        self.activity_analyzer = activity_analyzer
        self.is_running = False
        self.is_shutdown = False
        self.is_initialized = False
        self.logger = logging.getLogger(__name__)
        self._test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
        self.use_mock = should_use_mock_data()
        self.tasks = []
        self._initialization_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the token monitor"""
        if self.is_initialized:
            return

        async with self._initialization_lock:
            if self.is_initialized:  # Double-check pattern
                return

            try:
                # Initialize APIs if not in mock mode
                if not self.use_mock:
                    await asyncio.gather(
                        self.bitquery.initialize(),
                        self.helius.initialize(),
                        self.shyft.initialize()
                    )

                # Initialize analyzers
                init_tasks = []
                for analyzer in [self.token_analyzer, self.holder_analyzer, 
                               self.deployer_analyzer, self.activity_analyzer]:
                    if analyzer and hasattr(analyzer, 'initialize'):
                        init_tasks.append(analyzer.initialize())

                if init_tasks:
                    await asyncio.gather(*init_tasks)

                self.is_initialized = True
                self.logger.info("Token monitor initialized successfully")

            except Exception as e:
                self.logger.error(f"Failed to initialize token monitor: {str(e)}")
                raise

    async def check_health(self) -> Dict:
        """Check health of token monitor and dependencies"""
        try:
            if self.is_shutdown:
                return {
                    "status": "shutdown",
                    "timestamp": datetime.now().isoformat(),
                    "mock_mode": self.use_mock
                }

            if not self.is_initialized:
                return {
                    "status": "not_initialized",
                    "timestamp": datetime.now().isoformat(),
                    "mock_mode": self.use_mock
                }

            if self.use_mock:
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "apis_healthy": True,
                    "mock_mode": True
                }

            # Check API connections
            apis_healthy = all([
                await self.bitquery.check_health(),
                await self.helius.check_health(),
                await self.shyft.check_health()
            ])
            
            return {
                "status": "healthy" if apis_healthy else "degraded",
                "timestamp": datetime.now().isoformat(),
                "apis_healthy": apis_healthy,
                "mock_mode": False
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "mock_mode": self.use_mock
            }
            
    async def shutdown(self) -> None:
        """Shutdown token monitor and cleanup resources"""
        if self.is_shutdown:
            return

        self.is_running = False
        self.is_shutdown = True
        
        try:
            # Cancel all tasks
            for task in self.tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            self.tasks.clear()
            
            # Shutdown analyzers
            shutdown_tasks = []
            for analyzer in [self.token_analyzer, self.holder_analyzer, 
                           self.deployer_analyzer, self.activity_analyzer]:
                if analyzer and hasattr(analyzer, 'shutdown'):
                    shutdown_tasks.append(analyzer.shutdown())

            if shutdown_tasks:
                await asyncio.gather(*shutdown_tasks, return_exceptions=True)

            if not self.use_mock:
                # Close API connections
                await asyncio.gather(
                    self.bitquery.close(),
                    self.helius.close(),
                    self.shyft.close(),
                    return_exceptions=True
                )
                
            # Emit shutdown event
            await event_manager.emit("token_monitor_shutdown", {
                "timestamp": datetime.now().isoformat(),
                "status": "shutdown"
            })
            
            self.is_initialized = False
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
            raise

    async def start(self) -> None:
        """Start token monitoring"""
        if self.is_running or self.is_shutdown:
            return

        if not self.is_initialized:
            await self.initialize()

        self.is_running = True
        self.is_shutdown = False

        # Register event handlers
        event_manager.on("new_token_detected", self._handle_new_token)
        event_manager.on("transaction_detected", self._handle_transaction)
        event_manager.on("price_alert", self._handle_price_alert)

        # Start monitoring loop
        task = asyncio.create_task(self._monitoring_loop())
        self.tasks.append(task)
        
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Monitor new token launches
                await self.monitor_new_launches()
                
                # In test mode, only run once
                if self._test_mode:
                    self.is_running = False
                    break
                    
                # Wait before next iteration
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                self.logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                if self._test_mode:
                    break
                await asyncio.sleep(5)

    async def _handle_new_token(self, event) -> None:
        """Handle new token detection event"""
        try:
            token = event.data
            token_address = token["address"]

            # Run token analysis first
            if self.token_analyzer:
                try:
                    analysis_result = await self.token_analyzer.analyze_token(token)
                    await event_manager.emit("token_analysis_complete", analysis_result)
                except Exception as e:
                    self.logger.error(f"Analysis failed for {token_address}: {str(e)}")

            # Run other analysis tasks concurrently
            analysis_tasks = []
            if self.holder_analyzer:
                analysis_tasks.append(self.holder_analyzer.analyze_holders(token_address))
            if self.deployer_analyzer:
                analysis_tasks.append(self.deployer_analyzer.analyze_deployer(token_address))

            # Wait for all analysis tasks to complete
            if analysis_tasks:
                results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        self.logger.error(f"Analysis failed for {token_address}: {str(result)}")
                    else:
                        await event_manager.emit("analysis_complete", result)

        except Exception as e:
            self.logger.error(f"Error handling new token {token_address}: {str(e)}")

    async def _handle_transaction(self, event) -> None:
        """Handle new transaction event"""
        try:
            tx = event.data
            token_address = tx["token_address"]

            # Analyze transaction for suspicious activity
            if self.activity_analyzer:
                analysis = await self.activity_analyzer.analyze_activity(token_address)
                if any(analysis["risk_factors"].values()):
                    await event_manager.emit("suspicious_activity", {
                        "token_address": token_address,
                        "activity_type": "high_risk_score",
                        "risk_level": "high",
                        "risk_factors": analysis["risk_factors"],
                        "timestamp": datetime.now().isoformat()
                    })

        except Exception as e:
            self.logger.error(f"Error handling transaction: {str(e)}")

    async def _handle_price_alert(self, event) -> None:
        """Handle price alert event"""
        try:
            price_data = event.data
            token_address = price_data["token_address"]

            # Run price analysis
            if self.token_analyzer:
                analysis = await self.token_analyzer.analyze_price_movement(token_address, price_data)
                if analysis["metrics"]["volatility"] > 0.1:  # 10% change
                    await event_manager.emit("alert_generated", {
                        "token_address": token_address,
                        "alert_type": "price_volatility",
                        "severity": "high" if analysis["metrics"]["volatility"] > 0.5 else "medium",
                        "details": analysis["metrics"],
                        "timestamp": datetime.now().isoformat()
                    })

        except Exception as e:
            self.logger.error(f"Error handling price alert: {str(e)}")

    async def monitor_new_launches(self) -> None:
        """Monitor for new token launches"""
        try:
            if self.use_mock:
                # Use mock data in test mode
                token = get_mock_token()
                await event_manager.emit("new_token_detected", token)
            else:
                # TODO: Implement real token launch monitoring
                pass

        except Exception as e:
            self.logger.error(f"Error monitoring new launches: {str(e)}")
