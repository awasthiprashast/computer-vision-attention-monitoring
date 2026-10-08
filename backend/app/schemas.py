from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class AttentionIn(BaseModel):
    """Payload sent by the client once per interval."""

    session_id: str = Field(min_length=1, max_length=64)
    student_id: str = Field(min_length=1, max_length=64)
    timestamp: float = Field(description="Unix epoch seconds")
    attention_score: int = Field(ge=0, le=100)
    ear: float = Field(ge=0, le=1)
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0

    def to_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=UTC)


class AttentionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    student_id: str
    timestamp: datetime
    attention_score: int
    ear: float
    yaw: float
    pitch: float
    roll: float
