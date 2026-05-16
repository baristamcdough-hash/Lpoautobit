from collections import defaultdict
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models import LPODocument, LPOLineItem
from backend.schemas import (
    DashboardResponse,
    DistributionEntry,
    DistributionItemDetail,
    LPODocumentResponse,
    LPOLineItemResponse,
    MasterProcurementItem,
    StatusUpdate,
    UploadResponse,
)
from backend.services.ai_extractor import extract_lpo_data
from backend.services.pdf_parser import extract_text_from_pdf

router = APIRouter(prefix="/api/lpo", tags=["LPO"])


@router.post("/upload", response_model=UploadResponse)
async def upload_lpos(
    files: List[UploadFile],
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more PDF files for LPO extraction."""
    documents = []

    for file in files:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type for '{file.filename}'. Only PDF files are accepted.",
            )

        # Read file content
        file_bytes = await file.read()

        # Create document record
        doc = LPODocument(
            filename=file.filename,
            status="processing",
        )
        db.add(doc)
        await db.flush()

        # Extract text from PDF
        text = extract_text_from_pdf(file_bytes)

        if not text:
            doc.status = "error"
            await db.commit()
            documents.append(doc)
            continue

        # Extract structured data using AI or fallback
        try:
            extracted = await extract_lpo_data(text)
            doc.customer_name = extracted.get("customer_name", "Unknown")
            doc.status = "completed"

            # Create line items
            for item in extracted.get("line_items", []):
                line_item = LPOLineItem(
                    document_id=doc.id,
                    item_name=item["item_name"],
                    quantity=float(item["quantity"]),
                    unit=item["unit"],
                    date_extracted=date.today(),
                )
                db.add(line_item)
        except Exception:
            doc.status = "error"

        documents.append(doc)

    await db.commit()

    # Refresh to get updated fields
    for doc in documents:
        await db.refresh(doc)

    return UploadResponse(
        documents=[LPODocumentResponse.model_validate(doc) for doc in documents],
        message=f"Processed {len(documents)} file(s) successfully.",
    )


@router.get("/raw-data", response_model=List[LPOLineItemResponse])
async def get_raw_data(
    date_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all LPO line items, optionally filtered by date."""
    query = select(LPOLineItem)

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            query = query.where(LPOLineItem.date_extracted == filter_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD.",
            )

    result = await db.execute(query)
    items = result.scalars().all()
    return [LPOLineItemResponse.model_validate(item) for item in items]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    date_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated dashboard data for a given date (defaults to today)."""
    if date_filter:
        try:
            target_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD.",
            )
    else:
        target_date = date.today()

    # Get all line items for the target date with their documents
    query = (
        select(LPOLineItem)
        .where(LPOLineItem.date_extracted == target_date)
        .options(selectinload(LPOLineItem.document))
    )
    result = await db.execute(query)
    items = result.scalars().all()

    # Build master procurement (aggregate by item_name + unit)
    procurement_map = defaultdict(lambda: {"total_quantity": 0.0, "unit": "", "item_ids": []})
    for item in items:
        key = (item.item_name.lower(), item.unit.lower())
        procurement_map[key]["total_quantity"] += item.quantity
        procurement_map[key]["unit"] = item.unit
        procurement_map[key]["item_ids"].append(item.id)

    master_procurement = [
        MasterProcurementItem(
            item_name=key[0].title(),
            total_quantity=data["total_quantity"],
            unit=data["unit"],
            item_ids=data["item_ids"],
        )
        for key, data in procurement_map.items()
    ]

    # Build distribution breakdown (group by customer)
    distribution_map = defaultdict(list)
    for item in items:
        customer = item.document.customer_name or "Unknown"
        distribution_map[customer].append(
            DistributionItemDetail(
                item_name=item.item_name,
                quantity=item.quantity,
                unit=item.unit,
            )
        )

    distribution = [
        DistributionEntry(customer_name=customer, items=items_list)
        for customer, items_list in distribution_map.items()
    ]

    return DashboardResponse(
        date=target_date.isoformat(),
        master_procurement=master_procurement,
        distribution=distribution,
    )


@router.patch("/items/{item_id}/status")
async def update_item_status(
    item_id: int,
    body: StatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update the procurement status of a line item."""
    if body.status not in ("procured", "pending"):
        raise HTTPException(
            status_code=400,
            detail="Status must be 'procured' or 'pending'.",
        )

    result = await db.execute(select(LPOLineItem).where(LPOLineItem.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    # For now, we store status on the parent document
    # In a future iteration, line items could have their own status field
    result = await db.execute(
        select(LPODocument).where(LPODocument.id == item.document_id)
    )
    doc = result.scalar_one_or_none()
    if doc:
        doc.status = body.status
        await db.commit()

    return {"item_id": item_id, "status": body.status}
