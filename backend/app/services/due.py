"""工单到期分档：与逾期扫描共用同一时间基准（naive UTC）。"""

from __future__ import annotations

from datetime import datetime, timedelta

DUE_WARN_HOURS = 12

DUE_OVERDUE = "overdue"
DUE_SOON = "due_soon"
DUE_OK = "ok"


def classify_due(due_at: datetime, now: datetime | None = None) -> str:
    """按到期时间返回 overdue / due_soon / ok。

    - overdue: 已到到期时间（due_at <= now）
    - due_soon: 距到期不足 DUE_WARN_HOURS 小时（now < due_at <= now + 阈值）
    - ok: 尚余充足
    """
    if now is None:
        now = datetime.utcnow()
    if due_at <= now:
        return DUE_OVERDUE
    if due_at <= now + timedelta(hours=DUE_WARN_HOURS):
        return DUE_SOON
    return DUE_OK
