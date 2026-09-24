// 到期时间一律取自后端返回的 due_at（与工单到期字段同一来源），
// 前端只负责按当前时间分档与展示，禁止本地编造到期时间戳。

export type DueLevel = "overdue" | "due-soon" | "safe";

export const DUE_SOON_MS = 12 * 60 * 60 * 1000; // 距到期不足 12 小时

export function dueLevel(dueAt: string, now: number = Date.now()): DueLevel {
  const ms = new Date(dueAt).getTime();
  if (Number.isNaN(ms)) return "safe";
  if (ms < now) return "overdue";
  if (ms - now < DUE_SOON_MS) return "due-soon";
  return "safe";
}

// 与工单页、占位段共用同一展示格式，保证同票展示一致
export function formatDue(dueAt: string): string {
  const d = new Date(dueAt);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

function humanDuration(ms: number): string {
  const hours = Math.floor(ms / 3_600_000);
  if (hours >= 1) return `${hours} 小时`;
  return `${Math.max(1, Math.round(ms / 60_000))} 分钟`;
}

export function dueHint(dueAt: string, now: number = Date.now()): string {
  const ms = new Date(dueAt).getTime();
  if (Number.isNaN(ms)) return "";
  const diff = ms - now;
  if (diff < 0) return `已逾期 ${humanDuration(-diff)}`;
  if (diff < DUE_SOON_MS) return `${humanDuration(diff)}后到期`;
  return "尚余充足";
}
