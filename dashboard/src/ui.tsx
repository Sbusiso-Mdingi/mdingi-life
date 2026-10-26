import type { ReactNode } from "react";
import type { Kind, Price, Rmse, Sex, V2 } from "./api";
import { millions, num } from "./format";

export const SEXES: Sex[] = ["Male", "Female"];
export const COLOR: Record<Sex, string> = { Male: "var(--men)", Female: "var(--women)" };
export const AGES = [55, 65, 75];
export const RATES = [0.02, 0.04, 0.06];
export const ADJS = [0.6, 0.7, 0.8];
export const REPO = "https://github.com/Sbusiso-Mdingi/mdingi-life";
export const MODEL_NAMES: Record<string, string> = { B0: "No improvement", LC: "Lee-Carter", CBD: "Cairns-Blake-Dowd", RH: "Renshaw-Haberman" };
export const WINDOW_START: Record<string, number> = { full: 1997, "post-peak": 2006 };
export const modelLabel = (k: string) => {
  const [name, ...rest] = k.split(" ");
  return `${MODEL_NAMES[name] ?? name}, ${rest.join(" ") === "full" ? "from 1997" : "from 2006"}`;
};

export const find = (prices: Price[], age: number, rate: number, adj: number) =>
  prices.find((p) => p.age === age && Math.abs(p.rate - rate) < 1e-9 && Math.abs(p.adj - adj) < 1e-9)!;
export const meanAbs = (v: number[]) => v.reduce((a, b) => a + Math.abs(b), 0) / v.length;
export const f2 = (v: number) => num(v, 2);
export const f1 = (v: number) => num(v, 1);

export function Metric({ value, label, sub, className, children }: { value: string; label: string; sub?: string; className?: string; children?: ReactNode }) {
  return (
    <div className="metric">
      <div className={`value ${className ?? ""}`}>{value}</div>
      <div className="label">{label}</div>
      {sub && <div className="sub">{sub}</div>}
      {children}
    </div>
  );
}

export function Icon({ pass }: { pass: boolean }) {
  return (
    <svg width="11" height="11" viewBox="0 0 12 12" aria-hidden="true">
      {pass ? (
        <path d="M2 6.5 4.8 9.2 10 3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      ) : (
        <path d="M3 3l6 6M9 3l-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      )}
    </svg>
  );
}

export function Verdict({ pass, who }: { pass: boolean; who?: string }) {
  return (
    <span className={`verdict ${pass ? "pass" : "fail"}`}>
      <Icon pass={pass} />
      {who ? `${who} ` : ""}
      {pass ? "Pass" : "Fail"}
    </span>
  );
}

export function LowerBound() {
  return (
    <div className="bound">
      <svg width="11" height="11" viewBox="0 0 12 12" aria-hidden="true">
        <path d="M6 1.5 11 10.5H1Z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M6 5v2.4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      Lower bound · P3 failed
    </div>
  );
}

export function Segmented<T extends string | number>({ options, value, onChange, label }: { options: { id: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={String(o.id)} aria-pressed={o.id === value} onClick={() => onChange(o.id)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Legend({ items }: { items: { label: string; color: string; kind?: "line" | "dash" | "band" | "dot" }[] }) {
  return (
    <div className="legend">
      {items.map((i) => (
        <span key={i.label}>
          <i className={`key ${i.kind && i.kind !== "line" ? i.kind : ""}`} style={i.kind === "dash" || i.kind === "dot" ? { color: i.color, borderColor: i.color } : { background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}

export function TableView({ children }: { children: ReactNode }) {
  return (
    <details className="table-view">
      <summary>Table view</summary>
      <div className="table-wrap">{children}</div>
    </details>
  );
}

export const KINDS: Kind[] = ["ilb", "fixed"];
export const KIND_LABEL: Record<Kind, string> = { ilb: "Inflation-linked", fixed: "Fixed-rate" };
export const CURVE_COLOR = { LI: "var(--s1)", NS: "var(--s2)", B0: "var(--s3)" } as const;
export const KEYS = ["5", "10", "20", "30"];
export const longDate = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("en-ZA", { day: "numeric", month: "long", year: "numeric" });
export const bp = (v: number) => `${num(v, 1)}bp`;
export const rm = (s: Record<string, Rmse | number>, k: string) => (s[k] as Rmse | undefined)?.rmse;
export const v2find = (v: V2, s: Sex, age: number, adj: number) => v[s].prices.find((p) => p.age === age && Math.abs(p.adj - adj) < 1e-9)!;
export const rand = (v: number) => `R${millions(v)}m`;
export const randBig = (v: number) => `R${millions(v, 0)}m`;
export const v3doc = (f: string) => `${REPO}/blob/main/research/${f}`;
