import { useEffect, useState } from "react";
import { api } from "../api/client";
import { DueLevel, dueBadgeClass, dueLabel, dueSegClass, formatDue } from "../utils/due";

type Rail = { id: number; label: string; length_cm: number };
type Seg = {
  order_id: number;
  ticket_code: string;
  garment_name: string;
  start_cm: number;
  end_cm: number;
  due_at: string;
  due_level: DueLevel;
};
type Occ = { rail_id: number; label: string; length_cm: number; segments: Seg[] };

export default function OccupancyPage() {
  const [rails, setRails] = useState<Rail[]>([]);
  const [railId, setRailId] = useState<number | null>(null);
  const [map, setMap] = useState<Occ | null>(null);

  useEffect(() => {
    api<Rail[]>("/rails").then((rs) => {
      setRails(rs);
      setRailId((cur) => cur ?? rs[0]?.id ?? null);
    });
  }, []);

  // 切换挂杆即重新拉取；预警完全随响应 segments 刷新。
  useEffect(() => {
    if (railId == null) {
      setMap(null);
      return;
    }
    let alive = true;
    api<Occ>(`/occupancy/${railId}`).then((m) => {
      if (alive) setMap(m);
    });
    return () => {
      alive = false;
    };
  }, [railId]);

  return (
    <>
      <h2>占位图（横向尺线）</h2>
      <div className="toolbar">
        <label>
          挂杆：{" "}
          <select value={railId ?? ""} onChange={(e) => setRailId(Number(e.target.value))}>
            {rails.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}（{r.length_cm}cm）
              </option>
            ))}
          </select>
        </label>
        <span className="occ-legend">
          <i className="due-badge due-badge--overdue">已逾期</i>
          <i className="due-badge due-badge--due_soon">不足12小时</i>
          <i className="due-badge due-badge--ok">尚余充足</i>
        </span>
      </div>

      {!rails.length && <p>暂无挂杆</p>}

      {map && (
        <div className="ruler-wrap">
          <div className="ruler-label">
            <span>{map.label}</span>
            <span className="mono">
              0 — {map.length_cm} cm
            </span>
          </div>
          <div className="ruler">
            {map.segments.map((s) => (
              <div
                key={s.order_id}
                className={dueSegClass(s.due_level)}
                style={{
                  left: `${(s.start_cm / map.length_cm) * 100}%`,
                  width: `${((s.end_cm - s.start_cm) / map.length_cm) * 100}%`,
                }}
                title={`${s.ticket_code} ${s.garment_name} ${s.start_cm}-${s.end_cm}cm · 到期 ${formatDue(s.due_at)}（${dueLabel(s.due_level)}）`}
              >
                {s.garment_name}
              </div>
            ))}
          </div>

          <table className="table occ-warn">
            <thead>
              <tr>
                <th>票号</th>
                <th>衣物</th>
                <th>占位 cm</th>
                <th>到期</th>
                <th>预警</th>
              </tr>
            </thead>
            <tbody>
              {map.segments.map((s) => (
                <tr key={s.order_id} className={`occ-warn-row occ-warn-row--${s.due_level}`}>
                  <td className="mono">{s.ticket_code}</td>
                  <td>{s.garment_name}</td>
                  <td className="mono">
                    {s.start_cm}–{s.end_cm}
                  </td>
                  <td className="mono">{formatDue(s.due_at)}</td>
                  <td>
                    <i className={dueBadgeClass(s.due_level)}>{dueLabel(s.due_level)}</i>
                  </td>
                </tr>
              ))}
              {!map.segments.length && (
                <tr>
                  <td colSpan={5}>本杆暂无在挂工单</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
