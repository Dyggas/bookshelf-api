import uuid
from datetime import datetime

from pydantic import BaseModel


class AuthorBrief(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}
