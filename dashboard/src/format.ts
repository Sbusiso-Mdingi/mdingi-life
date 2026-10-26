export const pct = (v: number | null | undefined, digits = 1) =>
  v == null ? "n/a" : `${v < 0 ? "−" : ""}${Math.abs(v * 100).toFixed(digits)}%`;

export const num = (v: number | null | undefined, digits = 2) =>
  v == null ? "n/a" : `${v < 0 ? "−" : ""}${Math.abs(v).toFixed(digits)}`;

export const thousands = (v: number) => Math.round(v).toLocaleString("en-ZA").replace(/\s/g, ",");

export const SEX_LABEL = { Male: "Men", Female: "Women" } as const;

/** Rand amounts in millions, one decimal, with thousands separators. */
export const millions = (v: number, digits = 1) =>
  `${v < 0 ? "−" : ""}${Math.abs(v / 1e6).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
