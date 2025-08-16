"""
Common schemas and response models
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(default=True)
    message: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DataResponse(BaseResponse):
    """Response with data"""
    data: Any = Field(...)


class ListResponse(BaseResponse):
    """Response with list data"""
    data: List[Any] = Field(default_factory=list)
    count: int = Field(default=0)
    total: Optional[int] = Field(default=None)
    page: Optional[int] = Field(default=None)
    page_size: Optional[int] = Field(default=None)
    # Enhanced pagination fields
    limit: Optional[int] = Field(default=None)
    total_pages: Optional[int] = Field(default=None)
    has_next: Optional[bool] = Field(default=None)
    has_prev: Optional[bool] = Field(default=None)
    filters_applied: Optional[Dict[str, Any]] = Field(default=None)
    data_source: Optional[str] = Field(default=None)


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = Field(default=False)
    error_code: Optional[str] = Field(default=None)
    details: Optional[Dict[str, Any]] = Field(default=None)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(...)
    timestamp: float = Field(...)
    version: str = Field(...)
    database: bool = Field(default=True)
    redis: bool = Field(default=True)


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class SortParams(BaseModel):
    """Sorting parameters"""
    sort_by: Optional[str] = Field(default=None)
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")


class FilterParams(BaseModel):
    """Filtering parameters"""
    symbol: Optional[str] = Field(default=None)
    strategy: Optional[str] = Field(default=None)
    option_type: Optional[str] = Field(default=None, pattern="^(call|put)$")
    transaction_side: Optional[str] = Field(default=None, pattern="^(buy|sell)$")
    expiration_from: Optional[datetime] = Field(default=None)
    expiration_to: Optional[datetime] = Field(default=None)