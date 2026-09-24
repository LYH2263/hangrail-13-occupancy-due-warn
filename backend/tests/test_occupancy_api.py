import os
from datetime import datetime, timedelta

# 必须在导入 app.* 之前：app.database 会按 DATABASE_URL 立即创建 engine。
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import HangRail, RailPlacement, Store, WorkOrder
from app.services.due import DUE_WARN_HOURS, classify_due


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    def _get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    yield TestClient(app), TestingSession
    app.dependency_overrides.clear()


def _seed(session, specs):
    """specs: list of (ticket, due_delta, start_cm, end_cm)"""
    store = Store(name="测试店")
    session.add(store)
    session.flush()
    rail = HangRail(store_id=store.id, label="T 杆", length_cm=200)
    session.add(rail)
    session.flush()
    now = datetime.utcnow()
    for ticket, delta, start, end in specs:
        order = WorkOrder(
            store_id=store.id,
            ticket_code=ticket,
            garment_name="测试衣物",
            length_cm=end - start,
            status="hung",
            due_at=now + delta,
            hung_at=now,
        )
        session.add(order)
        session.flush()
        session.add(
            RailPlacement(rail_id=rail.id, order_id=order.id, start_cm=start, end_cm=end)
        )
    session.commit()
    return rail.id


def test_occupancy_segments_carry_due_at_and_levels(client):
    c, Session = client
    with Session() as db:
        rail_id = _seed(
            db,
            [
                ("T-1", timedelta(hours=-1), 0, 30),       # 已逾期
                ("T-2", timedelta(hours=5), 30, 60),       # 不足 12 小时
                ("T-3", timedelta(days=2), 60, 90),        # 尚余充足
            ],
        )

    resp = c.get(f"/api/occupancy/{rail_id}")
    assert resp.status_code == 200
    segs = resp.json()["segments"]

    by_ticket = {s["ticket_code"]: s for s in segs}
    # 契约：每个在挂段都必须带 due_at（可解析 ISO）与 due_level
    for s in segs:
        assert "due_at" in s
        datetime.fromisoformat(s["due_at"])
        assert s["due_level"] in ("overdue", "due_soon", "ok")

    assert by_ticket["T-1"]["due_level"] == "overdue"
    assert by_ticket["T-2"]["due_level"] == "due_soon"
    assert by_ticket["T-3"]["due_level"] == "ok"

    # due_at 与工单接口同一来源：同票号字符串一致
    orders = c.get("/api/orders").json()
    order_due = {o["ticket_code"]: o["due_at"] for o in orders}
    for s in segs:
        assert s["due_at"] == order_due[s["ticket_code"]]


def test_order_out_also_carries_due_level(client):
    c, Session = client
    with Session() as db:
        _seed(db, [("T-9", timedelta(hours=-2), 0, 30)])
    orders = c.get("/api/orders").json()
    assert orders[0]["due_level"] == "overdue"


def test_classify_due_boundary():
    now = datetime(2026, 9, 23, 12, 0, 0)
    assert classify_due(now - timedelta(seconds=1), now) == "overdue"
    assert classify_due(now, now) == "overdue"
    assert classify_due(now + timedelta(seconds=1), now) == "due_soon"
    assert classify_due(
        now + timedelta(hours=DUE_WARN_HOURS), now
    ) == "due_soon"
    assert classify_due(
        now + timedelta(hours=DUE_WARN_HOURS, seconds=1), now
    ) == "ok"
