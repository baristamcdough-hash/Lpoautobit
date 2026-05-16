import asyncio
from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session using in-memory SQLite."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Create an async test client with overridden database dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_bytes():
    """Generate a simple valid PDF with text content for testing."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(200, 10, text="LOCAL PURCHASE ORDER", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, text="Customer: Safari Hotel", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text=f"Date: {date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="Items Ordered:", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="5 Crates Tomatoes", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="10 Bags Potatoes", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="3 Bunches Sukuma Wiki", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()
