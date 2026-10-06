// Calendar dates carry no workout time. Format in UTC only to preserve their components.
export function formatCalendarDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("en-US", { timeZone: "UTC", weekday: "short", month: "short", day: "numeric" })
    .format(new Date(Date.UTC(year, month - 1, day)));
}

export function datesInWeek(weekStart: string): string[] {
  const [year, month, day] = weekStart.split("-").map(Number);
  return Array.from({ length: 7 }, (_, offset) => new Date(Date.UTC(year, month - 1, day + offset)).toISOString().slice(0, 10));
}
