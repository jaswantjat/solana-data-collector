"""Deployment verification script for the Solana token monitoring system"""
import os
import sys
import asyncio
import logging
from datetime import datetime
import aiohttp
import psutil
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import db_manager
from src.integrations.helius import HeliusAPI
from src.integrations.shyft import ShyftAPI
from src.integrations.bitquery import BitqueryAPI
from src.config import (
    HELIUS_API_KEY,
    SHYFT_API_KEY,
    DATABASE_URL,
    LOG_LEVEL,
    LOG_FORMAT
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

class DeploymentVerifier:
    """Verifies deployment status and system health"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending",
            "checks": {},
            "errors": []
        }
        
    async def verify_deployment(self) -> bool:
        """Run all deployment verification checks"""
        try:
            logger.info("Starting deployment verification...")
            
            # Check environment variables
            if not await self.check_environment():
                return False
                
            # Check database connection
            if not await self.check_database():
                return False
                
            # Check API integrations
            if not await self.check_api_integrations():
                return False
                
            # Check system resources
            if not await self.check_system_resources():
                return False
                
            # Save results
            self.save_results()
            
            # Log summary
            logger.info(f"Verification complete: {self.checks_passed} passed, {self.checks_failed} failed")
            return self.checks_failed == 0
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            self.results["errors"].append(str(e))
            return False
            
    async def check_environment(self) -> bool:
        """Check required environment variables"""
        required_vars = [
            "HELIUS_API_KEY",
            "SHYFT_API_KEY",
            "DATABASE_URL",
            "JWT_SECRET"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        self.results["checks"]["environment"] = {
            "status": "passed" if not missing_vars else "failed",
            "missing_vars": missing_vars
        }
        
        if missing_vars:
            self.checks_failed += 1
            logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
            return False
            
        self.checks_passed += 1
        return True
        
    async def check_database(self) -> bool:
        """Check database connection and migrations"""
        try:
            # Test connection
            async with db_manager.session() as session:
                await session.execute("SELECT 1")
            
            self.results["checks"]["database"] = {
                "status": "passed",
                "url": DATABASE_URL.split("@")[-1]  # Hide credentials
            }
            self.checks_passed += 1
            return True
            
        except Exception as e:
            self.checks_failed += 1
            logger.error(f"Database check failed: {str(e)}")
            self.results["checks"]["database"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
            
    async def check_api_integrations(self) -> bool:
        """Check API integrations"""
        apis = {
            "helius": HeliusAPI(HELIUS_API_KEY),
            "shyft": ShyftAPI(SHYFT_API_KEY)
        }
        
        all_passed = True
        self.results["checks"]["apis"] = {}
        
        for name, api in apis.items():
            try:
                await api.check_health()
                self.results["checks"]["apis"][name] = {
                    "status": "passed"
                }
                self.checks_passed += 1
            except Exception as e:
                all_passed = False
                self.checks_failed += 1
                logger.error(f"{name.capitalize()} API check failed: {str(e)}")
                self.results["checks"]["apis"][name] = {
                    "status": "failed",
                    "error": str(e)
                }
                
        return all_passed
        
    async def check_system_resources(self) -> bool:
        """Check system resources"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            checks = {
                "memory": memory.percent < 90,
                "disk": disk.percent < 90,
                "cpu": psutil.cpu_percent(interval=1) < 90
            }
            
            self.results["checks"]["resources"] = {
                "status": "passed" if all(checks.values()) else "failed",
                "memory_used": f"{memory.percent}%",
                "disk_used": f"{disk.percent}%",
                "cpu_used": f"{psutil.cpu_percent()}%"
            }
            
            if all(checks.values()):
                self.checks_passed += 1
                return True
            else:
                self.checks_failed += 1
                return False
                
        except Exception as e:
            self.checks_failed += 1
            logger.error(f"Resource check failed: {str(e)}")
            self.results["checks"]["resources"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
            
    def save_results(self):
        """Save verification results"""
        try:
            self.results["status"] = "success" if self.checks_failed == 0 else "failed"
            
            # Save to file
            output_file = "deployment_verification.json"
            with open(output_file, "w") as f:
                json.dump(self.results, f, indent=2)
                
            logger.info(f"Results saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")

async def main():
    """Main entry point"""
    verifier = DeploymentVerifier()
    success = await verifier.verify_deployment()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
