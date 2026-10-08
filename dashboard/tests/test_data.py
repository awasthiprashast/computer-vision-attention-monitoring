import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import build_report_pdf, list_students, load_records, summarize  # noqa: E402


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with eng.begin() as conn:
        conn.execute(text(
            "CREATE TABLE attention_records (id INTEGER PRIMARY KEY, session_id TEXT, student_id TEXT,"
            " timestamp TIMESTAMP, attention_score INTEGER, ear REAL, yaw REAL, pitch REAL, roll REAL)"
        ))
        rows = [("s1", "alice", f"2026-01-01 10:00:0{i}", 60 + i * 10) for i in range(3)]
        rows += [("s2", "bob", "2026-01-01 10:00:05", 40)]
        for sid, stu, ts, score in rows:
            conn.execute(text(
                "INSERT INTO attention_records"
                " (session_id, student_id, timestamp, attention_score, ear, yaw, pitch, roll)"
                " VALUES (:sid, :stu, :ts, :score, 0.3, 0, 0, 0)"
            ), {"sid": sid, "stu": stu, "ts": ts, "score": score})
    return eng


def test_list_students(engine):
    assert list_students(engine) == ["alice", "bob"]


def test_load_records_newest_first_and_limit(engine):
    df = load_records(engine, limit=2)
    assert len(df) == 2
    assert df["timestamp"].is_monotonic_decreasing
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])


def test_load_records_filters_students(engine):
    df = load_records(engine, student_ids=["bob"])
    assert set(df["student_id"]) == {"bob"}
    assert len(df) == 1


def test_summarize(engine):
    summary = summarize(load_records(engine)).set_index("student_id")
    assert summary.loc["alice", "avg"] == 70.0
    assert summary.loc["alice", "min"] == 60
    assert summary.loc["alice", "max"] == 80
    assert summary.loc["bob", "samples"] == 1


def test_report_is_a_pdf(engine):
    pdf = build_report_pdf(load_records(engine))
    assert pdf.startswith(b"%PDF")
