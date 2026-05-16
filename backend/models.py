from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class LPODocument(Base):
    __tablename__ = "lpo_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    customer_name = Column(String, nullable=True)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")

    line_items = relationship("LPOLineItem", back_populates="document")


class LPOLineItem(Base):
    __tablename__ = "lpo_line_items"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("lpo_documents.id"), nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    date_extracted = Column(Date, default=date.today)
    status = Column(String, default="pending")

    document = relationship("LPODocument", back_populates="line_items")
