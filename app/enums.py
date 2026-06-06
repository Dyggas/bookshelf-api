import enum


class Genre(str, enum.Enum):
    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    SCIENCE_FICTION = "science_fiction"
    FANTASY = "fantasy"
    MYSTERY = "mystery"
    THRILLER = "thriller"
    ROMANCE = "romance"
    HORROR = "horror"
    HISTORICAL = "historical"
    BIOGRAPHY = "biography"
    POETRY = "poetry"
    DRAMA = "drama"
