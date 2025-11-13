"""Pydantic models for alerts API"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class AlertCreate(BaseModel):
    """Create alert request model"""
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTC/USDT')")
    alert_type: Literal["price", "indicator"] = Field(..., description="Type of alert")
    
    # Price alert fields
    price_threshold: Optional[float] = Field(None, description="Price threshold for price alerts")
    price_condition: Optional[Literal["above", "below"]] = Field(None, description="Price condition (above/below)")
    
    # Indicator alert fields
    indicator_name: Optional[str] = Field(None, description="Indicator name (e.g., 'RSI', 'MACD', 'MACD_crossover')")
    indicator_condition: Optional[Literal["above", "below", "crosses_above", "crosses_below"]] = Field(None, description="Indicator condition")
    indicator_value: Optional[float] = Field(None, description="Indicator threshold value")
    
    # Common fields
    enabled: bool = Field(default=True, description="Whether alert is enabled")
    description: Optional[str] = Field(None, description="Optional description for the alert")


class AlertUpdate(BaseModel):
    """Update alert request model"""
    enabled: Optional[bool] = Field(None, description="Whether alert is enabled")
    price_threshold: Optional[float] = Field(None, description="Price threshold")
    price_condition: Optional[Literal["above", "below"]] = Field(None, description="Price condition")
    indicator_value: Optional[float] = Field(None, description="Indicator threshold value")
    description: Optional[str] = Field(None, description="Alert description")


class AlertResponse(BaseModel):
    """Alert response model"""
    id: str
    symbol: str
    alert_type: str  # "price" or "indicator"
    
    # Price alert fields
    price_threshold: Optional[float] = None
    price_condition: Optional[str] = None  # "above" or "below"
    
    # Indicator alert fields
    indicator_name: Optional[str] = None
    indicator_condition: Optional[str] = None
    indicator_value: Optional[float] = None
    
    # Status fields
    enabled: bool
    triggered: bool
    triggered_at: Optional[str] = None
    description: Optional[str] = None
    
    # Timestamps
    created_at: str
    updated_at: str


class AlertListResponse(BaseModel):
    """List of alerts response"""
    alerts: list[AlertResponse]
    total: int
    active: int  # Number of enabled alerts
    triggered: int  # Number of triggered alerts


