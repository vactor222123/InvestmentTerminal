from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class BaseModel:
    """
    Base class for all models.
    """

    created_at: datetime | None = None
    updated_at: datetime | None = None