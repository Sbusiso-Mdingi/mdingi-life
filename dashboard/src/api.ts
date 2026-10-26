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

export type Rmse = { rmse: number; mae: number };
export type Scores = Record<"fixed" | "ilb", { n: number } & Record<string, Rmse | number>>;
export type Kind = "ilb" | "fixed";
export type CurvePrice = { median: number; lo: number; hi: number; implied_flat_rate: number };
export type V2Price = { age: number; adj: number; flat: Record<string, number> } & Record<string, CurvePrice>;
export type Risk = { value: number; duration: number; dv01: Record<string, number> };
export type V2 = {
  protocol: string;
  data: { usable: number; screened: number };
  design: { curves: Scores; all: Scores; chosen: Record<Kind, string> };
  validation: {
    curves: Scores;
    all: Scores;
    without_covid: { curves: Scores; all: Scores };
    tests: Record<Kind, { C1: boolean; C1_rmse: Record<string, number>; C3: boolean; C3_rmse: number; C2?: boolean; C2_rmse?: Record<string, number> }>;
  };
  by_year: Record<Kind, { years: number[]; n: number[] } & Record<string, number[]>>;
  curves: Record<
    Kind,
    { date: string; longest: number; bonds: { bond: string; maturity: number; yield: number }[]; years: number[]; zero: Record<string, number[]>; forwards: Record<string, number[]> }
  >;
} & Record<
  Sex,
  { model: string; jump_off: number; prices: V2Price[]; matching: { annuity: Risk; portfolio: { holdings_per_100_nominal: Record<string, number>; dv01: Record<string, number> }; bonds: Record<string, Risk> } }
>;

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
  compare?: { runs: Run[]; completeness: BySex; exposure: BySex };
  v2?: V2;
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
