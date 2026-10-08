import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import config
from .db import Base, engine, get_db
from .models import AttentionRecord
from .schemas import AttentionIn, AttentionOut

logger = logging.getLogger("attention")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not config.API_KEY:
        logger.warning("API_KEY is not set: authentication is DISABLED")
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Attention Monitoring API", version="0.1.0", lifespan=lifespan)


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if config.API_KEY and not secrets.compare_digest(x_api_key, config.API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/attention", status_code=201, dependencies=[Depends(require_api_key)])
def create_record(payload: AttentionIn, db: Session = Depends(get_db)):
    record = AttentionRecord(
        session_id=payload.session_id,
        student_id=payload.student_id,
        timestamp=payload.to_datetime(),
        attention_score=payload.attention_score,
        ear=payload.ear,
        yaw=payload.yaw,
        pitch=payload.pitch,
        roll=payload.roll,
    )
    db.add(record)
    db.commit()
    return {"id": record.id}


@app.get(
    "/attention",
    response_model=list[AttentionOut],
    dependencies=[Depends(require_api_key)],
)
def list_records(
    student_id: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(AttentionRecord).order_by(AttentionRecord.timestamp.desc()).limit(limit)
    if student_id:
        stmt = stmt.where(AttentionRecord.student_id == student_id)
    return db.scalars(stmt).all()
