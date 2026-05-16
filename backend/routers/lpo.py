import logging
from collections import defaultdict
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import StreamingResponse

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
from backend.services.sheets_export import generate_pick_list_csv, generate_raw_data_csv

logger = logging.getLogger(__name__)

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

        # Check file size (10 MB limit)
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(413, "File too large. Maximum size is 10MB.")

        # Create document record
        doc = LPODocument(
            filename=file.filename,
            status="processing",
        )
        db.add(doc)
        await db.flush()

        # Extract text from PDF
        text = extract_text_from_pdf(file_bytes)
        logger.info(
            "PDF text extraction for '%s': %d chars extracted",
            file.filename,
            len(text) if text else 0,
        )
        if text:
            logger.debug("Extracted text preview: %s", text[:500])

        if not text:
            logger.warning("No text extracted from '%s', marking as error", file.filename)
            doc.status = "error"
            await db.commit()
            documents.append(doc)
            continue

        # Extract structured data using AI or fallback
        try:
            extracted = await extract_lpo_data(text)
            logger.info(
                "Extraction result for '%s': customer='%s', %d line items",
                file.filename,
                extracted.get("customer_name", "Unknown"),
                len(extracted.get("line_items", [])),
            )
            if not extracted.get("line_items"):
                logger.warning(
                    "No line items extracted from '%s'. Text content: %s",
                    file.filename,
                    text[:1000],
                )
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
        except Exception as e:
            logger.error("Extraction failed for '%s': %s", file.filename, str(e))
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
    procurement_map = defaultdict(lambda: {"total_quantity": 0.0, "unit": "", "item_ids": [], "item_statuses": []})
    for item in items:
        key = (item.item_name.lower(), item.unit.lower())
        procurement_map[key]["total_quantity"] += item.quantity
        procurement_map[key]["unit"] = item.unit
        procurement_map[key]["item_ids"].append(item.id)
        procurement_map[key]["item_statuses"].append(item.status or "pending")

    master_procurement = [
        MasterProcurementItem(
            item_name=key[0].title(),
            total_quantity=data["total_quantity"],
            unit=data["unit"],
            item_ids=data["item_ids"],
            item_statuses=data["item_statuses"],
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

    item.status = body.status
    await db.commit()

    return {"item_id": item_id, "status": body.status}


@router.get("/export")
async def export_data(
    format: str = "xlsx",
    date: Optional[str] = None,
    type: str = "raw",
    db: AsyncSession = Depends(get_db),
):
    """Export LPO data as a downloadable file (CSV or Excel).

    Query Parameters:
        format: Export format ('csv' or 'xlsx', defaults to 'xlsx')
        date: Date filter in YYYY-MM-DD format (defaults to today)
        type: 'raw' for raw LPO data, 'picklist' for consolidated pick list
    """
    if format not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'xlsx'.")

    if type not in ("raw", "picklist"):
        raise HTTPException(
            status_code=400, detail="Type must be 'raw' or 'picklist'."
        )

    # Determine target date
    from datetime import date as date_type

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
            )
    else:
        target_date = date_type.today()

    # Query line items for the target date with their documents
    query = (
        select(LPOLineItem)
        .where(LPOLineItem.date_extracted == target_date)
        .options(selectinload(LPOLineItem.document))
    )
    result = await db.execute(query)
    items = result.scalars().all()

    # Build data structures used by both formats
    if type == "raw":
        raw_items = [
            {
                "date": item.date_extracted.isoformat(),
                "customer_name": item.document.customer_name or "Unknown",
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit": item.unit,
            }
            for item in items
        ]
    else:
        procurement_map = defaultdict(
            lambda: {"total_quantity": 0.0, "unit": ""}
        )
        for item in items:
            key = (item.item_name.lower(), item.unit.lower())
            procurement_map[key]["total_quantity"] += item.quantity
            procurement_map[key]["unit"] = item.unit

        master_items = [
            {
                "item_name": key[0].title(),
                "total_quantity": data["total_quantity"],
                "unit": data["unit"],
            }
            for key, data in procurement_map.items()
        ]

        distribution_map = defaultdict(list)
        for item in items:
            customer = item.document.customer_name or "Unknown"
            distribution_map[customer].append(
                {
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                }
            )

        distribution = [
            {"customer_name": customer, "items": items_list}
            for customer, items_list in distribution_map.items()
        ]

    import io

    if format == "csv":
        if type == "raw":
            csv_content = generate_raw_data_csv(raw_items)
            filename = f"lpo_raw_data_{target_date.isoformat()}.csv"
        else:
            csv_content = generate_pick_list_csv(master_items, distribution)
            filename = f"marikiti_pick_list_{target_date.isoformat()}.csv"

        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Excel (xlsx) format
    from backend.services.sheets_export import generate_excel_export

    if type == "raw":
        excel_bytes = generate_excel_export(raw_items=raw_items)
        filename = f"lpo_raw_data_{target_date.isoformat()}.xlsx"
    else:
        excel_bytes = generate_excel_export(
            master_items=master_items, distribution=distribution
        )
        filename = f"marikiti_pick_list_{target_date.isoformat()}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
