from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Metadata root shared by SQLAlchemy mappings and Alembic."""
