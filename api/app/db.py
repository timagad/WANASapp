"""Database session wiring and pgvector bootstrap."""
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the vector extension, then the schema and its indexes."""
    from app.models import Base

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        # Cosine-distance ANN index over the heritage corpus.
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS heritage_chunk_embedding_idx "
                "ON heritage_chunks USING hnsw (embedding vector_cosine_ops)"
            )
        )
        # Lexical half of the hybrid retriever.
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS heritage_chunk_fts_idx "
                "ON heritage_chunks USING gin (to_tsvector('simple', search_text))"
            )
        )
