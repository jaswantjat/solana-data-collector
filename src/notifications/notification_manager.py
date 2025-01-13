import os
import logging
from typing import Dict, List, Optional, Union
import aiohttp
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        
        # Load alert rules
        self.alert_rules = self._load_alert_rules()
        
    def _load_alert_rules(self) -> Dict:
        """Load alert rules from configuration"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "alert_rules.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading alert rules: {str(e)}")
            return {}
            
    async def send_discord_notification(self, content: Dict, priority: str = "normal") -> bool:
        """Send Discord notification"""
        try:
            if not self.discord_webhook_url:
                logger.error("Discord webhook URL not configured")
                return False
                
            # Format embed based on priority
            color = {
                "high": 0xFF0000,    # Red
                "normal": 0x00FF00,  # Green
                "low": 0x0000FF      # Blue
            }.get(priority, 0x00FF00)
            
            # Create fields for token data
            fields = []
            for k, v in content.get("fields", {}).items():
                fields.append({
                    "name": k,
                    "value": str(v),
                    "inline": True
                })
            
            embed = {
                "title": content.get("title", "Alert"),
                "description": content.get("description", ""),
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "fields": fields
            }
            
            # Add footer based on priority
            footer_text = {
                "high": "🚨 High Priority Alert",
                "normal": "ℹ️ Normal Priority",
                "low": "📝 Low Priority"
            }.get(priority, "ℹ️ Normal Priority")
            
            embed["footer"] = {
                "text": footer_text
            }
            
            payload = {
                "embeds": [embed]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook_url, json=payload) as response:
                    return response.status == 204
                    
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
            return False
            
    def add_alert_rule(self, rule: Dict) -> bool:
        """Add new alert rule"""
        try:
            rule_id = rule.get("id") or str(len(self.alert_rules) + 1)
            
            self.alert_rules[rule_id] = {
                "conditions": rule["conditions"],
                "priority": rule.get("priority", "normal"),
                "enabled": rule.get("enabled", True),
                "created_at": datetime.now().isoformat()
            }
            
            # Save updated rules
            self._save_alert_rules()
            return True
            
        except Exception as e:
            logger.error(f"Error adding alert rule: {str(e)}")
            return False
            
    def update_alert_rule(self, rule_id: str, updates: Dict) -> bool:
        """Update existing alert rule"""
        try:
            if rule_id not in self.alert_rules:
                return False
                
            self.alert_rules[rule_id].update(updates)
            self.alert_rules[rule_id]["updated_at"] = datetime.now().isoformat()
            
            # Save updated rules
            self._save_alert_rules()
            return True
            
        except Exception as e:
            logger.error(f"Error updating alert rule: {str(e)}")
            return False
            
    def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete alert rule"""
        try:
            if rule_id not in self.alert_rules:
                return False
                
            del self.alert_rules[rule_id]
            
            # Save updated rules
            self._save_alert_rules()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting alert rule: {str(e)}")
            return False
            
    def _save_alert_rules(self):
        """Save alert rules to configuration file"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "alert_rules.json"
            config_path.parent.mkdir(exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(self.alert_rules, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving alert rules: {str(e)}")
            
    async def process_alert(self, alert_data: Dict) -> bool:
        """Process alert based on rules"""
        try:
            for rule_id, rule in self.alert_rules.items():
                if not rule["enabled"]:
                    continue
                    
                # Check if alert matches rule conditions
                if self._matches_conditions(alert_data, rule["conditions"]):
                    # Send Discord notification
                    await self.send_discord_notification(alert_data, rule["priority"])
                    
            return True
            
        except Exception as e:
            logger.error(f"Error processing alert: {str(e)}")
            return False
            
    def _matches_conditions(self, alert_data: Dict, conditions: List[Dict]) -> bool:
        """Check if alert matches conditions"""
        try:
            for condition in conditions:
                field = condition["field"]
                operator = condition["operator"]
                value = condition["value"]
                
                field_value = alert_data.get(field)
                
                if operator == "equals" and field_value != value:
                    return False
                elif operator == "contains" and value not in str(field_value):
                    return False
                elif operator == "greater_than" and float(field_value) <= float(value):
                    return False
                elif operator == "less_than" and float(field_value) >= float(value):
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error matching conditions: {str(e)}")
            return False
