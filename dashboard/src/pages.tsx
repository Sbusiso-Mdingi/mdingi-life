import { useState, type ReactNode } from "react";
import type { Book, Pct, Research, Sex, V3 } from "./api";
import { BarChart, IntervalChart, YearChart, type BarGroup, type Interval } from "./charts";
import { BalanceSheet, Backtest, CurveBacktest, CurvePanel, CurvePrices, FanPanel, History, Interest, Matching, Sensitivity, Sources } from "./detail";
import { SEX_LABEL, num, pct, thousands } from "./format";
import { ADJS, AGES, COLOR, KEYS, Legend, REPO, SEXES, Segmented, TableView, Verdict, longDate, v2find } from "./ui";

export type Tab = "overview" | "quote" | "customers" | "investments" | "capital" | "future" | "built";
type Go = (t: Tab) => void;

const randFull = (v: number) => `R${thousands(v)}`;
const randM = (v: number, digits = 0) => `${v < 0 ? "−" : ""}R${(Math.abs(v) / 1e6).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}m`;
const randBn = (v: number) => `R${(v / 1e9).toFixed(1)}bn`;
const cents = (v: number) => `R${v.toFixed(2)}`;
const coverPct = (c: number) => `${Math.round(c * 100)}%`;
const PERSON: Record<Sex, string> = { Male: "Man", Female: "Woman" };
const doc = (f: string) => `${REPO}/blob/main/research/${f}`;
const MARGIN = 0.2; // the funeral pricing basis, research/book_v3.py

/** The caveat on every 95% range from the mortality forecast: the backtest found them too narrow. */
export function LowerBound() {
  return (
    <p className="note caveat">
      <strong>These ranges are too narrow.</strong> In the backtest, the forecast's 95% ranges caught fewer than 90% of the death rates that actually
      happened, so treat every range from it as a lower bound on the real uncertainty.
    </p>
  );
}

function Stat({ label, value, sub, good, children }: { label: string; value: string; sub?: ReactNode; good?: boolean; children?: ReactNode }) {
  return (
    <div className="card stat">
      <span className="label">{label}</span>
      <span className={`value${good ? " good" : ""}`}>{value}</span>
      {sub && <span className="sub">{sub}</span>}
      {children}
    </div>
  );
}

function Pill({ kind, children }: { kind: "good" | "bad" | "warn"; children: ReactNode }) {
  return (
    <span className={`pill ${kind}`}>
      <svg width="10" height="10" viewBox="0 0 12 12" aria-hidden="true">
        {kind === "good" ? (
          <path d="M2 6.5 4.8 9.2 10 3" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        ) : kind === "warn" ? (
          <path d="M6 2.5v4.5M6 9.5v.01" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
        ) : (
          <path d="M3 3l6 6M9 3l-6 6" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
        )}
      </svg>
      {children}
    </span>
  );
}

function PageHead({ kicker, title, children }: { kicker: string; title: string; children?: ReactNode }) {
  return (
    <header className="page-head">
      <p className="kicker">{kicker}</p>
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  );
}

type Bar = { key: string; name: string; note?: string; value: number; label: string; color: string };

/** Horizontal bars on one scale, with an optional reference marker (e.g. 100% cover). */
function HBars({ rows, max, marker, markerLabel }: { rows: Bar[]; max?: number; marker?: number; markerLabel?: string }) {
  const top = max ?? Math.max(...rows.map((r) => r.value), marker ?? 0);
  return (
    <div className="hbars" role="list">
      {rows.map((r) => (
        <div className="hbar" role="listitem" key={r.key} title={`${r.name}: ${r.label}`}>
          <div className="name">
            {r.name}
            {r.note && <small>{r.note}</small>}
          </div>
          <div className="track">
            <div className="fill" style={{ width: `${Math.max(0.6, (r.value / top) * 100)}%`, background: r.color }} />
            {marker != null && <div className="marker" style={{ left: `${(marker / top) * 100}%` }} aria-hidden="true" />}
          </div>
          <div className="val">{r.label}</div>
        </div>
      ))}
      {markerLabel && <p className="marker-label">{markerLabel}</p>}
    </div>
  );
}

const current = (v: V3) => v.key_rate ?? v.main;

// Overview ----------------------------------------------------------------------------------------------------------

/** The disclaimer, kept above the fold on the pages people land on. */
function Fiction() {
  return (
    <p className="fiction" role="note">
      <strong>Mdingi Life is fictional and sells nothing.</strong> I generated its customers with a seeded random draw; the death records, bond auctions and
      capital rules are real. Nothing here is a quote or actuarial advice.
    </p>
  );
}

/** The first starting capital at which 95% of futures stay covered every year, if any level reached it. */
/** Industry-typical starting capital, about 1.8 times the SCR: the upper reference point for the 95% crossing. */
const REFERENCE = 627e6;

/** The levels either side of 95%: the highest run below it, and R627m (or the first level above 95%, if R627m is not). */
export const crossing = (r: Research) => {
  const L = r.v4?.capital?.levels ?? [];
  const hi = L.find((x) => x.own_funds === REFERENCE && x.share_covered >= 0.95) ?? L.find((x) => x.share_covered >= 0.95);
  const lo = hi && [...L].reverse().find((x) => x.own_funds < hi.own_funds && x.share_covered < 0.95);
  return hi && lo ? { lo, hi } : null;
};

type Finding = { key: string; figure: string; pill?: ReactNode; text: ReactNode; tab?: Tab };

export function Overview({ r, go }: { r: Research; go: Go }) {
  const v = r.v3!;
  const b = v.book!;
  const now = current(v);
  const k = v.key_rate;
  const m = v.main;
  const v4 = r.v4;
  const pension = r.v2 ? v2find(r.v2, "Female", 65, 0.7)["inflation-linked LI"].median * 120_000 : null;
  const real = k ? Object.values(k.holdings.real).reduce((a, x) => a + x, 0) : m.matching.real.liability.value;
  const fixed = k ? Object.values(k.holdings.nominal).reduce((a, x) => a + x, 0) : m.matching.nominal.liability.value;
  const bonds = k ? Object.keys(k.holdings.real).length + Object.keys(k.holdings.nominal).length : 4;
  const minPremium = Math.min(...SEXES.flatMap((s) => b.premium_rates[s].map((p) => p.per_rand * b.sums[0] + p.fixed)));
  const own = [
    { key: "ilb", label: "Inflation-linked government bonds", value: real, color: "var(--s1)" },
    { key: "fixed", label: "Fixed-rate government bonds", value: fixed, color: "var(--s2)" },
    { key: "bill", label: "Treasury bill (cash)", value: m.assets.bill, color: "#8a968f" },
  ];
  const owe = [
    { key: "bel", label: "Owed to customers (best estimate)", value: now.bel.total, color: "var(--s3)" },
    { key: "rm", label: "Risk margin", value: now.risk_margin, color: "var(--gold)" },
    { key: "own", label: "Own capital", value: now.own_funds, color: "var(--primary-strong)" },
  ];
  const total = m.assets.total;
  const p3 = r.backtest.tests.P3;
  const longevity = v4?.stresses["S2 Longevity"];
  const cross = crossing(r);
  const levels = v4?.capital?.levels ?? [];
  const top = levels[levels.length - 1];
  const findings: Finding[] = [
    {
      key: "today",
      figure: coverPct(now.cover),
      pill: now.cover >= 1 ? <Pill kind="good">Above 100%</Pill> : <Pill kind="bad">Below 100%</Pill>,
      text: (
        <>
          Solvency cover today, on {randM(now.own_funds)} of capital. My first choice of bonds gave {coverPct(m.cover)}, short of the regulator's 100%;
          spreading the same money across {bonds} bonds of 5 to 30 years cut the interest-rate charge from {randM(m.market)} to {randM(now.market)}.
        </>
      ),
      tab: "capital",
    },
    ...(v4
      ? [
          {
            key: "five",
            figure: pct(v4.scenarios.A1.share_covered, 0),
            pill: v4.scenarios.A1.pass ? <Pill kind="good">Meets the 95% target</Pill> : <Pill kind="bad">Misses the 95% target</Pill>,
            text: (
              <>
                of 1,000 simulated five-year futures keep cover above 100% at every year-end. I set the target at 95% before running them. The bonds
                hedge what is owed to customers, not the regulator's add-ons, so a fall in rates still hurts.
              </>
            ),
            tab: "future" as Tab,
          },
          ...(longevity
            ? [
                {
                  key: "longevity",
                  figure: coverPct(Math.min(...longevity.cover)),
                  pill: <Pill kind="bad">Needs {randM(longevity.capital_to_restore)}</Pill>,
                  text: (
                    <>
                      is where cover falls if pensioners' death rates are 20% lower for good. Longevity is the company's biggest risk by far, and the one
                      disaster it cannot ride out without new capital.
                    </>
                  ),
                  tab: "future" as Tab,
                },
              ]
            : []),
          ...(levels.length > 1
            ? [
                {
                  key: "capital",
                  figure: cross ? `${randM(cross.lo.own_funds)} to ${randM(cross.hi.own_funds)}` : `> ${randM(top.own_funds)}`,
                  pill: <Pill kind="warn">Exploratory</Pill>,
                  text: cross ? (
                    <>
                      of starting capital, instead of {randM(levels[0].own_funds)}, is where the share of futures staying covered every year crosses 95%:{" "}
                      {pct(cross.lo.share_covered, 0)} at {randM(cross.lo.own_funds)}, {pct(cross.hi.share_covered, 0)} at {randM(cross.hi.own_funds)}. Even at{" "}
                      {randM(cross.hi.own_funds)}, longer-living pensioners take cover to {coverPct(cross.hi.stresses["S2 Longevity"])}. I added these runs
                      after seeing the first result. They use the v1 mortality model.
                    </>
                  ) : (
                    <>
                      of starting capital would be needed for 95% of futures to stay covered: at {randM(top.own_funds)}, {pct(top.share_covered, 0)} do. I
                      stopped the range there, as planned.
                    </>
                  ),
                  tab: "future" as Tab,
                },
              ]
            : []),
        ]
      : []),
    {
      key: "ranges",
      figure: "Ranges too narrow",
      pill: p3.Male && p3.Female ? <Pill kind="good">Backtest passed</Pill> : <Pill kind="bad">Backtest failed</Pill>,
      text: (
        <>
          The mortality forecast's 95% ranges caught fewer than 90% of the death rates that actually happened in the backtest
          {p3.Male !== p3.Female ? ` for ${p3.Male ? "women" : "men"}` : ", for men and women"}, so every pension range on this site is a lower bound on the real
          uncertainty.
        </>
      ),
      tab: "built",
    },
  ];
  return (
    <>
      <section className="hero">
        <p className="kicker">A portfolio project by Sbusiso Mdingi</p>
        <h1>I built a model South African life insurer to see whether it could keep its promises.</h1>
        <p>
          It pays pensions to {thousands(b.annuities.n)} retirees and covers {thousands(b.funeral.n)} families' funerals. I priced them on Stats SA death
          records, invested the money on National Treasury bond auctions, tested the capital against the Prudential Authority's rules, and projected it
          five years ahead.
        </p>
        <Fiction />
        <div className="actions">
          <button className="cta" onClick={() => go("quote")}>
            Try the pricing
          </button>
          <button className="cta ghost" onClick={() => go("built")}>
            Methods and limitations
          </button>
        </div>
      </section>

      <section className="section">
        <h2>What it shows</h2>
        <p className="sub">The main results on one screen. Each was measured against a pass mark I wrote down before running it, except the capital levels, which I added afterwards.</p>
        <div className="card">
          <ul className="findings">
            {findings.map((f) => (
              <li key={f.key}>
                <div className="figure">
                  {f.figure} {f.pill}
                </div>
                <p>
                  {f.text}{" "}
                  {f.tab && (
                    <button className="link" onClick={() => go(f.tab!)}>
                      Details →
                    </button>
                  )}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <div className="grid four kpis">
        <Stat label="Pensions paid each year" value={randM(b.annuities.income)} sub={`To ${thousands(b.annuities.n)} retirees, median age ${Math.round(b.annuities.median_age)}`} />
        <Stat label="Funeral cover in force" value={b.funeral.cover >= 1e9 ? randBn(b.funeral.cover) : randM(b.funeral.cover)} sub={`${thousands(b.funeral.n)} policies, from ${cents(minPremium)} a month`} />
        <Stat label="Total assets" value={randBn(total)} sub={`${randBn(now.bel.total)} of it is owed to customers; the rest backs the risk margin and own capital`} />
        <Stat label="Solvency cover" value={coverPct(now.cover)} good={now.cover >= 1} sub={`${randM(now.own_funds)} of capital against ${randM(now.scr)} required`} />
      </div>

      <section className="section">
        <h2>How I built it</h2>
        <div className="steps">
          <div className="card step">
            <span className="num-badge">1</span>
            <h3>Pricing the pensions</h3>
            <p>
              I forecast how long people live from 26 years of Stats SA death records, with ranges from simulated futures.
              {pension && " A woman of 65 who wants R10,000 a month for life, rising with inflation, would pay once:"}
            </p>
            {pension && <div className="figure">{randFull(Math.round(pension / 100) * 100)}</div>}
            <button className="link" onClick={() => go("quote")}>
              Price your own →
            </button>
          </div>
          <div className="card step">
            <span className="num-badge">2</span>
            <h3>Investing the money</h3>
            <p>
              Pensions are paid for decades, so the money sits in government bonds that pay back over the same years, priced on yield curves I fitted to the
              Treasury's auctions.
            </p>
            <div className="figure">{randBn(total)}</div>
            <button className="link" onClick={() => go("investments")}>
              See the holdings →
            </button>
          </div>
          <div className="card step">
            <span className="num-badge">3</span>
            <h3>Testing the capital</h3>
            <p>
              The regulator's standard formula asks whether the company could still pay everyone after a 1-in-200 year. With rebalanced bonds, cover is:
            </p>
            <div className="figure">{coverPct(now.cover)}</div>
            <button className="link" onClick={() => go("capital")}>
              What it holds capital against →
            </button>
          </div>
          {v4 && (
            <div className="card step">
              <span className="num-badge">4</span>
              <h3>Looking five years ahead</h3>
              <p>A thousand simulated paths for interest rates and inflation, and five named disasters. Futures that stay above 100% every year:</p>
              <div className="figure">{pct(v4.scenarios.A1.share_covered, 0)}</div>
              <button className="link" onClick={() => go("future")}>
                The five-year view →
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="section">
        <h2>The balance sheet in one picture</h2>
        <p className="sub">
          What the company owns, and who it is for, on {longDate(v.valuation_date)}. Both sides add up to {randBn(total)}.
        </p>
        <div className="card">
          {[
            { who: "What it owns", parts: own },
            { who: "Who it's for", parts: owe },
          ].map((row) => (
            <div className="stack-row" key={row.who}>
              <span className="who">{row.who}</span>
              <div className="stack" role="img" aria-label={`${row.who}: ${row.parts.map((p) => `${p.label} ${randM(p.value)}`).join(", ")}`}>
                {row.parts.map((p) => (
                  <div key={p.key} style={{ flex: p.value, background: p.color }} title={`${p.label}: ${randM(p.value)}`}>
                    {p.value / total > 0.12 ? randM(p.value) : ""}
                  </div>
                ))}
              </div>
            </div>
          ))}
          <div className="keylist">
            {[...own, ...owe].map((p) => (
              <span key={p.key}>
                <i style={{ background: p.color }} />
                {p.label} <b>{randM(p.value)}</b>
              </span>
            ))}
          </div>
          <div className="callout">
            <strong>Why the funeral business shows up as a plus</strong>
            Funeral customers are expected to pay {randM(m.bel_parts.premiums)} in future premiums, against {randM(m.bel_parts.claims)} of claims and{" "}
            {randM(m.bel_parts.fun_expenses)} of running costs. The {randM(-m.bel.funeral)} difference is netted off what the pensions are owed. The risk margin
            is what another insurer would charge to take the book over; own capital is the cushion above that.
          </div>
        </div>
      </section>
    </>
  );
}

// Get a quote -------------------------------------------------------------------------------------------------------

export function Quote({ r }: { r: Research }) {
  const v2 = r.v2!;
  const book = r.v3!.book!;
  const [sex, setSex] = useState<Sex>("Female");
  const [age, setAge] = useState(65);
  const [kind, setKind] = useState<"inflation-linked" | "level">("inflation-linked");
  const [monthly, setMonthly] = useState(10_000);
  const p = v2find(v2, sex, age, 0.7)[`${kind} LI`];
  const yearly = monthly * 12;

  const [fsex, setFsex] = useState<Sex>("Female");
  const [fage, setFage] = useState(35);
  const [sum, setSum] = useState(book.sums[1] ?? book.sums[0]);
  const rate = book.premium_rates[fsex].find((x) => x.age === fage)!;
  const premium = rate.per_rand * sum + rate.fixed;
  const ages = book.premium_rates[fsex].map((x) => x.age);

  const rows: Interval[] = SEXES.flatMap((s) =>
    AGES.map((a) => {
      const q = v2find(v2, s, a, 0.7)[`${kind} LI`];
      return { key: `${s}${a}`, label: `${PERSON[s]}, ${a}`, color: COLOR[s], lo: (q.lo * yearly) / 1e6, median: (q.median * yearly) / 1e6, hi: (q.hi * yearly) / 1e6, active: s === sex && a === age };
    }),
  );

  return (
    <>
      <PageHead kicker="Pricing" title="What would cover cost?">
        Prices from my models, built on Stats SA death records and on the government bond market of {longDate(v2.curves.ilb.date)}.
      </PageHead>
      <Fiction />
      <div className="grid two">
        <section className="card" aria-label="Retirement income quote">
          <h3>A pension for life</h3>
          <p>Pay once when you retire, and receive an income every month for as long as you live.</p>
          <div className="quote" style={{ marginTop: 20 }}>
            <div>
              <div className="field">
                <span className="label">I am a</span>
                <Segmented label="Sex" value={sex} onChange={setSex} options={SEXES.map((s) => ({ id: s, label: PERSON[s].toLowerCase() }))} />
              </div>
              <div className="field">
                <span className="label">Retiring at</span>
                <Segmented label="Age" value={age} onChange={setAge} options={AGES.map((a) => ({ id: a, label: String(a) }))} />
              </div>
              <div className="field">
                <span className="label">My income</span>
                <Segmented
                  label="Income type"
                  value={kind}
                  onChange={setKind}
                  options={[
                    { id: "inflation-linked", label: "Rises with inflation" },
                    { id: "level", label: "Stays the same" },
                  ]}
                />
              </div>
              <label className="field">
                <span className="label">
                  Each month: <output>{randFull(monthly)}</output>
                </span>
                <input type="range" min={2000} max={50000} step={500} value={monthly} onChange={(e) => setMonthly(Number(e.target.value))} />
              </label>
            </div>
            <div className="quote-result" aria-live="polite">
              <span className="line">You pay once</span>
              <span className="big">{randFull(Math.round((p.median * yearly) / 100) * 100)}</span>
              <span className="line">
                95% range <b>{randFull(Math.round((p.lo * yearly) / 100) * 100)}</b> to <b>{randFull(Math.round((p.hi * yearly) / 100) * 100)}</b>, a lower
                bound on the real uncertainty
              </span>
              <span className="line" style={{ marginTop: 8 }}>
                That is <b>{num(p.median, 1)} years</b> of income up front.{" "}
                {kind === "level" ? "Your income stays fixed, so inflation slowly eats it." : "Your income keeps its buying power."}
              </span>
            </div>
          </div>
        </section>

        <section className="card" aria-label="Funeral cover quote">
          <h3>Funeral cover</h3>
          <p>A fixed monthly premium, and a lump sum to your family when you die.</p>
          <div className="quote" style={{ marginTop: 20 }}>
            <div>
              <div className="field">
                <span className="label">I am a</span>
                <Segmented label="Sex" value={fsex} onChange={setFsex} options={SEXES.map((s) => ({ id: s, label: PERSON[s].toLowerCase() }))} />
              </div>
              <label className="field">
                <span className="label">
                  My age: <output>{fage}</output>
                </span>
                <input type="range" min={ages[0]} max={ages[ages.length - 1]} value={fage} onChange={(e) => setFage(Number(e.target.value))} />
              </label>
              <div className="field">
                <span className="label">Cover</span>
                <Segmented label="Cover" value={sum} onChange={setSum} options={book.sums.map((x) => ({ id: x, label: `R${x / 1000}k` }))} />
              </div>
            </div>
            <div className="quote-result" aria-live="polite">
              <span className="line">You pay each month</span>
              <span className="big">{cents(premium)}</span>
              <span className="line">
                Your family receives <b>{randFull(sum)}</b>
              </span>
              <span className="line" style={{ marginTop: 8 }}>
                <b>{cents((1 - MARGIN) * rate.per_rand * sum)}</b> pays for the cover, <b>{cents((1 - MARGIN) * rate.fixed)}</b> for running the policy, and{" "}
                <b>{cents(MARGIN * premium)}</b> is the {pct(MARGIN, 0)} margin.
              </span>
            </div>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">Why a pension quote is a range</h2>
            <p className="eyebrow">
              {kind === "inflation-linked" ? "Rising" : "Level"} pension of {randFull(monthly)} a month: what it costs, in R million, with the forecast's 95% range
            </p>
          </div>
        </div>
        <IntervalChart label={`Price of a pension of ${randFull(monthly)} a month by sex and age at retirement, R million`} rows={rows} fmt={(x) => `R${x.toFixed(2)}m`} groups={2} />
        <p className="note">
          The price depends on how long you will live, and nobody knows that for sure. I forecast it from Stats SA death records and simulate thousands of
          possible futures; the bar is the middle 95% of them. Women live longer, so their pensions cost more.
        </p>
        <LowerBound />
        <div className="callout">
          <strong>What a real quote would add</strong>
          These pension prices cover the income alone, with no loading for costs, commission or profit, and no health check. That is also why the
          company's profit from insurance is small: almost all of it comes from investment return. The funeral premiums do include running costs (R15 a
          month) and a {pct(MARGIN, 0)} margin.
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">The assumption that moves the price most</h2>
            <p className="eyebrow">
              {PERSON[sex]} retiring at {age}, {kind === "inflation-linked" ? "rising" : "level"} pension of {randFull(monthly)} a month, by how much longer
              pension buyers live than South Africans on average
            </p>
          </div>
        </div>
        <p>
          People who buy pensions tend to be wealthier and live longer than the population the death records cover. I assume their death rates are 30%
          lower. No public South African data on pensioners' deaths was available to estimate it, so this is a judgement, and it moves the price more
          than the forecast's own range does.
        </p>
        <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Pension buyers' death rates</th>
              <th className="num">You pay once</th>
              <th className="num">95% range</th>
              <th className="num">Change</th>
            </tr>
          </thead>
          <tbody>
            {ADJS.map((adj) => {
              const q = v2find(v2, sex, age, adj)[`${kind} LI`];
              const base = p.median;
              return (
                <tr key={adj} className={Math.abs(adj - 0.7) < 1e-9 ? "total" : undefined}>
                  <td>
                    {pct(1 - adj, 0)} below average{Math.abs(adj - 0.7) < 1e-9 ? " (used everywhere)" : ""}
                  </td>
                  <td className="num">{randFull(Math.round((q.median * yearly) / 100) * 100)}</td>
                  <td className="num">
                    {randFull(Math.round((q.lo * yearly) / 1000) * 1000)} to {randFull(Math.round((q.hi * yearly) / 1000) * 1000)}
                  </td>
                  <td className="num">{Math.abs(adj - 0.7) < 1e-9 ? "" : `${q.median > base ? "+" : "−"}${pct(Math.abs(q.median / base - 1), 0)}`}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </section>
    </>
  );
}

// Customers ---------------------------------------------------------------------------------------------------------

function AgeChart({ label, ages, color, first }: { label: string; ages: Book["annuities"]["ages"]; color: string; first?: number }) {
  const groups: BarGroup[] = ages.from.map((f, i) => ({
    key: String(f),
    label: `${i === 0 && first ? first : f}–${f + 4}`,
    values: [{ key: "n", label: "Customers", color, value: ages.n[i] }],
  }));
  return <BarChart label={label} groups={groups} fmt={(x) => thousands(x)} height={220} />;
}

export function Customers({ r }: { r: Research }) {
  const b = r.v3!.book!;
  const a = b.annuities, f = b.funeral;
  const rising = (a.types["inflation-linked"] ?? 0) / a.n;
  const women = (f.sexes.Female ?? 0) / f.n;
  const ago = (n: number) => (n === 0 ? "this year" : n === 1 ? "a year ago" : `${n} years ago`);
  return (
    <>
      <PageHead kicker="The customers" title="Who the company covers">
        {thousands(a.n)} pensioners and {thousands(f.n)} funeral policyholders, all invented. I drew them at random, from a fixed seed in{" "}
        <a href={`${REPO}/blob/main/research/book_v3.py`} target="_blank" rel="noreferrer">
          book_v3.py
        </a>
        : pensions bought at 55 to 75 with incomes spread around R60,000 a year, and funeral policies taken out at around 38 for R10,000 to R30,000 of cover.
        The shapes are my choices, not taken from any insurer's data.
      </PageHead>

      <div className="grid two">
        <section className="card">
          <h3>Pensioners</h3>
          <div className="grid three" style={{ marginTop: 14, gap: 10 }}>
            <div className="metric">
              <div className="value">{Math.round(a.median_age)}</div>
              <div className="sub">median age</div>
            </div>
            <div className="metric">
              <div className="value">{randFull(Math.round(a.median_income / 12 / 10) * 10)}</div>
              <div className="sub">median monthly pension; the average is {randFull(Math.round(a.income / a.n / 12 / 10) * 10)}, pulled up by a few large ones</div>
            </div>
            <div className="metric">
              <div className="value">{pct(rising, 0)}</div>
              <div className="sub">have income that rises with inflation</div>
            </div>
          </div>
          <p className="eyebrow" style={{ marginTop: 18 }}>
            Pensioners by age
          </p>
          <AgeChart label="Number of pensioners by age band" ages={a.ages} color="var(--s1)" />
        </section>
        <section className="card">
          <h3>Funeral policyholders</h3>
          <div className="grid three" style={{ marginTop: 14, gap: 10 }}>
            <div className="metric">
              <div className="value">{Math.round(f.median_age)}</div>
              <div className="sub">median age</div>
            </div>
            <div className="metric">
              <div className="value">{cents(f.median_premium)}</div>
              <div className="sub">median monthly premium</div>
            </div>
            <div className="metric">
              <div className="value">{pct(women, 0)}</div>
              <div className="sub">are women</div>
            </div>
          </div>
          <p className="eyebrow" style={{ marginTop: 18 }}>
            Policyholders by age
          </p>
          <AgeChart label="Number of funeral policyholders by age band" ages={f.ages} color="var(--s2)" first={18} />
        </section>
      </div>

      <section className="section">
        <h2>A few of them</h2>
        <p className="sub">The first policies in the book.</p>
        <div className="grid four">
          {a.sample.map((p) => (
            <div className="card person" key={`a${p.id}`}>
              <span className="avatar" style={{ background: COLOR[p.sex] }} aria-hidden="true">
                {p.age}
              </span>
              <div>
                <h3>Pensioner #{String(p.id).padStart(5, "0")}</h3>
                <p className="meta">
                  {PERSON[p.sex]}, {p.age}. Retired at {p.age_at_purchase}, {ago(p.years_since_purchase)}.
                </p>
                <div className="money">
                  {randFull(Math.round(p.income / 12))} <small>a month, {p.type === "level" ? "level" : "rising with inflation"}</small>
                </div>
              </div>
            </div>
          ))}
          {f.sample.map((p) => (
            <div className="card person" key={`f${p.id}`}>
              <span className="avatar" style={{ background: COLOR[p.sex] }} aria-hidden="true">
                {p.age}
              </span>
              <div>
                <h3>Funeral #{String(p.id).padStart(5, "0")}</h3>
                <p className="meta">
                  {PERSON[p.sex]}, {p.age}. Joined at {p.entry_age}, {ago(p.years_in_force)}.
                </p>
                <div className="money">
                  {randFull(p.sum_assured)} <small>cover for {cents(p.premium)} a month</small>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <h2>How long pensioners might live</h2>
        <p className="sub">
          Every pension depends on this. South African life expectancy fell sharply with HIV and recovered with treatment, so the past is a poor
          straight-line guide to the future.
        </p>
        {r.history && <History r={r} />}
        <FanPanel r={r} />
        <LowerBound />
      </section>
    </>
  );
}

// Investments -------------------------------------------------------------------------------------------------------

export function Investments({ r }: { r: Research }) {
  const v = r.v3!;
  const k = v.key_rate;
  const m = v.main;
  const [curve, setCurve] = useState<"real" | "nominal">("real");
  const holdings: Bar[] = k
    ? [
        ...Object.entries(k.holdings.real).map(([bond, x]) => ({ key: bond, name: bond, note: "Inflation-linked", value: x, label: randM(x), color: "var(--s1)" })),
        ...Object.entries(k.holdings.nominal).map(([bond, x]) => ({ key: bond, name: bond, note: "Fixed-rate", value: x, label: randM(x), color: "var(--s2)" })),
        { key: "bill", name: "Treasury bill", note: "182 days, cash", value: m.assets.bill, label: randM(m.assets.bill), color: "#8a968f" },
      ].sort((a, b) => b.value - a.value)
    : [];
  const groups: BarGroup[] = KEYS.map((t) => ({
    key: t,
    label: `${t} years`,
    values: [
      { key: "l", label: "The pensions", color: "var(--s1)", value: m.dv01[curve].liability[t] / 1e3 },
      { key: "d", label: "First portfolio (two bonds)", color: "var(--s2)", value: m.dv01[curve].portfolio[t] / 1e3 },
      ...(k ? [{ key: "k", label: "Rebalanced portfolio", color: "var(--s3)", value: k.dv01[curve].portfolio[t] / 1e3 }] : []),
    ],
  }));
  const d = m.dv01.real;
  return (
    <>
      <PageHead kicker="Investments" title="Where the money is">
        The money behind the pensions is in South African government bonds and a Treasury bill, chosen so their value moves in step with what is owed.
      </PageHead>

      {k && (
        <section className="card">
          <h3>What the company holds today</h3>
          <p>
            {randM(m.assets.total)} across {holdings.length - 1} government bonds and a Treasury bill. Inflation-linked bonds pay the pensions that rise with
            inflation; fixed-rate bonds pay the level ones.
          </p>
          <HBars rows={holdings} />
          <p className="note caveat">
            All of it is lent to one borrower, the South African government. The regulator's formula charges nothing for that, so neither does this model, but a
            sovereign downgrade or default would hit every asset at once.
          </p>
        </section>
      )}

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">Matching the pensions, point by point on the curve</h2>
            <p className="eyebrow">
              Value lost if {curve === "real" ? "inflation-linked" : "fixed-rate"} yields rise by 0.01% at one point on the curve, R thousand
            </p>
          </div>
          <Segmented
            label="Curve"
            value={curve}
            onChange={setCurve}
            options={[
              { id: "real", label: "Rising pensions" },
              { id: "nominal", label: "Level pensions" },
            ]}
          />
        </div>
        <div className="legend">
          {groups[0].values.map((x) => (
            <span key={x.key}>
              <i className="key" style={{ background: x.color, height: 10, width: 10 }} />
              {x.label}
            </span>
          ))}
        </div>
        <BarChart label="Sensitivity of the pensions and of each bond portfolio to a 0.01% rise in yields at 5, 10, 20 and 30 years, R thousand" groups={groups} fmt={(x) => `R${num(x, 0)}k`} height={260} />
        <p className="note">
          When interest rates move, the value of the pensions moves, and so must the bonds behind them. My first portfolio held two bonds of each kind that matched the
          pensions on average, but bunched all the risk around 10 years: R{num(d.portfolio["10"] / 1e3, 0)}k against the pensions' R{num(d.liability["10"] / 1e3, 0)}k,
          and nothing at 30 years against R{num(d.liability["30"] / 1e3, 0)}k. {k ? "The rebalanced portfolio matches the pensions at all four points, so a change in the shape of the curve no longer hits only one side." : ""}
        </p>
        <TableView>
          <table>
            <thead>
              <tr>
                <th>Point on the curve</th>
                {groups[0].values.map((x) => (
                  <th key={x.key} className="num">
                    {x.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <tr key={g.key}>
                  <td>{g.label}</td>
                  {g.values.map((x) => (
                    <td key={x.key} className="num">
                      {num(x.value, 1)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </TableView>
      </section>

      {r.v2 && <CurvePanel v={r.v2} />}
    </>
  );
}

// Capital -----------------------------------------------------------------------------------------------------------

export function Capital({ r }: { r: Research }) {
  const v = r.v3!;
  const m = v.main, u = v.unmatched, k = v.key_rate;
  const now = current(v);
  const median = v.checks.K5.industry_median;
  const strategies: Bar[] = [
    { key: "u", name: "Everything in cash", note: "No bonds", value: u.cover, label: coverPct(u.cover), color: "var(--s2)" },
    { key: "m", name: "First portfolio", note: "Two bonds of each kind, near 10 years", value: m.cover, label: coverPct(m.cover), color: "var(--s3)" },
    ...(k ? [{ key: "k", name: "Rebalanced", note: `${Object.keys(k.holdings.real).length + Object.keys(k.holdings.nominal).length} bonds, 5 to 30 years`, value: k.cover, label: coverPct(k.cover), color: "var(--s1)" }] : []),
  ];
  const loss = (a: string, b: string) => Math.max(now.rate_losses?.[a] ?? 0, now.rate_losses?.[b] ?? 0);
  const realWorst = (now.rate_losses?.["real down"] ?? 0) >= (now.rate_losses?.["real up"] ?? 0) ? "fall" : "rise";
  const nomWorst = (now.rate_losses?.["nominal up"] ?? 0) >= (now.rate_losses?.["nominal down"] ?? 0) ? "rise" : "fall";
  const stress: Bar[] = [
    { key: "lon", name: "People live longer", note: "The regulator's test: pensioners' death rates 10% lower, and improving 1 point a year faster", value: now.life.longevity, label: randM(now.life.longevity, 1), color: "var(--s1)" },
    { key: "real", name: `Inflation-linked yields ${realWorst}`, note: "By about half to three quarters", value: loss("real down", "real up"), label: randM(loss("real down", "real up"), 1), color: "var(--s1)" },
    { key: "nom", name: `Fixed-rate yields ${nomWorst}`, note: "By 30% to 50% at most terms", value: loss("nominal up", "nominal down"), label: randM(loss("nominal up", "nominal down"), 1), color: "var(--s1)" },
    { key: "exp", name: "Costs rise", note: "Running costs 10% up, inflation 2 points up", value: now.life.expense, label: randM(now.life.expense, 1), color: "var(--s1)" },
    { key: "lapse", name: "Customers leave", note: "40% of funeral policies cancelled at once", value: now.life.lapse, label: randM(now.life.lapse, 1), color: "var(--s1)" },
    { key: "op", name: "Something breaks", note: "Systems, people or fraud", value: now.op, label: randM(now.op, 1), color: "var(--s1)" },
    { key: "mort", name: "More funeral claims", note: "Death rates 15% higher", value: now.life.mortality, label: randM(now.life.mortality, 1), color: "var(--s1)" },
    { key: "cat", name: "A pandemic", note: "A spike in deaths over three months", value: now.life.catastrophe, label: randM(now.life.catastrophe, 1), color: "var(--s1)" },
  ].sort((a, b) => b.value - a.value);
  const sum = stress.reduce((a, x) => a + x.value, 0);
  return (
    <>
      <PageHead kicker="Capital" title="Is there enough capital?">
        The Prudential Authority asks every insurer to hold enough capital to survive a 1-in-200 year: the solvency capital requirement. Solvency cover is the
        capital held divided by that requirement, and it has to be at least 100%.
      </PageHead>

      <div className="grid three">
        <Stat label="Solvency cover today" value={coverPct(now.cover)} good={now.cover >= 1}>
          {now.cover >= 1 ? <Pill kind="good">Meets the requirement</Pill> : <Pill kind="bad">Below the requirement</Pill>}
        </Stat>
        <Stat label="Capital required" value={randM(now.scr)} sub="To survive a 1-in-200 year" />
        <Stat label="Capital held" value={randM(now.own_funds)} sub={`${coverPct(median)} cover, the life industry's typical level, would need ${randM(now.scr * median)}`} />
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">How the money is invested decides whether it passes</h2>
            <p className="eyebrow">Solvency cover on the same {randM(m.own_funds)} of capital, by how the money is invested</p>
          </div>
        </div>
        <HBars rows={strategies} max={Math.max(1.3, ...strategies.map((s) => s.value))} marker={1} markerLabel="The line marks 100%, the regulator's minimum." />
        <p className="note">
          With everything in cash, a fall in interest rates would raise the value of the pensions with nothing to offset it: the interest-rate charge is{" "}
          {randM(u.market)} and the requirement {randM(u.scr)}, almost three times the capital. The first portfolio cut that charge to {randM(m.market)}, but
          left the far end of the curve open.{" "}
          {k ? `Spreading the bonds across 5 to 30 years cut it to ${randM(k.market)}, and took the same capital over the line.` : ""}
        </p>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">What the capital is held against</h2>
            <p className="eyebrow">Loss in each of the regulator's stress tests, R million</p>
          </div>
        </div>
        <HBars rows={stress} />
        <p className="note">
          Taken one at a time these losses add up to {randM(sum)}. They would not all happen in the same year, so the regulator's formula combines them into a
          requirement of {randM(now.scr)}. People living longer is by far the biggest risk, {randM(now.life.longevity)} on its own, because the pensions are
          paid for as long as people live. The funeral business barely registers. It is profitable, so its main risk is customers leaving.
        </p>
        <TableView>
          <table>
            <thead>
              <tr>
                <th>Stress test</th>
                <th className="num">Loss, R million</th>
              </tr>
            </thead>
            <tbody>
              {stress.map((x) => (
                <tr key={x.key}>
                  <td>
                    {x.name}
                    <div className="plain">{x.note}</div>
                  </td>
                  <td className="num">{(x.value / 1e6).toFixed(1)}</td>
                </tr>
              ))}
              <tr className="total">
                <td>Requirement after combining (including operational)</td>
                <td className="num">{(now.scr / 1e6).toFixed(1)}</td>
              </tr>
            </tbody>
          </table>
        </TableView>
      </section>

      <AnnuitantSensitivity v={v} />
    </>
  );
}

/** v3's annuitant mortality sensitivity, on the first portfolio, where it was run. */
function AnnuitantSensitivity({ v }: { v: NonNullable<Research["v3"]> }) {
  const rows = [
    { adj: 0.6, s: v.sensitivities["annuitant 0.6"] },
    { adj: 0.7, s: v.main },
    { adj: 0.8, s: v.sensitivities["annuitant 0.8"] },
  ].filter((x) => x.s);
  return (
    <section className="panel">
      <h2 className="serif">The assumption behind it all</h2>
      <p className="note">
        People who buy pensions live longer than the population. I assumed their death rates are 70% of everyone's. It is a round number I chose, not one fitted
        to South African pensioners, since no such data is public. Ten points either way moves what is owed by about R200m and cover by about 5 points. These
        rows are on the first portfolio, where the sensitivity was run, so cover is lower than today's.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Pensioners' death rates, share of everyone's</th>
              <th className="num">Owed to customers</th>
              <th className="num">Capital required</th>
              <th className="num">Solvency cover</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ adj, s }) => (
              <tr key={adj}>
                <td>
                  {pct(adj, 0)}
                  {adj === 0.7 ? " (used everywhere)" : ""}
                </td>
                <td className="num">{randM(s.bel.total)}</td>
                <td className="num">{randM(s.scr)}</td>
                <td className="num">{coverPct(s.cover)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// How it's built ----------------------------------------------------------------------------------------------------

function Disclose({ title, sub, children }: { title: string; sub: string; children: ReactNode }) {
  return (
    <details className="disclose">
      <summary>
        <span>
          {title}
          <br />
          <small>{sub}</small>
        </span>
      </summary>
      <div className="body">{children}</div>
    </details>
  );
}

const Commit = ({ hash, when }: { hash: string; when: string }) => (
  <a href={`${REPO}/commit/${hash}`} target="_blank" rel="noreferrer">
    <code>{hash.slice(0, 7)}</code>, {when}
  </a>
);

const Frozen = ({ hash, when }: { hash: string; when: string }) => (
  <a href={`${REPO}/commit/${hash}`} target="_blank" rel="noreferrer">
    Frozen {when} (<code>{hash.slice(0, 7)}</code>)
  </a>
);

export function Built({ r }: { r: Research }) {
  const t = r.backtest.tests;
  const v2 = r.v2, v3 = r.v3;
  const both = (x: Record<Sex, boolean>) => SEXES.map((s) => <Verdict key={s} pass={x[s]} who={SEX_LABEL[s]} />);
  const checks: { claim: string; plain: string; verdicts: ReactNode; code?: boolean }[] = [
    { claim: "Death rates keep improving", plain: "The forecast beat a no-improvement baseline on 2017 to 2019.", verdicts: both(t.P1) },
    { claim: "The HIV years are handled", plain: "Fitting from 2006, after HIV deaths peaked, beat fitting from 1997.", verdicts: both(t.P2) },
    {
      claim: "The forecast ranges are wide enough",
      plain: "The 95% ranges were meant to catch at least 90% of what actually happened. They caught fewer, so every pension range here is a lower bound: the true uncertainty is wider.",
      verdicts: both(t.P3),
    },
    { claim: "Pension prices are accurate", plain: "Prices at 65 from the forecast missed the actual ones by under 2%.", verdicts: both(t.P4) },
  ];
  if (v2) {
    const c = v2.validation.tests;
    checks.push(
      {
        claim: "The bond curve beats each bond's last yield",
        plain: "Predicting each Treasury auction from the curve beat using the bond's own last price, but only just.",
        verdicts: (["ilb", "fixed"] as const).map((k) => <Verdict key={k} pass={c[k].C1} who={k === "ilb" ? "Inflation-linked" : "Fixed-rate"} />),
      },
      {
        claim: "The bond curve is within 0.25% of auction yields",
        plain: "Inflation-linked bonds pass. Fixed-rate yields are harder to predict, mostly because the market moves between auctions.",
        verdicts: (["ilb", "fixed"] as const).map((k) => <Verdict key={k} pass={c[k].C3} who={k === "ilb" ? "Inflation-linked" : "Fixed-rate"} />),
      },
    );
  }
  if (v3) {
    checks.push(
      { claim: "The valuation engine is right", plain: "A simple month-by-month calculation agrees with the engine to better than one part in a trillion, under every stress.", verdicts: <Verdict pass={v3.checks.K1.pass} />, code: true },
      {
        claim: "Matching cuts the interest-rate charge below a quarter",
        plain: `The first portfolio cut it from ${randM(v3.unmatched.market)} with everything in cash to ${randM(v3.main.market)}.`,
        verdicts: <Verdict pass={v3.checks.K3.pass} />,
      },
      { claim: "Longevity is the largest risk", plain: "A sense check: for a pension book it could hardly come out otherwise.", verdicts: <Verdict pass={v3.checks.K4.pass} />, code: true },
    );
    if (v3.key_rate)
      checks.push({
        claim: "Rebalancing beats the first portfolio",
        plain: "Added after the first result was seen, and written down before it was run.",
        verdicts: <Verdict pass={v3.key_rate.checks.K6.pass} />,
      });
  }
  const v4 = r.v4;
  if (v4) {
    const a2 = Object.values(v4.checks.A2);
    checks.push(
      {
        claim: "The projection adds up",
        plain: "Each year's cash flows and the roll-forward of the accounts reconcile with the valuations at either end, to rounding.",
        verdicts: <Verdict pass={v4.checks.R1.pass && v4.checks.R2.pass} />,
        code: true,
      },
      {
        claim: "Simulated rates move like real ones",
        plain: `A year's change in the 10-year yield across the futures is within a third of its spread since 2011. Fixed-rate passes at ${num(v4.checks.E1.nominal.ratio, 2)} against a limit of 1.33, only just. The model as first written failed this for inflation-linked bonds; the change was committed before anything was projected.`,
        verdicts: (["real", "nominal"] as const).map((k) => <Verdict key={k} pass={v4.checks.E1[k].pass} who={k === "real" ? "Inflation-linked" : "Fixed-rate"} />),
      },
      {
        claim: "Cover stays above 100% in 95% of futures",
        plain: `It does in ${pct(v4.checks.A1.share_covered, 0)}. The bonds match the pensions, not the risk margin or the capital requirement.`,
        verdicts: <Verdict pass={v4.checks.A1.pass} />,
      },
      {
        claim: "Cover stays above 100% under each disaster",
        plain: `${a2.filter(Boolean).length} of ${a2.length} pass. See the next five years.`,
        verdicts: <Verdict pass={a2.every(Boolean)} />,
      },
    );
  }
  return (
    <>
      <PageHead kicker="Methods" title="Methods and limitations">
        I built this in four parts. For each, I wrote down the method, the tests and the pass marks, and committed them before running anything. Later changes
        are dated and committed before the run they affect. Each card links the commit it was frozen at.
      </PageHead>

      <div className="grid two">
        <div className="card">
          <div className="icon-badge" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 17l5-5 4 4 8-8" />
              <path d="M14 8h6v6" />
            </svg>
          </div>
          <h3>Forecasting how long people live</h3>
          <p>Four mortality models backtested on Stats SA registered deaths, 1997 to 2022. The winner prices the pensions, with ranges from 5,000 simulated futures.</p>
          <p>
            <a href={doc("PROTOCOL.md")} target="_blank" rel="noreferrer">
              Plan
            </a>{" "}
            ·{" "}
            <a href={doc("RESULTS.md")} target="_blank" rel="noreferrer">
              Results
            </a>{" "}
            · <Frozen hash="6335c9c5c418" when="25 Oct 2026, 22:02" />
          </p>
        </div>
        <div className="card">
          <div className="icon-badge" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 21h18M5 21V10M10 21V10M14 21V10M19 21V10M2 10l10-6 10 6" />
            </svg>
          </div>
          <h3>Reading the bond market</h3>
          <p>Yield curves fitted to National Treasury auction results since 2010 and tested on every auction from 2018. The pensions are priced and matched on them.</p>
          <p>
            <a href={doc("PROTOCOL_v2.md")} target="_blank" rel="noreferrer">
              Plan
            </a>{" "}
            ·{" "}
            <a href={doc("RESULTS_v2.md")} target="_blank" rel="noreferrer">
              Results
            </a>{" "}
            · <Frozen hash="cc4c12514ee1" when="26 Oct 2026, 06:22" />
          </p>
        </div>
        <div className="card">
          <div className="icon-badge" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          </div>
          <h3>Testing the capital</h3>
          <p>The Prudential Authority's standard formula for solvency (SAM), applied to an invented book of pensions and funeral policies.</p>
          <p>
            <a href={doc("PROTOCOL_v3.md")} target="_blank" rel="noreferrer">
              Plan
            </a>{" "}
            ·{" "}
            <a href={doc("RESULTS_v3.md")} target="_blank" rel="noreferrer">
              Results
            </a>{" "}
            · <Frozen hash="545ba7193b24" when="26 Oct 2026, 10:21" />
          </p>
        </div>
        <div className="card">
          <div className="icon-badge" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 12h4l3-8 4 16 3-8h4" />
            </svg>
          </div>
          <h3>Looking five years ahead</h3>
          <p>A thousand simulated paths for interest rates and inflation, five named disasters, and the accounts under IFRS 17, year by year.</p>
          <p>
            <a href={doc("PROTOCOL_v4.md")} target="_blank" rel="noreferrer">
              Plan
            </a>{" "}
            ·{" "}
            <a href={doc("RESULTS_v4.md")} target="_blank" rel="noreferrer">
              Results
            </a>{" "}
            · <Frozen hash="fedf29aeeebc" when="26 Oct 2026, 11:49" />
          </p>
        </div>
      </div>

      <section className="section">
        <h2>The tests, and how they came out</h2>
        <p className="sub">Each was set before the result it checks. These could have gone either way.</p>
        <div className="card">
          <ul className="checks">
            {checks.filter((c) => !c.code).map((c) => (
              <li key={c.claim}>
                <strong>{c.claim}</strong>
                <span className="verdicts">{c.verdicts}</span>
                <p>{c.plain}</p>
              </li>
            ))}
          </ul>
        </div>
        <h3 className="subhead">Checks on the code, not the model</h3>
        <p className="sub">These confirm the arithmetic or a result that was all but certain. They are not evidence the model is right.</p>
        <div className="card">
          <ul className="checks">
            {checks.filter((c) => c.code).map((c) => (
              <li key={c.claim}>
                <strong>{c.claim}</strong>
                <span className="verdicts">{c.verdicts}</span>
                <p>{c.plain}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="section">
        <h2>Changes after freezing</h2>
        <div className="card">
          <ul className="method">
            <li>
              <strong>Key-rate matching (v3)</strong>
              The first portfolio left cover below 100%. I wrote the rebalancing up at{" "}
              <Commit hash="7017b9f" when="10:58" /> and ran it at <Commit hash="202232b" when="11:09" />.
            </li>
            <li>
              <strong>Two factors a curve (v4)</strong>
              The frozen three-factor rate model failed its own check. The two-factor version was committed at <Commit hash="ce1ad56" when="12:08" />, and the
              projection results at <Commit hash="d50d59b" when="13:55" />. Its fixed-rate check, 1.32 against 1.33, was first seen in that run. The frozen model's
              results are reported too.
            </li>
            <li>
              <strong>Starting capital (v4), exploratory</strong>
              Added after seeing the first result. The levels and the rule for investing the extra were written at <Commit hash="28e4b67" when="14:51" />,
              before any level was run. After R600m to R1,000m had run, I stopped at R500m rather than narrowing to the nearest R25m, and report the crossing
              as an interval (<Commit hash="55fbcb9" when="16:15" />, before the R500m result). Every level used the same 1,000 futures, regenerated from
              the same seed on the same calibration, and the same five disasters. Like every capital result on this site, it uses the v1 mortality model.
            </li>
          </ul>
        </div>
      </section>

      <section className="section">
        <h2>Limitations</h2>
        <div className="card">
          <ul className="method">
            <li>
              <strong>The customers are invented</strong>
              Seeded random draws, in shapes I chose. A real book would differ in ages, sizes and mix.
            </li>
            <li>
              <strong>The pensioners' death rates are assumed</strong>
              70% of the population's, a round number, not fitted to South African pensioners. The Capital page shows how much it matters.
            </li>
            <li>
              <strong>Ranges are too narrow</strong>
              The mortality forecast's 95% ranges caught fewer outcomes than they should have, for both sexes. Read every range here as a lower bound.
            </li>
            <li>
              <strong>The backtests flatter the models</strong>
              Each holdout period was short and was also used to choose between models, so the scores are likely better than out-of-sample performance would be.
            </li>
            <li>
              <strong>Fixed-rate yields fit poorly</strong>
              The fixed-rate curve missed the 0.25% auction-yield target. It drives the level pensions and the funeral discounting.
            </li>
            <li>
              <strong>One borrower</strong>
              Every asset is South African government debt. The standard formula charges nothing for that concentration, and neither does this model.
            </li>
            <li>
              <strong>The pensions are priced at cost</strong>
              Prices carry no expense or profit loading, which is why the insurance profit is so small. Funeral premiums carry a 20% margin.
            </li>
            <li>
              <strong>Simplified rules</strong>
              No tax, the bond curves in place of the regulator's risk-free curve, and the other simplifications listed in each plan.
            </li>
          </ul>
        </div>
      </section>

      <section className="section">
        <h2>The technical detail</h2>
        <p className="sub">For actuaries and quants: the full charts, tables and caveats.</p>
        <Disclose title="Mortality forecasts" sub="Backtest, model risk, data quality, the annuitant assumption">
          <Backtest r={r} />
          {r.compare && <Sources r={r} />}
          <Sensitivity r={r} />
        </Disclose>
        {v2 && (
          <Disclose title="Bond curves and matching" sub="Curve backtest, pension prices on the curve, duration matching">
            <CurveBacktest v={v2} />
            <CurvePrices v={v2} r={r} />
            <Matching v={v2} />
          </Disclose>
        )}
        {v3 && (
          <Disclose title="Balance sheet and solvency" sub={`SAM standard formula, valuation date ${longDate(v3.valuation_date)}`}>
            <Interest v={v3} />
            <BalanceSheet v={v3} />
          </Disclose>
        )}
      </section>

      <section className="section">
        <h2>Data and credits</h2>
        <div className="card">
          <ul className="method">
            <li>
              <strong>Deaths</strong>
              Statistics South Africa, Mortality and Causes of Death 1997 to 2022, unit records, distributed by DataFirst, University of Cape Town.
            </li>
            <li>
              <strong>Population and life tables</strong>
              United Nations, Population Division (2024), World Population Prospects 2024, CC BY 3.0 IGO. Stats SA P0302 for the population check.
            </li>
            <li>
              <strong>Bonds</strong>
              National Treasury government bond auction results. Not commercial use; attribution to National Treasury.
            </li>
            <li>
              <strong>Capital rules</strong>
              Prudential Authority, Financial Soundness Standards for Insurers. Tax and the regulator's own risk-free curve are left out; the plans list
              every simplification.
            </li>
            <li>
              <strong>Code</strong>
              Python for the models, a small FastAPI service, and this React site.{" "}
              <a href={REPO} target="_blank" rel="noreferrer">
                github.com/Sbusiso-Mdingi/mdingi-life
              </a>
            </li>
            <li>
              <strong>Fictional company</strong>
              Mdingi Life does not exist and sells nothing. The customers are invented; the data and rules are real, the results are a model's. Nothing here
              is a quote or actuarial advice.
            </li>
          </ul>
        </div>
      </section>
    </>
  );
}


// The next five years -----------------------------------------------------------------------------------------------

const STRESS: Record<string, { name: string; note: string }> = {
  "S1 Rates fall": { name: "Interest rates fall", note: "Both curves 1.5 points lower, then drifting back" },
  "S2 Longevity": { name: "Pensioners live longer", note: "Their death rates 20% lower for good: my own test, harsher than the regulator's 10%" },
  "S3 Pandemic year": { name: "A pandemic year", note: "Deaths as in 2021 against 2019, for one year" },
  "S4 Lapse wave": { name: "Customers leave", note: "30% of funeral policies cancelled at once" },
  "S5 All at once": { name: "All three at once", note: "Rates fall, a pandemic year and customers leave" },
};

export function Future({ r }: { r: Research }) {
  const v = r.v4!;
  const [rate, setRate] = useState<"nominal" | "real">("nominal");
  const y0 = Number(v.valuation_date.slice(0, 4));
  const years = v.central.map((_, t) => y0 + t);
  const s = v.scenarios;
  const c = s.cover;
  const ifrs = v.ifrs17["0.1"];
  const fanBands = (p: Pct, color: string, what: string) => [
    { key: "90", label: `9 in 10 ${what}`, color, xs: years, lo: p["5"], hi: p["95"] },
    { key: "50", label: `Half of ${what}`, color, xs: years, lo: p["25"], hi: p["75"] },
  ];
  const ten = v.esg.ten_year[rate];
  const hist = v.esg.history[rate];
  const stress: Bar[] = Object.entries(v.stresses).map(([k, x]) => {
    const worst = Math.min(...x.cover);
    return { key: k, name: STRESS[k]?.name ?? k, note: STRESS[k]?.note, value: Math.max(worst, 0), label: coverPct(worst), color: worst >= 1 ? "var(--s1)" : "var(--s3)" };
  });
  const failed = Object.entries(v.stresses).filter(([, x]) => !x.A2);
  const below = s.below_one_share;
  const m = (x: number[]) => x.map((y) => y / 1e6);
  return (
    <>
      <PageHead kicker="The next five years" title="Does the cover hold up?">
        A look five years ahead, of the kind the regulator asks every insurer for: a thousand possible paths for interest rates and inflation, and five named
        disasters, each run through the customers, the bonds and the capital, year by year.
      </PageHead>

      <div className="grid three">
        <Stat label="Solvency cover in five years" value={coverPct(c["50"][5])} sub={`In the middle future, from ${coverPct(c["50"][0])} today`} good={c["50"][5] >= 1} />
        <Stat label="Futures that stay above 100%" value={pct(s.A1.share_covered, 0)} sub="Every year for five years, against the 95% I set beforehand">
          {s.A1.pass ? <Pill kind="good">Meets the target</Pill> : <Pill kind="bad">Misses the target</Pill>}
        </Stat>
        <Stat
          label="Lowest cover if pensioners live longer"
          value={coverPct(Math.min(...v.stresses["S2 Longevity"].cover))}
          sub={`It would take ${randM(v.stresses["S2 Longevity"].capital_to_restore)} of new capital to get back to 100%`}
          good={false}
        >
          {failed.length ? <Pill kind="bad">{failed.length} of 5 disasters go below 100%</Pill> : <Pill kind="good">Every disaster stays above 100%</Pill>}
        </Stat>
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">Solvency cover across a thousand futures</h2>
            <p className="eyebrow">Capital held over capital required, at the end of each year from {longDate(v.valuation_date)}</p>
          </div>
        </div>
        <Legend
          items={[
            { label: "Middle future", color: "var(--s1)" },
            { label: "Rates as expected", color: "var(--s2)", kind: "dash" },
            { label: "Half of futures", color: "var(--s1)", kind: "band" },
            { label: "9 in 10 futures", color: "var(--s1)", kind: "band" },
            { label: "Regulator's minimum", color: "var(--muted-foreground)", kind: "dash" },
          ]}
        />
        <YearChart
          label="Solvency cover at each year-end over five years: the middle of 1,000 scenarios, the central path, and the ranges holding half and 9 in 10 of them"
          series={[
            { key: "min", label: "Regulator's minimum", color: "var(--muted-foreground)", xs: years, ys: years.map(() => 1), dash: true },
            { key: "central", label: "Rates as expected", color: "var(--s2)", xs: years, ys: v.central.map((y) => y.cover), dash: true },
            { key: "median", label: "Middle future", color: "var(--s1)", xs: years, ys: c["50"] },
          ]}
          bands={fanBands(c, "var(--s1)", "futures")}
          fmt={coverPct}
          height={300}
        />
        <p className="note">
          If interest rates follow their expected path, cover climbs from {coverPct(v.central[0].cover)} to {coverPct(v.central[5].cover)}: the business earns
          more than the capital it ties up. But rates rarely do what is expected. In {pct(below, 0)} of the futures cover dips below 100% at least once, against
          a target of no more than 5%. The bonds match what is owed to pensioners, but not the risk margin and capital requirement the regulator adds on top, so a
          fall in rates still hurts.
        </p>
        <p className="note caveat">
          The rate model was fitted on 2011 to 2026 and judged on the same years, so these ranges are likely narrower than the real ones. With March to May 2020
          left out of the fit, {pct(v.sensitivities.covid_excluded.A1.share_covered, 0)} of futures stay covered rather than {pct(s.A1.share_covered, 0)}: three
          months of data move the answer that much.
        </p>
        <TableView>
          <table>
            <thead>
              <tr>
                <th>Year-end</th>
                <th className="num">Rates as expected</th>
                <th className="num">5th percentile</th>
                <th className="num">Middle</th>
                <th className="num">95th percentile</th>
                <th className="num">Futures below 100%</th>
              </tr>
            </thead>
            <tbody>
              {years.map((y, t) => (
                <tr key={y}>
                  <td>{t === 0 ? `Today (${y})` : y}</td>
                  <td className="num">{coverPct(v.central[t].cover)}</td>
                  <td className="num">{coverPct(c["5"][t])}</td>
                  <td className="num">{coverPct(c["50"][t])}</td>
                  <td className="num">{coverPct(c["95"][t])}</td>
                  <td className="num">{pct(s.below_one_by_year[t], 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableView>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">Where interest rates could go</h2>
            <p className="eyebrow">The 10-year {rate === "nominal" ? "fixed-rate" : "inflation-linked"} government bond yield, each September and in the modelled futures</p>
          </div>
          <Segmented
            label="Curve"
            value={rate}
            onChange={setRate}
            options={[
              { id: "nominal", label: "Fixed-rate" },
              { id: "real", label: "Inflation-linked" },
            ]}
          />
        </div>
        <Legend
          items={[
            { label: "What happened", color: "var(--s2)" },
            { label: "Middle future", color: "var(--s1)" },
            { label: "Half of futures", color: "var(--s1)", kind: "band" },
            { label: "9 in 10 futures", color: "var(--s1)", kind: "band" },
          ]}
        />
        <YearChart
          label={`The 10-year ${rate} zero rate each September since ${hist.years[0]}, and its spread over 1,000 scenarios for the next five years`}
          series={[
            { key: "hist", label: "What happened", color: "var(--s2)", xs: hist.years, ys: hist.rate },
            { key: "median", label: "Middle future", color: "var(--s1)", xs: years, ys: ten["50"] },
          ]}
          bands={fanBands(ten, "var(--s1)", "futures")}
          fmt={(x) => pct(x, 1)}
          height={280}
        />
        <p className="note">
          The futures come from a model of how the whole curve moved month by month since 2011, each curve reduced to a level and a slope. In a year, its rates
          move about as much as they did in the past: {num(v.checks.E1[rate].ratio, 2)} times the historical spread, inside the 0.75 to 1.33 I set beforehand{rate === "nominal" ? ", though only just" : ""}.
          Its worst 1-in-200 fall over a year, {num(-v.esg.checks.E2[rate].scenario_q005 * 100, 1)} points, is close to the regulator's own rate shock at 10 years,{" "}
          {num(-v.esg.checks.E2[rate].sam_down_10y * 100, 1)} points.
        </p>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">Five disasters</h2>
            <p className="eyebrow">Lowest solvency cover over the five years under each</p>
          </div>
        </div>
        <HBars rows={stress} max={Math.max(1.5, ...stress.map((x) => x.value))} marker={1} markerLabel="The line marks 100%, the regulator's minimum." />
        <p className="note">
          A pandemic year or a wave of cancellations is absorbed. A fall in interest rates takes cover below 100% at once, and it recovers within{" "}
          {Math.max(...failed.filter(([k]) => k !== "S2 Longevity").map(([, x]) => x.cover.findIndex((y) => y >= 1)), 0)} years as rates drift back. Pensioners living
          longer is the one the company could not ride out: the pensions would cost {randM(v.stresses["S2 Longevity"].losses + v.stresses["S2 Longevity"].csm_used)} more,
          and it would take {randM(v.stresses["S2 Longevity"].capital_to_restore)} of new capital to get back to 100%. This is a harsher test than the
          regulator's own longevity shock on the Capital page (death rates 10% lower and improving faster), which is what sets the capital requirement.
        </p>
        <div className="callout">
          <strong>What I would do next</strong>
          Reinsure part of the longevity risk, which shrinks both the capital requirement and the risk margin, and hedge their sensitivity to rates as well as the
          pensions'. Neither is modelled here.
        </div>
        <TableView>
          <table>
            <thead>
              <tr>
                <th>Disaster</th>
                {years.map((y) => (
                  <th key={y} className="num">
                    {y}
                  </th>
                ))}
                <th className="num">New capital needed</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(v.stresses).map(([k, x]) => (
                <tr key={k}>
                  <td>
                    {STRESS[k]?.name ?? k}
                    <div className="plain">{STRESS[k]?.note}</div>
                  </td>
                  {x.cover.map((y, t) => (
                    <td key={t} className="num">
                      {coverPct(y)}
                    </td>
                  ))}
                  <td className="num">{randM(x.capital_to_restore)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableView>
      </section>

      {v.capital && v.capital.levels.length > 1 && <CapitalCurve c={v.capital} />}

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">The profit it would report</h2>
            <p className="eyebrow">IFRS 17 profit each year if rates move as expected, R million</p>
          </div>
        </div>
        <Legend
          items={[
            { label: "Profit", color: "var(--s1)" },
            { label: "From insurance", color: "var(--s2)" },
            { label: "From investments", color: "var(--s3)" },
          ]}
        />
        <YearChart
          label="IFRS 17 profit each year on the central path, split into the insurance service result and the net finance result, R million"
          series={[
            { key: "p", label: "Profit", color: "var(--s1)", xs: years.slice(1), ys: m(ifrs.profit) },
            { key: "s", label: "From insurance", color: "var(--s2)", xs: years.slice(1), ys: m(ifrs.service_result) },
            { key: "f", label: "From investments", color: "var(--s3)", xs: years.slice(1), ys: m(ifrs.finance_result) },
          ]}
          fmt={(x) => `R${num(x, 0)}m`}
          height={260}
        />
        <p className="note">
          Accounts and solvency measure the same business differently. Under IFRS 17 the profit expected from the policies is held back in a reserve, the
          contractual service margin, and released as cover is provided: {randM(ifrs.csm[0])} today. Most of the profit is investment return, on the company's own capital as
          well as on the bonds behind the pensions. Across the thousand futures, profit in the first year ranges
          from {randM(s.profit["5"][0])} to {randM(s.profit["95"][0])}, nine times in ten.
        </p>
        <TableView>
          <table>
            <thead>
              <tr>
                <th>Year</th>
                <th className="num">Profit</th>
                <th className="num">From insurance</th>
                <th className="num">From investments</th>
                <th className="num">Reserve for future profit, year-end</th>
              </tr>
            </thead>
            <tbody>
              {years.slice(1).map((y, t) => (
                <tr key={y}>
                  <td>{y}</td>
                  <td className="num">{randM(ifrs.profit[t], 1)}</td>
                  <td className="num">{randM(ifrs.service_result[t], 1)}</td>
                  <td className="num">{randM(ifrs.finance_result[t], 1)}</td>
                  <td className="num">{randM(ifrs.csm[t + 1], 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableView>
      </section>
    </>
  );
}

/** The added runs: starting capital against the share of futures covered throughout. */
function CapitalCurve({ c }: { c: NonNullable<NonNullable<Research["v4"]>["capital"]> }) {
  const L = c.levels;
  const xs = L.map((x) => x.own_funds / 1e6);
  const hit = L.find((x) => x.own_funds === REFERENCE && x.share_covered >= 0.95) ?? L.find((x) => x.share_covered >= 0.95);
  const below = hit && [...L].reverse().find((x) => x.own_funds < hit.own_funds && x.share_covered < 0.95);
  const names = Object.keys(L[0].stresses);
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2 className="serif">How much capital would be enough?</h2>
          <Pill kind="warn">Exploratory</Pill>
          <p className="eyebrow">Share of the 1,000 futures above 100% at every year-end, by starting capital. Rule: {c.rule}.</p>
        </div>
      </div>
      <Legend
        items={[
          { label: "Futures covered throughout", color: "var(--s1)" },
          { label: "The 95% target", color: "var(--muted-foreground)", kind: "dash" },
        ]}
      />
      <YearChart
        label={`Share of futures covered at every year-end against starting capital from R${xs[0]}m to R${xs[xs.length - 1]}m; ${c.rule}`}
        series={[
          { key: "t", label: "The 95% target", color: "var(--muted-foreground)", xs, ys: xs.map(() => 0.95), dash: true },
          { key: "s", label: "Futures covered throughout", color: "var(--s1)", xs, ys: L.map((x) => x.share_covered) },
        ]}
        points={[{ key: "p", label: "Run", color: "var(--s1)", xs, ys: L.map((x) => x.share_covered) }]}
        fmt={(x) => pct(x, 0)}
        xFmt={(x) => `R${num(x, 0)}m`}
        height={280}
      />
      <p className="note">
        I added this after seeing that only {pct(L[0].share_covered, 0)} of futures stay covered at {randM(L[0].own_funds)}, so it is an exploration, not a
        test set beforehand. Every level uses the same 1,000 futures, regenerated from the same seed, and the same five disasters; each extra rand is invested in
        the same mix of bonds and bills as today's assets.{" "}
        {hit && below
          ? `The 95% target is crossed between ${randM(below.own_funds)} (${pct(below.share_covered, 1)}) and ${randM(hit.own_funds)} (${pct(hit.share_covered, 1)}), the industry-typical cover of about 1.8 times. I did not run points in between to narrow it.`
          : `Even ${randM(L[L.length - 1].own_funds)} does not reach 95%.`}{" "}
        Every point is a full run; the line between them is drawn, not modelled. All of it uses the v1 mortality model; it will be rerun once,
        at R400m, R500m and R627m, when the mortality revision is final.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Starting capital</th>
              <th className="num">Capital required</th>
              <th className="num">Cover today</th>
              <th className="num">Futures covered throughout</th>
              {names.map((n) => (
                <th key={n} className="num">
                  Lowest, {(STRESS[n]?.name ?? n).toLowerCase()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {L.map((x) => (
              <tr key={x.own_funds}>
                <td>{randM(x.own_funds)}</td>
                <td className="num">{randM(x.scr)}</td>
                <td className="num">{coverPct(x.cover)}</td>
                <td className="num">{pct(x.share_covered, 1)}</td>
                {names.map((n) => (
                  <td key={n} className="num">
                    {coverPct(x.stresses[n])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
