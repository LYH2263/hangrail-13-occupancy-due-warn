import { useEffect, useState } from "react";
import { api } from "../api/client";
import { dueHint, dueLevel, formatDue } from "../utils/due";
type Rail = { id: number; label: string; length_cm: number };
type Seg = { order_id: number; ticket_code: string; garment_name: string; start_cm: number; end_cm: number; due_at: string };
type Occ = { rail_id: number; label: string; length_cm: number; segments: Seg[] };
export default function OccupancyPage() {
  const [rails, setRails] = useState<Rail[]>([]);
  const [maps, setMaps] = useState<Occ[]>([]);
  const [railId, setRailId] = useState<number | "all">("all");
  // 切换挂杆后重新拉取占位段，三档预警随段一起刷新
  useEffect(() => {
    api<Rail[]>("/rails").then(async rs => {
      setRails(rs);
      const ids = railId === "all" ? rs.map(r => r.id) : [railId];
      const all = await Promise.all(ids.map(id => api<Occ>(`/occupancy/${id}`)));
      setMaps(all);
    });
  }, [railId]);
  const shown = maps;
  return (<>
    <h2>占位图（横向尺线）</h2>
    <div className="toolbar">
      <label>挂杆
        <select className="rail-select" value={railId} onChange={e => setRailId(e.target.value === "all" ? "all" : Number(e.target.value))}>
          <option value="all">全部挂杆</option>
          {rails.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}
        </select>
      </label>
      <span className="due-legend">
        <i className="dot dot--overdue" />已逾期
        <i className="dot dot--due-soon" />不足 12 小时
        <i className="dot dot--safe" />尚余充足
      </span>
    </div>
    {shown.map(m => (
      <div className="ruler-wrap" key={m.rail_id}>
        <div className="ruler-label"><span>{m.label}</span><span className="mono">0 — {m.length_cm} cm</span></div>
        <div className="ruler">
          {m.segments.map((s) => {
            const lvl = dueLevel(s.due_at);
            return (
              <div key={s.order_id} className={`seg seg--${lvl}`} style={{ left: `${(s.start_cm / m.length_cm) * 100}%`, width: `${((s.end_cm - s.start_cm) / m.length_cm) * 100}%` }}
                title={`${s.ticket_code} · ${s.garment_name} · ${s.start_cm}-${s.end_cm}cm · 到期 ${formatDue(s.due_at)}（${dueHint(s.due_at)}）`}>
                <span className="seg-code">{s.ticket_code}</span>
                <span className="seg-name">{s.garment_name}</span>
                <span className="seg-due">{formatDue(s.due_at)}</span>
              </div>
            );
          })}
        </div>
      </div>
    ))}
    {!rails.length && <p>暂无挂杆</p>}
  </>);
}
