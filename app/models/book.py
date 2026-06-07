import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Book(TimestampMixin, Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("year >= 1800", name="books_year_min"),
        CheckConstraint(
            "year <= EXTRACT(YEAR FROM CURRENT_DATE)", name="books_year_max"
        ),
        UniqueConstraint("title", "author_id", name="uq_books_title_author"),
        Index("ix_books_year", "year"),
        Index("ix_books_author_id", "author_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authors.id", ondelete="RESTRICT"), nullable=False
    )
    genre: Mapped[str] = mapped_column(nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    author: Mapped["Author"] = relationship(lazy="selectin")
