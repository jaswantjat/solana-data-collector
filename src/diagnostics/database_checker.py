import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from ..database.database_manager import DatabaseManager
from ..database.models import (
    Token, TokenPrice, TokenHolder, TokenTransaction,
    WalletAnalysis, Alert, SystemMetric
)

logger = logging.getLogger(__name__)

class DatabaseChecker:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.results = {
            "connections": {},
            "integrity": {},
            "performance": {},
            "relationships": {},
            "gaps": {},
            "sync": {}
        }
        
    async def run_full_check(self) -> Dict:
        """Run all database checks"""
        try:
            logger.info("Starting full database check")
            
            # Run all checks
            await asyncio.gather(
                self.check_connections(),
                self.check_data_integrity(),
                self.check_query_performance(),
                self.check_relationships(),
                self.check_data_gaps(),
                self.check_sync_issues()
            )
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error in full database check: {str(e)}")
            raise
            
    async def check_connections(self):
        """Check all database connections"""
        try:
            async with self.db_manager.get_session() as session:
                # Get connection stats
                pool_stats = await self.db_manager.get_pool_stats()
                
                # Check active connections
                result = await session.execute(
                    text("""
                    SELECT count(*) as connections,
                           state,
                           wait_event_type
                    FROM pg_stat_activity
                    GROUP BY state, wait_event_type
                    """)
                )
                connections = result.fetchall()
                
                # Check connection timeouts
                result = await session.execute(
                    text("""
                    SELECT count(*) as timeouts
                    FROM pg_stat_activity
                    WHERE state = 'idle'
                    AND current_timestamp - state_change > interval '1 hour'
                    """)
                )
                timeouts = result.scalar()
                
                self.results["connections"] = {
                    "pool_stats": pool_stats,
                    "active_connections": connections,
                    "connection_timeouts": timeouts,
                    "status": "healthy" if timeouts == 0 else "warning"
                }
                
        except Exception as e:
            logger.error(f"Connection check error: {str(e)}")
            self.results["connections"] = {"status": "error", "message": str(e)}
            
    async def check_data_integrity(self):
        """Check data integrity for all tables"""
        try:
            async with self.db_manager.get_session() as session:
                integrity_checks = {}
                
                # Check each table
                for table in [Token, TokenPrice, TokenHolder, TokenTransaction,
                            WalletAnalysis, Alert, SystemMetric]:
                    table_name = table.__tablename__
                    
                    # Check for null values in required fields
                    null_counts = await self._check_null_values(session, table)
                    
                    # Check for duplicate records
                    duplicates = await self._check_duplicates(session, table)
                    
                    # Check for data consistency
                    consistency = await self._check_data_consistency(session, table)
                    
                    integrity_checks[table_name] = {
                        "null_values": null_counts,
                        "duplicates": duplicates,
                        "consistency": consistency,
                        "status": "healthy" if not (null_counts or duplicates) else "warning"
                    }
                    
                self.results["integrity"] = integrity_checks
                
        except Exception as e:
            logger.error(f"Integrity check error: {str(e)}")
            self.results["integrity"] = {"status": "error", "message": str(e)}
            
    async def check_query_performance(self):
        """Check query performance"""
        try:
            async with self.db_manager.get_session() as session:
                performance_metrics = {}
                
                # Test common queries
                test_queries = [
                    ("token_lookup", "SELECT * FROM tokens WHERE address = :address"),
                    ("price_history", "SELECT * FROM token_prices WHERE token_id = :token_id"),
                    ("holder_analysis", "SELECT * FROM token_holders WHERE token_id = :token_id"),
                    ("transaction_history", "SELECT * FROM token_transactions WHERE token_id = :token_id")
                ]
                
                for name, query in test_queries:
                    start_time = datetime.now()
                    await session.execute(text(query), {"address": "dummy", "token_id": 1})
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    performance_metrics[name] = {
                        "duration": duration,
                        "status": "healthy" if duration < 1.0 else "warning"
                    }
                    
                # Check index usage
                result = await session.execute(
                    text("""
                    SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
                    FROM pg_stat_user_indexes
                    WHERE idx_scan = 0
                    """)
                )
                unused_indexes = result.fetchall()
                
                self.results["performance"] = {
                    "query_metrics": performance_metrics,
                    "unused_indexes": unused_indexes,
                    "status": "healthy" if all(m["status"] == "healthy" for m in performance_metrics.values()) else "warning"
                }
                
        except Exception as e:
            logger.error(f"Performance check error: {str(e)}")
            self.results["performance"] = {"status": "error", "message": str(e)}
            
    async def check_relationships(self):
        """Check data relationships"""
        try:
            async with self.db_manager.get_session() as session:
                relationship_checks = {}
                
                # Check token relationships
                token_checks = await self._check_token_relationships(session)
                
                # Check wallet relationships
                wallet_checks = await self._check_wallet_relationships(session)
                
                # Check transaction relationships
                transaction_checks = await self._check_transaction_relationships(session)
                
                self.results["relationships"] = {
                    "tokens": token_checks,
                    "wallets": wallet_checks,
                    "transactions": transaction_checks,
                    "status": "healthy" if all(c["status"] == "healthy" for c in [token_checks, wallet_checks, transaction_checks]) else "warning"
                }
                
        except Exception as e:
            logger.error(f"Relationship check error: {str(e)}")
            self.results["relationships"] = {"status": "error", "message": str(e)}
            
    async def check_data_gaps(self):
        """Check for data gaps"""
        try:
            async with self.db_manager.get_session() as session:
                gaps = {}
                
                # Check price data gaps
                price_gaps = await self._check_price_gaps(session)
                
                # Check transaction data gaps
                transaction_gaps = await self._check_transaction_gaps(session)
                
                # Check holder data gaps
                holder_gaps = await self._check_holder_gaps(session)
                
                self.results["gaps"] = {
                    "prices": price_gaps,
                    "transactions": transaction_gaps,
                    "holders": holder_gaps,
                    "status": "healthy" if all(len(g) == 0 for g in [price_gaps, transaction_gaps, holder_gaps]) else "warning"
                }
                
        except Exception as e:
            logger.error(f"Gap check error: {str(e)}")
            self.results["gaps"] = {"status": "error", "message": str(e)}
            
    async def check_sync_issues(self):
        """Check for synchronization issues"""
        try:
            async with self.db_manager.get_session() as session:
                sync_issues = {}
                
                # Check for data inconsistencies between related tables
                token_sync = await self._check_token_sync(session)
                
                # Check for transaction ordering issues
                transaction_sync = await self._check_transaction_sync(session)
                
                # Check for holder balance consistency
                holder_sync = await self._check_holder_sync(session)
                
                self.results["sync"] = {
                    "tokens": token_sync,
                    "transactions": transaction_sync,
                    "holders": holder_sync,
                    "status": "healthy" if all(s["status"] == "healthy" for s in [token_sync, transaction_sync, holder_sync]) else "warning"
                }
                
        except Exception as e:
            logger.error(f"Sync check error: {str(e)}")
            self.results["sync"] = {"status": "error", "message": str(e)}
            
    async def _check_null_values(self, session: AsyncSession, table: Any) -> Dict:
        """Check for null values in required fields"""
        result = await session.execute(
            select(func.count()).select_from(table).where(
                func.concat_ws('', *[getattr(table, c.name) for c in table.__table__.columns]) == None
            )
        )
        return result.scalar()
        
    async def _check_duplicates(self, session: AsyncSession, table: Any) -> Dict:
        """Check for duplicate records"""
        # This needs to be customized based on what constitutes a duplicate for each table
        return {}
        
    async def _check_data_consistency(self, session: AsyncSession, table: Any) -> Dict:
        """Check data consistency"""
        # This needs to be customized based on consistency rules for each table
        return {}
        
    async def _check_token_relationships(self, session: AsyncSession) -> Dict:
        """Check token relationships"""
        try:
            # Check for orphaned prices
            orphaned_prices = await session.execute(
                select(func.count()).select_from(TokenPrice).where(
                    ~TokenPrice.token_id.in_(select(Token.id))
                )
            )
            
            # Check for orphaned holders
            orphaned_holders = await session.execute(
                select(func.count()).select_from(TokenHolder).where(
                    ~TokenHolder.token_id.in_(select(Token.id))
                )
            )
            
            return {
                "orphaned_prices": orphaned_prices.scalar(),
                "orphaned_holders": orphaned_holders.scalar(),
                "status": "healthy" if orphaned_prices.scalar() == 0 and orphaned_holders.scalar() == 0 else "warning"
            }
            
        except Exception as e:
            logger.error(f"Token relationship check error: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _check_wallet_relationships(self, session: AsyncSession) -> Dict:
        """Check wallet relationships"""
        try:
            # Check for inconsistent wallet analyses
            inconsistent = await session.execute(
                select(func.count()).select_from(WalletAnalysis).where(
                    WalletAnalysis.wallet_address.notin_(
                        select(TokenHolder.wallet_address)
                    )
                )
            )
            
            return {
                "inconsistent_analyses": inconsistent.scalar(),
                "status": "healthy" if inconsistent.scalar() == 0 else "warning"
            }
            
        except Exception as e:
            logger.error(f"Wallet relationship check error: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _check_transaction_relationships(self, session: AsyncSession) -> Dict:
        """Check transaction relationships"""
        try:
            # Check for orphaned transactions
            orphaned = await session.execute(
                select(func.count()).select_from(TokenTransaction).where(
                    ~TokenTransaction.token_id.in_(select(Token.id))
                )
            )
            
            return {
                "orphaned_transactions": orphaned.scalar(),
                "status": "healthy" if orphaned.scalar() == 0 else "warning"
            }
            
        except Exception as e:
            logger.error(f"Transaction relationship check error: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _check_price_gaps(self, session: AsyncSession) -> List[Dict]:
        """Check for gaps in price data"""
        try:
            # Find gaps longer than 5 minutes
            result = await session.execute(
                text("""
                SELECT token_id,
                       timestamp as gap_start,
                       lead(timestamp) over (partition by token_id order by timestamp) as gap_end
                FROM token_prices
                WHERE timestamp < NOW() - INTERVAL '5 minutes'
                HAVING gap_end - timestamp > INTERVAL '5 minutes'
                """)
            )
            
            return [dict(row) for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Price gap check error: {str(e)}")
            return []
            
    async def _check_transaction_gaps(self, session: AsyncSession) -> List[Dict]:
        """Check for gaps in transaction data"""
        try:
            # Find gaps longer than 1 hour
            result = await session.execute(
                text("""
                SELECT token_id,
                       timestamp as gap_start,
                       lead(timestamp) over (partition by token_id order by timestamp) as gap_end
                FROM token_transactions
                WHERE timestamp < NOW() - INTERVAL '1 hour'
                HAVING gap_end - timestamp > INTERVAL '1 hour'
                """)
            )
            
            return [dict(row) for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Transaction gap check error: {str(e)}")
            return []
            
    async def _check_holder_gaps(self, session: AsyncSession) -> List[Dict]:
        """Check for gaps in holder data"""
        try:
            # Find tokens with no recent holder updates
            result = await session.execute(
                text("""
                SELECT t.id as token_id,
                       max(h.last_updated) as last_update
                FROM tokens t
                LEFT JOIN token_holders h ON t.id = h.token_id
                GROUP BY t.id
                HAVING max(h.last_updated) < NOW() - INTERVAL '24 hours'
                """)
            )
            
            return [dict(row) for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Holder gap check error: {str(e)}")
            return []
            
    async def _check_token_sync(self, session: AsyncSession) -> Dict:
        """Check token data synchronization"""
        try:
            # Check for price/supply mismatches
            result = await session.execute(
                text("""
                SELECT t.id, t.total_supply,
                       tp.price_usd * t.total_supply as market_cap,
                       th.total_balance
                FROM tokens t
                LEFT JOIN (
                    SELECT token_id, price_usd
                    FROM token_prices
                    WHERE timestamp = (
                        SELECT max(timestamp)
                        FROM token_prices
                    )
                ) tp ON t.id = tp.token_id
                LEFT JOIN (
                    SELECT token_id, sum(balance) as total_balance
                    FROM token_holders
                    GROUP BY token_id
                ) th ON t.id = th.token_id
                WHERE abs(t.total_supply - th.total_balance) > 0.01 * t.total_supply
                """)
            )
            
            mismatches = [dict(row) for row in result.fetchall()]
            
            return {
                "supply_mismatches": mismatches,
                "status": "healthy" if len(mismatches) == 0 else "warning"
            }
            
        except Exception as e:
            logger.error(f"Token sync check error: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _check_transaction_sync(self, session: AsyncSession) -> Dict:
        """Check transaction synchronization"""
        try:
            # Check for transaction ordering issues
            result = await session.execute(
                text("""
                SELECT t1.id, t1.timestamp, t2.timestamp as next_timestamp
                FROM token_transactions t1
                JOIN token_transactions t2 ON t1.token_id = t2.token_id
                WHERE t1.timestamp > t2.timestamp
                AND t2.id > t1.id
                """)
            )
            
            ordering_issues = [dict(row) for row in result.fetchall()]
            
            return {
                "ordering_issues": ordering_issues,
                "status": "healthy" if len(ordering_issues) == 0 else "warning"
            }
            
        except Exception as e:
            logger.error(f"Transaction sync check error: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _check_holder_sync(self, session: AsyncSession) -> Dict:
        """Check holder balance synchronization"""
        try:
            # Check for balance inconsistencies
            result = await session.execute(
                text("""
                SELECT th.token_id,
                       sum(th.balance) as total_balance,
                       t.total_supply
                FROM token_holders th
                JOIN tokens t ON th.token_id = t.id
                GROUP BY th.token_id, t.total_supply
                HAVING abs(sum(th.balance) - t.total_supply) > 0.01 * t.total_supply
                """)
            )
            
            balance_issues = [dict(row) for row in result.fetchall()]
            
            return {
                "balance_issues": balance_issues,
                "status": "healthy" if len(balance_issues) == 0 else "warning"
            }
            
        except Exception as e:
            logger.error(f"Holder sync check error: {str(e)}")
            return {"status": "error", "message": str(e)}
