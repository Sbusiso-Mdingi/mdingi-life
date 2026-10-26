import { useState, type ReactNode } from "react";
import type { Book, Research, Sex, V3 } from "./api";
import { BarChart, IntervalChart, type BarGroup, type Interval } from "./charts";
import { BalanceSheet, Backtest, CurveBacktest, CurvePanel, CurvePrices, FanPanel, History, Interest, Matching, Sensitivity, Sources } from "./detail";
import { SEX_LABEL, num, pct, thousands } from "./format";
import { AGES, COLOR, KEYS, REPO, SEXES, Segmented, TableView, Verdict, f2, longDate, v2find } from "./ui";

export type Tab = "overview" | "quote" | "customers" | "investments" | "capital" | "built";
type Go = (t: Tab) => void;

const randFull = (v: number) => `R${thousands(v)}`;
const randM = (v: number, digits = 0) => `R${(v / 1e6).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}m`;
const randBn = (v: number) => `R${(v / 1e9).toFixed(1)}bn`;
const cents = (v: number) => `R${v.toFixed(2)}`;
const coverPct = (c: number) => `${Math.round(c * 100)}%`;
const PERSON: Record<Sex, string> = { Male: "Man", Female: "Woman" };
const doc = (f: string) => `${REPO}/blob/main/research/${f}`;

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

export function Overview({ r, go }: { r: Research; go: Go }) {
  const v = r.v3!;
  const b = v.book!;
  const now = current(v);
  const k = v.key_rate;
  const m = v.main;
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
    { key: "bel", label: "What we expect to pay customers", value: now.bel.total, color: "var(--s3)" },
    { key: "rm", label: "Risk margin", value: now.risk_margin, color: "var(--gold)" },
    { key: "own", label: "Our own capital", value: now.own_funds, color: "var(--primary-strong)" },
  ];
  const total = m.assets.total;
  const cut = k ? 1 - k.interest.combined / m.interest.combined : 0;
  return (
    <>
      <section className="hero">
        <p className="kicker">Welcome to Mdingi Life</p>
        <h1>
          We pay pensions to {thousands(b.annuities.n)} retirees and cover {thousands(b.funeral.n)} families' funerals.
        </h1>
        <p>
          Take a look around as if it were your first week here. Quote a customer, meet the people we cover, see where their money is invested, and
          check that we can keep every promise, even in a very bad year.
        </p>
        <div className="actions">
          <button className="cta" onClick={() => go("quote")}>
            Get a quote
          </button>
          <button className="cta ghost" onClick={() => go("capital")}>
            How safe are we?
          </button>
        </div>
      </section>

      <div className="grid four kpis">
        <Stat label="Pensions paid each year" value={randM(b.annuities.income)} sub={`To ${thousands(b.annuities.n)} retirees, typically aged ${Math.round(b.annuities.median_age)}`} />
        <Stat label="Funeral cover in force" value={b.funeral.cover >= 1e9 ? randBn(b.funeral.cover) : randM(b.funeral.cover)} sub={`${thousands(b.funeral.n)} policies, from ${cents(minPremium)} a month`} />
        <Stat label="Invested for our customers" value={randBn(total)} sub={`In ${bonds} South African government bonds, and cash`} />
        <Stat label="Solvency cover" value={coverPct(now.cover)} good={now.cover >= 1} sub={`${randM(now.own_funds)} of capital against ${randM(now.scr)} required`}>
          {now.cover >= 1 ? <Pill kind="good">Above the regulator's 100%</Pill> : <Pill kind="bad">Below the regulator's 100%</Pill>}
        </Stat>
      </div>

      <section className="section">
        <h2>Our year so far</h2>
        <p className="sub">Four things happened at Mdingi Life this year. Each one has its own page.</p>
        <div className="steps">
          <div className="card step">
            <span className="num-badge">1</span>
            <h3>We priced our pensions</h3>
            <p>
              Using 26 years of Stats SA death records, we forecast how long our customers will live, and how unsure that forecast is.
              {pension && " A woman of 65 who wants R10,000 a month for life, rising with inflation, pays once:"}
            </p>
            {pension && <div className="figure">{randFull(Math.round(pension / 1000) * 1000)}</div>}
            <button className="link" onClick={() => go("quote")}>
              Get your own quote →
            </button>
          </div>
          <div className="card step">
            <span className="num-badge">2</span>
            <h3>We invested the money</h3>
            <p>
              Pensions are paid for decades. So the money sits in government bonds that pay us back over the same years, read off the Treasury's own
              auctions.
            </p>
            <div className="figure">{randBn(total)}</div>
            <button className="link" onClick={() => go("investments")}>
              See where it is →
            </button>
          </div>
          <div className="card step">
            <span className="num-badge">3</span>
            <h3>We took the regulator's test</h3>
            <p>
              The rules ask: if a 1-in-200 year hit, could we still pay everyone? With our first choice of bonds, not quite. We needed {coverPct(1)} and had:
            </p>
            <div className="figure">
              {coverPct(m.cover)} {m.cover < 1 && <Pill kind="bad">Short by {randM(m.scr - m.own_funds, 0)}</Pill>}
            </div>
            <button className="link" onClick={() => go("capital")}>
              What went wrong →
            </button>
          </div>
          {k && (
            <div className="card step">
              <span className="num-badge">4</span>
              <h3>We fixed it without new money</h3>
              <p>
                We spread the bonds across 5 to 30 years, so they move the way our pensions do. That cut our interest-rate risk by {pct(cut, 0)} and lifted
                cover to:
              </p>
              <div className="figure">
                {coverPct(k.cover)} {k.cover >= 1 && <Pill kind="good">Covered</Pill>}
              </div>
              <button className="link" onClick={() => go("investments")}>
                How matching works →
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="section">
        <h2>Our balance sheet in one picture</h2>
        <p className="sub">
          What we own, and who it is for, on {longDate(v.valuation_date)}. Both sides add up to {randBn(total)}.
        </p>
        <div className="card">
          {[
            { who: "What we own", parts: own },
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
            Our funeral customers will pay us {randM(m.bel_parts.premiums)} in future premiums, against {randM(m.bel_parts.claims)} of claims and{" "}
            {randM(m.bel_parts.fun_expenses)} of running costs. The {randM(-m.bel.funeral)} difference is netted off what we owe. The risk margin is what
            another insurer would charge to take the book over; our own capital is the cushion above that.
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
      <PageHead kicker="Get a quote" title="What would cover cost you?">
        These are the prices our pricing team works with. They are built on Stats SA death records and on the government bond market of{" "}
        {longDate(v2.curves.ilb.date)}.
      </PageHead>
      <div className="grid two">
        <section className="card" aria-label="Retirement income quote">
          <h3>A pension for life</h3>
          <p>Pay once when you retire, and we pay you every month for as long as you live.</p>
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
                Likely range <b>{randFull(Math.round((p.lo * yearly) / 100) * 100)}</b> to <b>{randFull(Math.round((p.hi * yearly) / 100) * 100)}</b>
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
                <b>{cents(rate.fixed)}</b> of it covers running your policy, and <b>{cents(rate.per_rand * sum)}</b> the cover itself.
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
              {kind === "inflation-linked" ? "Rising" : "Level"} pension of {randFull(monthly)} a month: what it costs, in R million, with the range our forecast allows
            </p>
          </div>
        </div>
        <IntervalChart label={`Price of a pension of ${randFull(monthly)} a month by sex and age at retirement, R million`} rows={rows} fmt={(x) => `R${x.toFixed(2)}m`} groups={2} />
        <p className="note">
          The price depends on how long you will live, and nobody knows that for sure. We forecast it from Stats SA death records and simulate thousands of
          possible futures; the bar is the middle 95% of them. Women live longer, so their pensions cost more. We assume people who buy pensions live
          longer than South Africans on average, with death rates 30% lower.
        </p>
        <div className="callout">
          <strong>What a real quote would add</strong>
          These prices cover the pension itself. A real insurer adds its costs, commission and profit, and checks your health. The funeral premiums already
          include our running costs (R15 a month) and a 20% margin.
        </div>
      </section>
    </>
  );
}

// Our customers -----------------------------------------------------------------------------------------------------

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
      <PageHead kicker="Our customers" title="The people we look after">
        {thousands(a.n)} pensioners and {thousands(f.n)} funeral policyholders. They are invented, but drawn to look like a real South African book.
      </PageHead>

      <div className="grid two">
        <section className="card">
          <h3>Pensioners</h3>
          <div className="grid three" style={{ marginTop: 14, gap: 10 }}>
            <div className="metric">
              <div className="value">{Math.round(a.median_age)}</div>
              <div className="sub">typical age</div>
            </div>
            <div className="metric">
              <div className="value">{randFull(Math.round(a.median_income / 12 / 10) * 10)}</div>
              <div className="sub">typical monthly pension</div>
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
              <div className="sub">typical age</div>
            </div>
            <div className="metric">
              <div className="value">{cents(f.median_premium)}</div>
              <div className="sub">typical monthly premium</div>
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
        <h2>Meet a few of them</h2>
        <p className="sub">The first policies on our books.</p>
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
        <h2>How long our customers live</h2>
        <p className="sub">
          Everything we promise depends on this. South African life expectancy fell sharply with HIV and recovered with treatment, so the past is a poor
          straight-line guide to the future.
        </p>
        {r.history && <History r={r} />}
        <FanPanel r={r} />
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
      { key: "l", label: "Our pensions", color: "var(--s1)", value: m.dv01[curve].liability[t] / 1e3 },
      { key: "d", label: "First portfolio (two bonds)", color: "var(--s2)", value: m.dv01[curve].portfolio[t] / 1e3 },
      ...(k ? [{ key: "k", label: "Rebalanced portfolio", color: "var(--s3)", value: k.dv01[curve].portfolio[t] / 1e3 }] : []),
    ],
  }));
  const d = m.dv01.real;
  return (
    <>
      <PageHead kicker="Investments" title="Where the money is">
        Every rand we owe our customers is invested in South African government bonds and cash, chosen so their value moves in step with what we owe.
      </PageHead>

      {k && (
        <section className="card">
          <h3>What we hold today</h3>
          <p>
            {randM(m.assets.total)} across {holdings.length - 1} government bonds and a Treasury bill. Inflation-linked bonds pay the pensions that rise with
            inflation; fixed-rate bonds pay the level ones.
          </p>
          <HBars rows={holdings} />
        </section>
      )}

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">Matching our promises, year by year</h2>
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
        <BarChart label="Sensitivity of our pensions and of each bond portfolio to a 0.01% rise in yields at 5, 10, 20 and 30 years, R thousand" groups={groups} fmt={(x) => `R${num(x, 0)}k`} height={260} />
        <p className="note">
          When interest rates move, the value of our pensions moves, and so must the bonds behind them. Our first portfolio held two bonds of each kind that matched the
          pensions on average, but bunched all the risk around 10 years: R{num(d.portfolio["10"] / 1e3, 0)}k against our R{num(d.liability["10"] / 1e3, 0)}k,
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
    { key: "lon", name: "People live longer", note: "Pensioners' death rates 10% lower, falling faster", value: now.life.longevity, label: randM(now.life.longevity, 1), color: "var(--s1)" },
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
      <PageHead kicker="Capital" title="Can we keep our promises?">
        The Prudential Authority asks every insurer to hold enough capital to survive a 1-in-200 year: the solvency capital requirement. Our cover is the
        capital we hold divided by that requirement. It needs to be at least 100%.
      </PageHead>

      <div className="grid three">
        <Stat label="Solvency cover today" value={coverPct(now.cover)} good={now.cover >= 1}>
          {now.cover >= 1 ? <Pill kind="good">Meets the requirement</Pill> : <Pill kind="bad">Below the requirement</Pill>}
        </Stat>
        <Stat label="Capital required" value={randM(now.scr)} sub="To survive a 1-in-200 year" />
        <Stat label="Capital we hold" value={randM(now.own_funds)} sub={`${coverPct(median)} cover, the life industry's typical level, would need ${randM(now.scr * median)}`} />
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">How we invest decides whether we pass</h2>
            <p className="eyebrow">Solvency cover on the same {randM(m.own_funds)} of capital, by how the money is invested</p>
          </div>
        </div>
        <HBars rows={strategies} max={Math.max(1.3, ...strategies.map((s) => s.value))} marker={1} markerLabel="The line marks 100%, the regulator's minimum." />
        <p className="note">
          With everything in cash, a fall in interest rates would raise the value of our pensions with nothing to offset it, and we would need almost three
          times our capital. Our first portfolio fixed most of that, but not the far end of the curve.{" "}
          {k ? `Spreading the bonds across 5 to 30 years took us over the line without raising a rand.` : ""}
        </p>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">What we hold capital against</h2>
            <p className="eyebrow">Loss in each of the regulator's stress tests, R million</p>
          </div>
        </div>
        <HBars rows={stress} />
        <p className="note">
          Taken one at a time these losses add up to {randM(sum)}. They would not all happen in the same year, so the regulator's formula combines them into a
          requirement of {randM(now.scr)}. People living longer is by far our biggest risk: it is {pct(now.life.longevity / sum, 0)} of the total, because our
          pensions are paid for as long as people live. The funeral business barely registers. It is profitable, so its main risk is customers leaving.
        </p>
        <div className="callout">
          <strong>What we would do next</strong>
          Our bonds now match our pensions closely, so the remaining risk is mostly longevity. The usual next step is to reinsure part of it. We have not
          modelled that yet.
        </div>
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
    </>
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

export function Built({ r }: { r: Research }) {
  const t = r.backtest.tests;
  const v2 = r.v2, v3 = r.v3;
  const both = (x: Record<Sex, boolean>) => SEXES.map((s) => <Verdict key={s} pass={x[s]} who={SEX_LABEL[s]} />);
  const checks: { claim: string; plain: string; verdicts: ReactNode }[] = [
    { claim: "Death rates keep improving", plain: "The forecast beat a no-improvement baseline on 2017 to 2019.", verdicts: both(t.P1) },
    { claim: "The HIV years are handled", plain: "Fitting from 2006, after HIV deaths peaked, beat fitting from 1997.", verdicts: both(t.P2) },
    {
      claim: "The forecast ranges are honest",
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
      { claim: "The valuation engine is right", plain: "A simple month-by-month calculation agrees with the engine to better than one part in a trillion, under every stress.", verdicts: <Verdict pass={v3.checks.K1.pass} /> },
      { claim: "Matching cuts interest-rate risk below a quarter", plain: `The first portfolio cut it to ${f2(v3.checks.K3.ratio)} of the unmatched risk.`, verdicts: <Verdict pass={v3.checks.K3.pass} /> },
      { claim: "Longevity is the largest risk", plain: "As expected for a pension book.", verdicts: <Verdict pass={v3.checks.K4.pass} /> },
    );
    if (v3.key_rate)
      checks.push({
        claim: "Rebalancing beats the first portfolio",
        plain: "Added after the first result was seen, and written down before it was run.",
        verdicts: <Verdict pass={v3.key_rate.checks.K6.pass} />,
      });
  }
  return (
    <>
      <PageHead kicker="How it's built" title="The work behind the numbers">
        Mdingi Life is a portfolio project by Sbusiso Mdingi. For each part, the rules, tests and pass marks were written down and committed before any
        result was seen. The results are reported as they came out, failures included.
      </PageHead>

      <div className="grid three">
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
            </a>
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
            </a>
          </p>
        </div>
        <div className="card">
          <div className="icon-badge" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          </div>
          <h3>Testing our capital</h3>
          <p>The Prudential Authority's standard formula for solvency (SAM), applied to an invented book of pensions and funeral policies.</p>
          <p>
            <a href={doc("PROTOCOL_v3.md")} target="_blank" rel="noreferrer">
              Plan
            </a>{" "}
            ·{" "}
            <a href={doc("RESULTS_v3.md")} target="_blank" rel="noreferrer">
              Results
            </a>
          </p>
        </div>
      </div>

      <section className="section">
        <h2>The checks, and how they came out</h2>
        <p className="sub">Each was set before the result it checks.</p>
        <div className="card">
          <ul className="checks">
            {checks.map((c) => (
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
              Mdingi Life does not exist and sells nothing. The customers are invented. Nothing here is a quote or actuarial advice.
            </li>
          </ul>
        </div>
      </section>
    </>
  );
}

