export function asList(value: unknown): unknown[] {
  if (value == null) return [];
  return Array.isArray(value) ? value : [value];
}

export function textOf(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") {
    const s = value.trim();
    return s || null;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      const t = textOf(item);
      if (t) return t;
    }
    return null;
  }
  if (typeof value === "object") {
    const rec = value as Record<string, unknown>;
    for (const key of ["@value", "text", "name", "value", "caption", "description"]) {
      if (key in rec) {
        const t = textOf(rec[key]);
        if (t) return t;
      }
    }
  }
  return null;
}

export function hasText(node: Record<string, unknown>, ...keys: string[]): boolean {
  for (const key of keys) {
    if (textOf(node[key]) != null) return true;
  }
  return false;
}

export function nonempty(value: unknown): boolean {
  if (value == null) return false;
  if (value === "" || (Array.isArray(value) && value.length === 0)) return false;
  if (typeof value === "object" && !Array.isArray(value) && Object.keys(value as object).length === 0) {
    return false;
  }
  if (typeof value === "string" && !value.trim()) return false;
  return true;
}
