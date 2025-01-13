from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path
from datetime import datetime

router = APIRouter()

class AlertCondition(BaseModel):
    type: str  # price, market_cap, confidence, holders
    operator: str  # >, <, =
    value: float
    
class Alert(BaseModel):
    id: str
    token_address: str
    condition: AlertCondition
    notification_type: str  # discord, email
    notification_target: str
    created_at: datetime
    is_active: bool = True

class AlertManager:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.alerts_file = self.data_dir / "alerts.json"
        self._ensure_file_exists()
        
    def _ensure_file_exists(self):
        if not self.alerts_file.exists():
            self.alerts_file.write_text('{"alerts": []}')
            
    def get_alerts(self) -> List[Alert]:
        data = json.loads(self.alerts_file.read_text())
        return [Alert(**a) for a in data["alerts"]]
        
    def add_alert(self, alert: Alert):
        data = json.loads(self.alerts_file.read_text())
        data["alerts"].append(alert.dict())
        self.alerts_file.write_text(json.dumps(data, indent=2))
        
    def remove_alert(self, alert_id: str):
        data = json.loads(self.alerts_file.read_text())
        data["alerts"] = [a for a in data["alerts"] if a["id"] != alert_id]
        self.alerts_file.write_text(json.dumps(data, indent=2))
        
    def toggle_alert(self, alert_id: str):
        data = json.loads(self.alerts_file.read_text())
        for alert in data["alerts"]:
            if alert["id"] == alert_id:
                alert["is_active"] = not alert["is_active"]
                break
        self.alerts_file.write_text(json.dumps(data, indent=2))

alert_manager = AlertManager()

@router.get("/alerts", response_model=List[Alert])
async def get_alerts():
    return alert_manager.get_alerts()

@router.post("/alerts", response_model=Alert)
async def create_alert(alert: Alert):
    alert_manager.add_alert(alert)
    return alert

@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    alert_manager.remove_alert(alert_id)
    return {"status": "success"}

@router.post("/alerts/{alert_id}/toggle")
async def toggle_alert(alert_id: str):
    alert_manager.toggle_alert(alert_id)
    return {"status": "success"}
