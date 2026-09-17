from typing import AsyncGenerator
import geoalchemy2.functions
from geoalchemy2.functions import ST_AsBinary, ST_GeogFromText, ST_GeomFromText
from geoalchemy2.types import Geography, Geometry
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

settings = get_settings()

Base = declarative_base()

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


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

