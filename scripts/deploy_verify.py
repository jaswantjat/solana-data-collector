"""Deployment verification script for the Solana token monitoring system"""
import os
import sys
import asyncio
import logging
from datetime import datetime
import requests
import psutil
import json
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentVerifier:
    """Verifies deployment status and system health"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.checks_passed = 0
        self.checks_failed = 0
        
    async def verify_deployment(self) -> bool:
        """Run all deployment verification checks"""
        try:
            logger.info("Starting deployment verification...")
            
            # Check API health
            if not await self.check_api_health():
                return False
                
            # Check database connection
            if not await self.check_database():
                return False
                
            # Check component status
            if not await self.check_components():
                return False
                
            # Check monitoring
            if not await self.check_monitoring():
                return False
                
            # Check performance
            if not await self.check_performance():
                return False
                
            logger.info(f"Verification complete. Passed: {self.checks_passed}, Failed: {self.checks_failed}")
            return self.checks_failed == 0
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return False
            
    async def check_api_health(self) -> bool:
        """Check API health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                health_data = response.json()
                if health_data["status"] == "healthy":
                    logger.info("✅ API health check passed")
                    self.checks_passed += 1
                    return True
                    
            logger.error("❌ API health check failed")
            self.checks_failed += 1
            return False
            
        except Exception as e:
            logger.error(f"❌ API health check error: {str(e)}")
            self.checks_failed += 1
            return False
            
    async def check_database(self) -> bool:
        """Check database connection"""
        try:
            response = requests.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                health_data = response.json()
                if health_data["components"]["database"] == "healthy":
                    logger.info("✅ Database check passed")
                    self.checks_passed += 1
                    return True
                    
            logger.error("❌ Database check failed")
            self.checks_failed += 1
            return False
            
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
            self.checks_failed += 1
            return False
            
    async def check_components(self) -> bool:
        """Check all system components"""
        try:
            response = requests.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                health_data = response.json()
                components = health_data["components"]
                
                all_healthy = all(
                    status == "healthy" for status in components.values()
                )
                
                if all_healthy:
                    logger.info("✅ Component check passed")
                    self.checks_passed += 1
                    return True
                    
            logger.error("❌ Component check failed")
            self.checks_failed += 1
            return False
            
        except Exception as e:
            logger.error(f"❌ Component check error: {str(e)}")
            self.checks_failed += 1
            return False
            
    async def check_monitoring(self) -> bool:
        """Check monitoring systems"""
        try:
            # Check metrics endpoint
            metrics_response = requests.get(f"{self.base_url}/api/system/metrics")
            if metrics_response.status_code != 200:
                logger.error("❌ Metrics check failed")
                self.checks_failed += 1
                return False
                
            # Check alerts endpoint
            alerts_response = requests.get(f"{self.base_url}/api/alerts/status")
            if alerts_response.status_code != 200:
                logger.error("❌ Alerts check failed")
                self.checks_failed += 1
                return False
                
            logger.info("✅ Monitoring check passed")
            self.checks_passed += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Monitoring check error: {str(e)}")
            self.checks_failed += 1
            return False
            
    async def check_performance(self) -> bool:
        """Check system performance"""
        try:
            response = requests.get(f"{self.base_url}/api/system/metrics")
            if response.status_code == 200:
                metrics = response.json()
                
                # Check CPU usage
                if metrics["cpu_usage"] > 80:
                    logger.warning("⚠️ High CPU usage detected")
                    
                # Check memory usage
                if metrics["memory_usage"] > 80:
                    logger.warning("⚠️ High memory usage detected")
                    
                # Check response time
                if metrics["response_time"] > 1000:  # 1 second
                    logger.warning("⚠️ High response time detected")
                    
                logger.info("✅ Performance check passed")
                self.checks_passed += 1
                return True
                
            logger.error("❌ Performance check failed")
            self.checks_failed += 1
            return False
            
        except Exception as e:
            logger.error(f"❌ Performance check error: {str(e)}")
            self.checks_failed += 1
            return False

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python deploy_verify.py <base_url>")
        sys.exit(1)
        
    base_url = sys.argv[1]
    verifier = DeploymentVerifier(base_url)
    
    if await verifier.verify_deployment():
        logger.info("🎉 Deployment verification successful!")
        sys.exit(0)
    else:
        logger.error("❌ Deployment verification failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
