"""Pydantic models for notifications API"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class NotificationResponse(BaseModel):
    """Notification response model"""
    id: str
    type: str
    priority: str
    title: str
    message: str
    source: str
    symbol: Optional[str] = None
    confidence_score: Optional[float] = None
    urgency_score: Optional[float] = None
    promise_score: Optional[float] = None
    metadata: Dict = Field(default_factory=dict)
    actions: List[str] = Field(default_factory=list)
    created_at: str
    expires_at: Optional[str] = None
    read: bool = False
    responded: bool = False
    response_action: Optional[str] = None
    response_at: Optional[str] = None
    summarized_message: Optional[str] = None  # AI-generated concise message
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc12345",
                "type": "combined_signal",
                "priority": "critical",
                "title": "Combined Signal - BTC/USDT",
                "message": "Strong buy signal detected with 85% confidence",
                "source": "combined",
                "symbol": "BTC/USDT",
                "confidence_score": 85.0,
                "urgency_score": 90.0,
                "promise_score": 88.0,
                "metadata": {},
                "actions": ["approve", "reject", "custom"],
                "created_at": "2025-11-12T10:00:00",
                "read": False,
                "responded": False,
                "summarized_message": "BTC breaking resistance. High confidence. Volume surge detected."
            }
        }


class NotificationCreate(BaseModel):
    """Create notification request model"""
    type: str
    priority: str
    title: str
    message: str
    source: str
    symbol: Optional[str] = None
    confidence_score: Optional[float] = None
    urgency_score: Optional[float] = None
    promise_score: Optional[float] = None
    metadata: Dict = Field(default_factory=dict)
    actions: List[str] = Field(default_factory=list)
    expires_at: Optional[str] = None


class NotificationUpdate(BaseModel):
    """Update notification request model"""
    read: Optional[bool] = None
    response_action: Optional[str] = None


class NotificationListResponse(BaseModel):
    """List of notifications response"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int

