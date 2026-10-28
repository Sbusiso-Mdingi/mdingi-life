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

export type Sheet = {
  bel: Record<"annuities" | "funeral" | "total", number>;
  risk_margin: number;
  scr_life: number;
  market: number;
  bscr: number;
  scr: number;
  cover: number;
  own_funds: number;
  op: number;
  inflation: number;
  life: Record<"mortality" | "longevity" | "lapse" | "expense" | "catastrophe", number>;
  interest: Record<"nominal" | "real" | "combined", number>;
};
export type DV01 = Record<"real" | "nominal", { liability: Record<string, number>; portfolio: Record<string, number> }>;
export type Ages = { from: number[]; n: number[] };
export type Pensioner = { id: number; sex: Sex; age_at_purchase: number; years_since_purchase: number; age: number; type: "inflation-linked" | "level"; income: number };
export type FuneralPolicy = { id: number; sex: Sex; entry_age: number; years_in_force: number; age: number; sum_assured: number; premium: number };
export type Book = {
  annuities: { n: number; income: number; median_income: number; types: Record<string, number>; sexes: Record<Sex, number>; ages: Ages; median_age: number; sample: Pensioner[] };
  funeral: {
    n: number;
    cover: number;
    premiums: number;
    sums: Record<string, number>;
    sexes: Record<Sex, number>;
    ages: Ages;
    median_age: number;
    median_premium: number;
    sample: FuneralPolicy[];
  };
  premium_rates: Record<Sex, { age: number; per_rand: number; fixed: number }[]>;
  sums: number[];
};
export type V3 = {
  protocol: string;
  valuation_date: string;
  curve_dates: Record<"real" | "nominal", string>;
  main: Sheet & {
    bel_parts: Record<"income" | "ann_expenses" | "claims" | "premiums" | "fun_expenses", number>;
    lapse: Record<"up" | "down" | "level" | "mass" | "combined", number>;
    rate_losses: Record<string, number>;
    op_detail: { earned_premiums: number; premiums: number; provisions: number; charge: number };
    policies: Record<"annuities" | "funeral", number>;
    capital_for: Record<string, number>;
    assets: Record<"total" | "bill" | "matched", number>;
    matching: Record<"real" | "nominal", { liability: Risk; bonds: Record<string, { duration: number; value: number }> }>;
    scr_ru: { t0: number; annuity_weight: number; by_year: number[] };
    dv01: DV01;
  };
  book?: Book | null;
  unmatched: Sheet;
  sensitivities: Record<string, Sheet>;
  key_rate?: Sheet & {
    rate_losses: Record<string, number>;
    checks: { K6: { key_rate: number; duration: number; pass: boolean } };
    holdings: Record<"real" | "nominal", Record<string, number>>;
    dv01: DV01;
  };
  checks: {
    K1: { worst_relative: number; pass: boolean; scenarios: number };
    K3: { matched: number; unmatched: number; ratio: number; pass: boolean };
    K4: { largest: string; pass: boolean };
    K5: { cover: number; industry_median: number };
  };
};

export type Pct = Record<"5" | "25" | "50" | "75" | "95", number[]>;
export type Spread = {
  cover: Pct;
  below_one_share: number;
  below_one_by_year: number[];
  worst: number;
  A1: { share_covered: number; pass: boolean };
};
type Esg = {
  factors: number;
  tau: Record<"nominal" | "real", number>;
  phi: number[];
  checks: {
    E1: Record<"nominal" | "real", { scenario_sd: number; history_sd: number; ratio: number; pass: boolean }>;
    E2: Record<"nominal" | "real", { scenario_q005: number; sam_down_10y: number; spot_10y: number }>;
  };
};
export type Stress = {
  cover: number[];
  own_funds: number[];
  scr: number[];
  capital_to_restore: number;
  worst_year: number;
  A2: boolean;
  csm: number[];
  profit: number[];
  service_result: number[];
  csm_used: number;
  losses: number;
};
export type Ifrs = {
  csm_transition: Record<"annuities" | "funeral", number>;
  csm: number[];
  equity: number[];
  profit: number[];
  service_result: number[];
  finance_result: number[];
};

export type CapitalLevel = { own_funds: number; scr: number; cover: number; share_covered: number; below_one_by_year?: number[]; stresses: Record<string, number> };

export type V4 = {
  protocol: string;
  valuation_date: string;
  esg: Esg & {
    ten_year: Record<"nominal" | "real", Pct & { central: number[] }>;
    history: Record<"nominal" | "real", { years: number[]; rate: number[] }>;
    frozen_three_factor: Esg & { cover: Spread };
    covid_excluded: Esg;
  };
  central: { cover: number; own_funds: number; scr: number; assets: number; risk_margin: number; bel: Record<"annuities" | "funeral" | "total", number> }[];
  scenarios: Spread & { profit: Pct; own_funds: Pct };
  stresses: Record<string, Stress>;
  pandemic_ratio: Record<Sex, number>;
  ifrs17: Record<string, Ifrs>;
  transition: { ra: Record<"annuities" | "funeral", number>; confidence: number; csm: Record<"annuities" | "funeral", number> };
  sensitivities: { covid_excluded: Spread; no_rematch: Spread; no_rematch_central: { cover: number[] } };
  checks: {
    R1: { worst: number; pass: boolean };
    R2: { worst_relative: number; pass: boolean };
    E1: Esg["checks"]["E1"];
    A1: { share_covered: number; pass: boolean };
    A2: Record<string, boolean>;
  };
  capital?: { rule: string; levels: CapitalLevel[] } | null;
};

export type Rate = { per_rand: number; fixed: number };
export type Benefit = "level" | "rising";
export type FuneralPolicyV6 = FuneralPolicy & { benefit: Benefit };
export type BookV6 = {
  weights: Record<"annuities" | "funeral", number>;
  drawn: Record<"annuities" | "funeral", number>;
  annuities: Book["annuities"];
  funeral: Omit<Book["funeral"], "median_premium" | "sample"> & { benefits: Record<Benefit, number>; median_premium: Record<Benefit, number>; sample: FuneralPolicyV6[] };
  premium_rates: Record<Sex, ({ age: number } & Record<Benefit, Rate>)[]>;
  sums: number[];
  margin: number;
  pricing_growth: number;
  expense: number;
};
export type SheetV6 = Sheet & { diversification: number; interest: Sheet["interest"] & { curve: number; volatility: number } };
export type V6 = {
  protocol: string;
  protocol_v5: string;
  valuation_date: string;
  matching: string;
  exposures: Record<"annuities" | "funeral" | "total", number>;
  mix: number;
  scales: Record<"annuities" | "funeral", number>;
  policies: Record<"annuitants" | "funeral", number>;
  trend: Record<"annuities" | "funeral" | "total", number>;
  large: Record<string, number>;
  main: SheetV6 & {
    bel_parts: V3["main"]["bel_parts"];
    rising_claims: number;
    lapse: V3["main"]["lapse"];
    rate_losses: Record<string, number>;
    vol_loss: number;
    risk_margin_parts: Record<"annuities" | "funeral", number>;
    breakeven: number;
    capital_for: Record<string, number>;
    assets: Record<"total" | "bill" | "matched", number>;
    holdings: Partial<Record<"real" | "nominal", Record<string, number>>>;
    dv01: { liability: Record<string, number>; portfolio: Record<string, number> };
  };
  v5_matching: SheetV6;
  unmatched: SheetV6;
  sensitivities: Record<string, SheetV6>;
  checks: {
    D1: { relative: number; pass: boolean };
    D2: { cover: number; pass: boolean };
    D3: { worst: number; pass: boolean };
    D5: { relative: number; lowest_units: number; pass: boolean };
    C4: { pass: boolean };
    C5: { pass: boolean };
    C6: { pass: boolean };
  };
  v5: { bel: Sheet["bel"]; scr: number; risk_margin: number; cover: number; own_funds: number; policies: Record<"annuities" | "funeral", number> };
  book: BookV6;
  projection: V4 | null;
};

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
  v3?: V3;
  v4?: V4 | null;
  v6?: V6 | null;
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
