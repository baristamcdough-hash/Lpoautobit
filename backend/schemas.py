from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class LPOLineItemResponse(BaseModel):
    id: int
    document_id: int
    item_name: str
    quantity: float
    unit: str
    date_extracted: date

    class Config:
        from_attributes = True


class LPODocumentResponse(BaseModel):
    id: int
    filename: str
    customer_name: Optional[str] = None
    upload_timestamp: datetime
    status: str

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    documents: List[LPODocumentResponse]
    message: str


class MasterProcurementItem(BaseModel):
    item_name: str
    total_quantity: float
    unit: str
    item_ids: List[int]


class DistributionItemDetail(BaseModel):
    item_name: str
    quantity: float
    unit: str


class DistributionEntry(BaseModel):
    customer_name: str
    items: List[DistributionItemDetail]


class DashboardResponse(BaseModel):
    date: str
    master_procurement: List[MasterProcurementItem]
    distribution: List[DistributionEntry]


class StatusUpdate(BaseModel):
    status: str
