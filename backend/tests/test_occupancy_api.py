from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.router import api_router
from app.database import Base, get_db
from app.models.models import HangRail, RailPlacement, Store, WorkOrder

# 契约：占用接口每个在挂段必须带 due_at，且与工单到期字段同一来源
# （直接取自 WorkOrder.due_at，前端不得本地编造时间戳）。


def _client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    now = datetime(2026, 9, 23, 12, 0, 0)
    with TestingSession() as db:
        store = Store(name="测试店")
        db.add(store)
        db.flush()
        rail = HangRail(store_id=store.id, label="T 杆", length_cm=200)
        db.add(rail)
        db.flush()
        orders = [
            # 已逾期、不足 12 小时、尚余充足 各一单
            WorkOrder(store_id=store.id, ticket_code="T-001", garment_name="大衣",
                      length_cm=40, status="hung", due_at=now - timedelta(hours=6)),
            WorkOrder(store_id=store.id, ticket_code="T-002", garment_name="西装",
                      length_cm=30, status="hung",
                      due_at=now + timedelta(hours=6)),
            WorkOrder(store_id=store.id, ticket_code="T-003", garment_name="风衣",
                      length_cm=50, status="hung",
                      due_at=now + timedelta(days=2)),
        ]
        db.add_all(orders)
        db.flush()
        db.add_all([
            RailPlacement(rail_id=rail.id, order_id=orders[0].id, start_cm=0, end_cm=40, active=1),
            RailPlacement(rail_id=rail.id, order_id=orders[1].id, start_cm=40, end_cm=70, active=1),
            RailPlacement(rail_id=rail.id, order_id=orders[2].id, start_cm=70, end_cm=120, active=1),
        ])
        db.commit()
        due_by_ticket = {o.ticket_code: o.due_at for o in orders}

    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: TestingSession()
    return TestClient(app), due_by_ticket


def test_occupancy_segments_carry_due_at():
    client, due_by_ticket = _client()
    res = client.get("/api/occupancy/1")
    assert res.status_code == 200
    data = res.json()
    assert data["rail_id"] == 1
    assert len(data["segments"]) == 3
    for seg in data["segments"]:
        # 契约断言：占位段含 due_at 时间戳
        assert "due_at" in seg
        parsed = datetime.fromisoformat(seg["due_at"])
        expected = due_by_ticket[seg["ticket_code"]]
        assert parsed == expected


def test_occupancy_due_at_matches_orders_same_source():
    client, _ = _client()
    occ = client.get("/api/occupancy/1").json()
    orders = {o["ticket_code"]: o["due_at"] for o in client.get("/api/orders").json()}
    for seg in occ["segments"]:
        # 同一票号：占位段与工单页到期展示来自同一字段
        assert seg["due_at"] == orders[seg["ticket_code"]]


def test_occupancy_due_at_reflects_overdue_and_soon():
    # 三档所需时间由后端 due_at 表达，前端仅据此分档：
    # 逾期单 due_at 在过去，临期单距 now < 12h，充足单在 12h 之外
    client, due_by_ticket = _client()
    occ = client.get("/api/occupancy/1").json()
    by_ticket = {s["ticket_code"]: s for s in occ["segments"]}
    assert by_ticket["T-001"]["due_at"] < "2026-09-23T12:00:00"
    assert due_by_ticket["T-002"] - due_by_ticket["T-001"] == timedelta(hours=12)
    assert by_ticket["T-003"]["due_at"] > "2026-09-23T12:00:00"
