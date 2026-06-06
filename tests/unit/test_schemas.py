import pytest
from pydantic import ValidationError

from app.enums import Genre
from app.schemas.auth import RegisterRequest
from app.schemas.book import BookCreate, BookFilters, BookUpdate


class TestBookCreate:
    def test_valid_book(self):
        book = BookCreate(
            title="Kobzar", author="Taras Shevchenko", genre=Genre.POETRY, year=1840
        )
        assert book.title == "Kobzar"
        assert book.author == "Taras Shevchenko"
        assert book.genre == Genre.POETRY
        assert book.year == 1840

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            BookCreate(
                title="", author="Taras Shevchenko", genre=Genre.POETRY, year=1840
            )
        assert "title" in str(exc_info.value)

    def test_whitespace_only_title_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            BookCreate(
                title="   ", author="Taras Shevchenko", genre=Genre.POETRY, year=1840
            )
        assert "title" in str(exc_info.value)

    def test_title_too_long(self):
        with pytest.raises(ValidationError) as exc_info:
            BookCreate(
                title="x" * 501,
                author="Taras Shevchenko",
                genre=Genre.POETRY,
                year=1840,
            )
        assert "title" in str(exc_info.value)

    def test_title_at_max_length(self):
        book = BookCreate(
            title="x" * 500, author="Taras Shevchenko", genre=Genre.POETRY, year=1840
        )
        assert len(book.title) == 500

    def test_empty_author_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            BookCreate(title="Kobzar", author="", genre=Genre.POETRY, year=1840)
        assert "author" in str(exc_info.value)

    def test_year_below_1800_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            BookCreate(
                title="Kobzar",
                author="Taras Shevchenko",
                genre=Genre.POETRY,
                year=1799,
            )
        assert "year" in str(exc_info.value)

    def test_year_1800_accepted(self):
        book = BookCreate(
            title="Some Book", author="Author", genre=Genre.FICTION, year=1800
        )
        assert book.year == 1800

    def test_year_above_current_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            BookCreate(
                title="Future Book",
                author="Author",
                genre=Genre.FICTION,
                year=2027,
            )
        assert "year" in str(exc_info.value)

    def test_invalid_genre_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            BookCreate(
                title="Kobzar",
                author="Taras Shevchenko",
                genre="cooking",
                year=1840,
            )
        assert "genre" in str(exc_info.value)

    def test_all_valid_genres(self):
        for genre in Genre:
            book = BookCreate(title="Book", author="Author", genre=genre, year=2000)
            assert book.genre == genre


class TestBookUpdate:
    def test_all_fields_none_accepted(self):
        update = BookUpdate()
        assert update.title is None
        assert update.author is None
        assert update.genre is None
        assert update.year is None

    def test_partial_update_title_only(self):
        update = BookUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.author is None

    def test_partial_update_genre_only(self):
        update = BookUpdate(genre=Genre.FANTASY)
        assert update.genre == Genre.FANTASY
        assert update.title is None

    def test_invalid_value_still_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            BookUpdate(year=1799)
        assert "year" in str(exc_info.value)

    def test_empty_title_rejected_when_provided(self):
        with pytest.raises(ValidationError) as exc_info:
            BookUpdate(title="")
        assert "title" in str(exc_info.value)


class TestRegisterRequest:
    def test_valid_registration(self):
        req = RegisterRequest(email="user@example.com", password="secret123")
        assert req.email == "user@example.com"
        assert req.password == "secret123"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="not-an-email", password="secret123")
        assert "email" in str(exc_info.value)

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="user@example.com", password="short")
        assert "password" in str(exc_info.value)

    def test_password_at_min_length(self):
        req = RegisterRequest(email="user@example.com", password="12345678")
        assert len(req.password) == 8

    def test_password_too_long(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="user@example.com", password="x" * 129)
        assert "password" in str(exc_info.value)


class TestBookFilters:
    def test_no_filters(self):
        filters = BookFilters()
        assert filters.title is None
        assert filters.author is None
        assert filters.genre is None
        assert filters.year_from is None
        assert filters.year_to is None

    def test_partial_filters(self):
        filters = BookFilters(genre=Genre.FICTION, year_from=1900)
        assert filters.genre == Genre.FICTION
        assert filters.year_from == 1900
        assert filters.title is None

    def test_invalid_year_from(self):
        with pytest.raises(ValidationError) as exc_info:
            BookFilters(year_from=1799)
        assert "year_from" in str(exc_info.value)

    def test_invalid_year_to(self):
        with pytest.raises(ValidationError) as exc_info:
            BookFilters(year_to=2027)
        assert "year_to" in str(exc_info.value)
