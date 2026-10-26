export type Sex = "Male" | "Female";
export type Score = { deviance: number; annuity_error: number[]; coverage: number };
export type Price = { age: number; rate: number; adj: number; median: number; lo: number; hi: number; width_pct: number };
export type Fan = {
  model: string;
  jump_off: number;
  years: number[];
  median: number[];
  lo: number[];
  hi: number[];
  observed_years: number[];
  observed: number[];
  covid: number[];
};

export type Run = { key: string; label: string; exploratory: boolean } & Record<Sex, { model: string; jump_off: number; prices: Price[] }>;
export type BySex = { years: number[] } & Record<Sex, number[]>;

export type Candidate = { deviance: number; wins: number; abs_annuity_error: number; coverage: number };
export type Rolling = {
  origins: number[];
  horizon: number;
  chosen: Record<Sex, string>;
  windows: Record<string, string>;
  by_sex: Record<Sex, { winners: string[]; candidates: Record<string, Candidate> }>;
  readings: { R1: Record<Sex, boolean>; R2: Record<Sex, boolean>; lowest: Record<Sex, string> };
  weights: Record<Sex, Record<string, number>>;
  reprice: Record<Sex, { jump_offs: number[]; quotes: Record<string, { price: number | null; failed: number }[]> }>;
};
export type Blend = Record<Sex, { model: string; chosen: string; jump_off: number; prices: Price[] }>;

export type Research = {
  source: string;
  protocol: string;
  backtest: {
    validation: Record<string, Record<Sex, Score>>;
    windows: Record<string, string>;
    tests: { chosen: Record<Sex, string> } & Record<"P1" | "P2" | "P3" | "P4", Record<Sex, boolean>>;
  };
  annuities: Record<Sex, { model: string; jump_off: number; prices: Price[] }>;
  fan: Record<Sex, Fan>;
  history?: { years: number[]; e0: Record<Sex, number[]>; e65: Record<Sex, number[]> };
  compare?: { runs: Run[]; completeness: BySex; exposure: BySex; rolling_wpp?: Rolling };
  rolling?: Rolling | null;
  blend?: Blend | null;
};

export type Quote = Price & { sex: Sex; model: string; jump_off: number; lower_bound: boolean };

const get = async <T,>(path: string): Promise<T> => {
  const r = await fetch(path);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail ?? `${r.status} ${r.statusText}`);
  }
  return r.json();
};

export const api = {
  research: () => get<Research>("/api/research"),
  price: (sex: Sex, age: number, rate: number, adj: number) =>
    get<Quote>(`/api/price?sex=${sex}&age=${age}&rate=${rate}&adj=${adj}`),
};
