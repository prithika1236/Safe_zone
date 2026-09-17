import pytest
import pytest_asyncio
import geoalchemy2.functions
from geoalchemy2.functions import ST_AsBinary, ST_GeogFromText, ST_GeomFromText
from geoalchemy2.types import Geography, Geometry
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.database.session import Base, get_db
from app.main import app
from app.models.crime import CrimeIncident
from app.models.help_point import SafeHelpPoint
from app.models.optimization import OptimizationRun, PRPLocation, RiskScore
from app.models.patrol import LocationUpdate, PatrolAssignment, PatrolUnit
from app.models.sos import SOSRequest
from app.models.user import EmergencyContact, PoliceOfficer, User


# 1. Register SQLite DDL compilation for PostGIS geography/geometry types
@compiles(Geography, "sqlite")
@compiles(Geometry, "sqlite")
def compile_geography_sqlite(element, compiler, **kw):
    return "BLOB"


# 2. Register SQLite function compilation for spatial extraction and insertion functions
@compiles(ST_AsBinary, "sqlite")
def compile_as_binary_sqlite(element, compiler, **kw):
    return compiler.process(element.clauses, **kw)


@compiles(ST_GeogFromText, "sqlite")
@compiles(ST_GeomFromText, "sqlite")
def compile_from_text_sqlite(element, compiler, **kw):
    return compiler.process(element.clauses, **kw)


# 3. Disable spatial index DDL generation on SQLite
@event.listens_for(Base.metadata, "before_create")
def disable_spatial_indexes_sqlite(target, connection, **kw):
    if connection.dialect.name == "sqlite":
        for table in target.tables.values():
            for col in table.columns:
                if isinstance(col.type, (Geography, Geometry)):
                    col.type.spatial_index = False


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
