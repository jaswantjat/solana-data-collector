import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
import sys
import os
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemChecker:
    def __init__(self):
        self.results = {
            "database": {},
            "redis": {},
            "dependencies": {},
            "environment": {}
        }
        
    async def check_all(self) -> Dict:
        """Run all system checks"""
        try:
            await asyncio.gather(
                self.check_database_prerequisites(),
                self.check_redis_prerequisites(),
                self.check_dependencies(),
                self.check_environment()
            )
            return self.results
        except Exception as e:
            logger.error(f"Error in system check: {str(e)}")
            raise
            
    async def check_database_prerequisites(self):
        """Check PostgreSQL installation and configuration"""
        try:
            # Check if psql is installed
            psql_version = await self._run_command("psql --version")
            postgres_status = "installed" if psql_version else "not_installed"
            
            # Check if database exists
            db_exists = await self._run_command("psql -l | grep solana_data")
            db_status = "exists" if db_exists else "not_exists"
            
            # Get database URL from environment
            db_url = os.getenv("DATABASE_URL", "")
            db_config_status = "configured" if db_url else "not_configured"
            
            self.results["database"] = {
                "postgres_installation": postgres_status,
                "database_exists": db_status,
                "configuration": db_config_status,
                "status": "ready" if all(s in ["installed", "exists", "configured"] 
                                      for s in [postgres_status, db_status, db_config_status]) 
                         else "not_ready",
                "actions_needed": self._get_database_actions(postgres_status, db_status, db_config_status)
            }
            
        except Exception as e:
            logger.error(f"Database prerequisite check error: {str(e)}")
            self.results["database"] = {"status": "error", "message": str(e)}
            
    async def check_redis_prerequisites(self):
        """Check Redis installation and configuration"""
        try:
            # Check if Redis is installed
            redis_version = await self._run_command("redis-cli --version")
            redis_status = "installed" if redis_version else "not_installed"
            
            # Check if Redis server is running
            redis_running = await self._run_command("redis-cli ping")
            server_status = "running" if redis_running == "PONG" else "not_running"
            
            # Get Redis URL from environment
            redis_url = os.getenv("REDIS_URL", "")
            redis_config_status = "configured" if redis_url else "not_configured"
            
            self.results["redis"] = {
                "redis_installation": redis_status,
                "server_status": server_status,
                "configuration": redis_config_status,
                "status": "ready" if all(s in ["installed", "running", "configured"]
                                      for s in [redis_status, server_status, redis_config_status])
                         else "not_ready",
                "actions_needed": self._get_redis_actions(redis_status, server_status, redis_config_status)
            }
            
        except Exception as e:
            logger.error(f"Redis prerequisite check error: {str(e)}")
            self.results["redis"] = {"status": "error", "message": str(e)}
            
    async def check_dependencies(self):
        """Check Python dependencies"""
        try:
            required_packages = [
                "sqlalchemy",
                "asyncpg",
                "aioredis",
                "fastapi",
                "pandas",
                "plotly"
            ]
            
            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)
                    
            self.results["dependencies"] = {
                "required_packages": required_packages,
                "missing_packages": missing_packages,
                "status": "ready" if not missing_packages else "not_ready",
                "actions_needed": [f"pip install {pkg}" for pkg in missing_packages] if missing_packages else []
            }
            
        except Exception as e:
            logger.error(f"Dependency check error: {str(e)}")
            self.results["dependencies"] = {"status": "error", "message": str(e)}
            
    async def check_environment(self):
        """Check environment variables"""
        try:
            required_vars = [
                "DATABASE_URL",
                "DATABASE_POOL_SIZE",
                "DATABASE_MAX_OVERFLOW",
                "DATABASE_POOL_TIMEOUT",
                "REDIS_URL",
                "REDIS_DB",
                "REDIS_POOL_SIZE",
                "REDIS_TIMEOUT"
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
                    
            self.results["environment"] = {
                "required_variables": required_vars,
                "missing_variables": missing_vars,
                "status": "ready" if not missing_vars else "not_ready",
                "actions_needed": ["Add missing environment variables to .env file"] if missing_vars else []
            }
            
        except Exception as e:
            logger.error(f"Environment check error: {str(e)}")
            self.results["environment"] = {"status": "error", "message": str(e)}
            
    async def _run_command(self, command: str) -> Optional[str]:
        """Run a shell command and return output"""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return stdout.decode().strip() if stdout else None
        except Exception:
            return None
            
    def _get_database_actions(self, postgres_status: str, db_status: str, config_status: str) -> list:
        """Get required actions for database setup"""
        actions = []
        if postgres_status == "not_installed":
            actions.append("Install PostgreSQL: brew install postgresql")
        if db_status == "not_exists":
            actions.append("Create database: createdb solana_data")
        if config_status == "not_configured":
            actions.append("Configure DATABASE_URL in .env file")
        return actions
        
    def _get_redis_actions(self, redis_status: str, server_status: str, config_status: str) -> list:
        """Get required actions for Redis setup"""
        actions = []
        if redis_status == "not_installed":
            actions.append("Install Redis: brew install redis")
        if server_status == "not_running":
            actions.append("Start Redis server: brew services start redis")
        if config_status == "not_configured":
            actions.append("Configure REDIS_URL in .env file")
        return actions
        
async def main():
    try:
        checker = SystemChecker()
        results = await checker.check_all()
        
        # Print results
        print("\nSystem Check Results:")
        print("=" * 50)
        
        for component, data in results.items():
            print(f"\n{component.upper()}:")
            status = data.get("status", "unknown")
            status_color = {
                "ready": "\033[92m",      # Green
                "not_ready": "\033[93m",  # Yellow
                "error": "\033[91m",      # Red
                "unknown": "\033[90m"     # Gray
            }.get(status, "\033[0m")
            print(f"Status: {status_color}{status}\033[0m")
            
            if status != "ready":
                if "message" in data:
                    print(f"Error: {data['message']}")
                if "actions_needed" in data:
                    print("\nRequired Actions:")
                    for action in data["actions_needed"]:
                        print(f"  - {action}")
                        
        # Save results to file
        report_dir = Path("reports/system_checks")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"system_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(results, f, indent=2)
            
        print(f"\nDetailed report saved to: {report_file}")
        
        # Exit with error if any component is not ready
        if any(data.get("status") != "ready" for data in results.values()):
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error running system checks: {str(e)}")
        sys.exit(1)
        
if __name__ == "__main__":
    asyncio.run(main())
