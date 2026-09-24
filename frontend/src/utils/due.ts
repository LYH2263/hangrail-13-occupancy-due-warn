// 到期展示唯一出口：时间与分档全部来自后端，前端只渲染、不做任何到期推算。

export type DueLevel = "overdue" | "due_soon" | "ok";

// 仅用于格式化后端下发的到期时间戳，禁止在此与本机时间比较。
export function formatDue(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function dueLabel(level: DueLevel): string {
  switch (level) {
    case "overdue":
      return "已逾期";
    case "due_soon":
      return "不足12小时";
    case "ok":
      return "尚余充足";
  }
}

export function dueSegClass(level: DueLevel): string {
  return `seg seg--${level}`;
}

export function dueBadgeClass(level: DueLevel): string {
  return `due-badge due-badge--${level}`;
}
