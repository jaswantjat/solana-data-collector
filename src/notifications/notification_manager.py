"""Notification manager for handling alerts and notifications"""
import os
import json
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import aiohttp
from src.events.event_manager import event_manager

# Initialize logger
logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages notifications and alerts"""
    def __init__(self):
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.alert_rules = {}  # Dictionary of rule_id -> rule
        self.rate_limits = {}
        self.alert_history = []
        self.error_log = []
        self.logger = logging.getLogger(__name__)
        
    def add_alert_rule(self, rule: Dict) -> str:
        """Add an alert rule"""
        rule_id = str(len(self.alert_rules) + 1)
        self.alert_rules[rule_id] = rule
        return rule_id
        
    def update_alert_rule(self, rule_id: str, updated_rule: Dict) -> bool:
        """Update an existing alert rule
        
        Args:
            rule_id (str): ID of the rule to update
            updated_rule (Dict): New rule data
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if rule_id not in self.alert_rules:
            return False
            
        self.alert_rules[rule_id] = updated_rule
        return True
        
    def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete an alert rule
        
        Args:
            rule_id (str): ID of the rule to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if rule_id not in self.alert_rules:
            return False
            
        del self.alert_rules[rule_id]
        return True
        
    def get_alert_rule(self, rule_id: str) -> Optional[Dict]:
        """Get an alert rule by its ID
        
        Args:
            rule_id (str): ID of the alert rule to get
        
        Returns:
            Optional[Dict]: Alert rule if found, None otherwise
        """
        return self.alert_rules.get(rule_id)
        
    def match_alert_rules(self, data: Dict) -> List[Dict]:
        """Find all rules that match the data"""
        matching_rules = []
        for rule_id, rule in self.alert_rules.items():
            if not rule.get("enabled", True):
                continue
                
            if self._matches_conditions(data, rule["conditions"]):
                matching_rules.append({**rule, "id": rule_id})
                
        return matching_rules
            
    def _matches_conditions(self, data: Dict, conditions: List[Dict]) -> bool:
        """Check if data matches alert conditions"""
        for condition in conditions:
            field = condition["field"]
            operator = condition["operator"]
            value = condition["value"]
            
            if field not in data:
                return False
                
            data_value = str(data[field])
            
            if operator == "equals":
                if data_value != value:
                    return False
            elif operator == "greater_than":
                if not (float(data_value) > float(value)):
                    return False
            elif operator == "less_than":
                if not (float(data_value) < float(value)):
                    return False
                    
        return True
        
    async def process_alert(self, alert_data: Dict) -> bool:
        """Process an alert through rules and send notifications"""
        matching_rules = self.match_alert_rules(alert_data)
        success = False
        
        for rule in matching_rules:
            notification_success = await self.send_discord_notification(
                alert_data,
                rule.get("priority", "low")
            )
            success = success or notification_success
            
            if notification_success:
                # Log alert
                self.alert_history.append({
                    **alert_data,
                    "rule_id": rule["id"],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Emit event
                await event_manager.emit("alert_processed", {
                    "alert": alert_data,
                    "rule": rule,
                    "timestamp": datetime.now().isoformat()
                })
                
        return success
        
    async def send_discord_notification(self, content: Dict, priority: str = "low") -> bool:
        """Send notification to Discord"""
        if not self.discord_webhook_url:
            self.logger.warning("Discord webhook URL not configured")
            return False
            
        # Check rate limits
        now = datetime.now()
        if priority in self.rate_limits:
            last_sent, count = self.rate_limits[priority]
            if now - last_sent < timedelta(minutes=1):
                if count >= 5:  # Max 5 notifications per minute
                    self.logger.warning(f"Rate limit exceeded for {priority} priority")
                    return False
                self.rate_limits[priority] = (last_sent, count + 1)
            else:
                self.rate_limits[priority] = (now, 1)
        else:
            self.rate_limits[priority] = (now, 1)
            
        try:
            # Format Discord message
            message = {
                "embeds": [{
                    "title": content.get("title", "Alert"),
                    "description": content.get("description", "No description"),
                    "color": self._get_priority_color(priority),
                    "timestamp": datetime.now().isoformat(),
                    "fields": self._format_fields(content)
                }]
            }
            
            # Send notification
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook_url, json=message) as response:
                    if response.status == 204:
                        # Emit event
                        await event_manager.emit("notification_sent", {
                            **content,
                            "priority": priority,
                            "timestamp": datetime.now().isoformat()
                        })
                        return True
                        
            return False
            
        except Exception as e:
            error_msg = f"Failed to send Discord notification: {str(e)}"
            self.logger.error(error_msg)
            self.error_log.append({
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            return False
            
    def _get_priority_color(self, priority: str) -> int:
        """Get Discord embed color for priority"""
        colors = {
            "low": 0x00FF00,  # Green
            "medium": 0xFFA500,  # Orange
            "high": 0xFF0000  # Red
        }
        return colors.get(priority.lower(), 0x808080)  # Default gray
        
    def _format_fields(self, content: Dict) -> List[Dict]:
        """Format content into Discord embed fields"""
        fields = []
        for key, value in content.items():
            if key not in ["title", "description"]:
                fields.append({
                    "name": key.replace("_", " ").title(),
                    "value": str(value),
                    "inline": True
                })
        return fields
        
    @property
    def rate_limit_remaining(self) -> int:
        """Get remaining rate limit for current minute"""
        now = datetime.now()
        total_count = 0
        for last_sent, count in self.rate_limits.values():
            if now - last_sent < timedelta(minutes=1):
                total_count += count
        return max(0, 5 - total_count)
