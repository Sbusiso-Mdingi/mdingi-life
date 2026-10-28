import { useState, type ReactNode } from "react";
import type { Book, BookV7, Pct, PremiumType, Research, Sex } from "./api";
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

/** An age-rated policy's monthly premium in policy year j (0 the first), for entry age `entry` and cover `sum`; the
 * last priced year carries on, as in book_v7.rows. */
const ratedPremium = (b: BookV7, s: Sex, entry: number, j: number, sum: number) => {
  const r = b.schedule[s][String(entry)];
  const k = Math.min(j, r.per_rand.length - 1);
  return r.per_rand[k] * sum + r.fixed[k];
};
const TYPE_LABEL: Record<PremiumType, string> = { level: "level", "age-rated": "age-rated" };
const RISK_LABEL: Record<string, string> = {
  lapse: "funeral customers leaving",
  expense: "running costs rising",
  longevity: "pensioners living longer",
  mortality: "more funeral deaths",
  catastrophe: "a pandemic",
};
const PERSON: Record<Sex, string> = { Male: "Man", Female: "Woman" };
const doc = (f: string) => `${REPO}/blob/main/research/${f}`;

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

type Levels = NonNullable<NonNullable<Research["v4"]>["capital"]>["levels"];

/** The completed levels either side of 95%: the lowest run at or above it, and the highest run below that. */
const levelsAround = (L: Levels) => {
  const hi = L.find((x) => x.share_covered >= 0.95);
  const lo = hi && [...L].reverse().find((x) => x.own_funds < hi.own_funds && x.share_covered < 0.95);
  return hi && lo ? { lo, hi } : null;
};

export const crossing = (r: Research) => levelsAround(r.v4?.capital?.levels ?? []);

type Finding = { key: string; figure: string; pill?: ReactNode; text: ReactNode; tab?: Tab };

export function Overview({ r, go }: { r: Research; go: Go }) {
  const v = r.v7!;
  const b = v.book;
  const m = v.main;
  const p = v.projection;
  const pension = r.v2 ? v2find(r.v2, "Female", 65, 0.7)["inflation-linked LI"].median * 120_000 : null;
  const held = (k: "real" | "nominal") => Object.values(m.holdings[k] ?? {}).reduce((a, x) => a + x, 0);
  const minPremium = Math.min(
    ...SEXES.flatMap((s) => b.premium_rates[s].flatMap((x) => [x.level.per_rand * b.sums[0] + x.level.fixed, ratedPremium(b, s, x.age, 0, b.sums[0])])),
  );
  const nBonds = Object.values(m.holdings).reduce((a, h) => a + Object.keys(h ?? {}).length, 0);
  const own = [
    { key: "ilb", label: "Inflation-linked government bonds", value: held("real"), color: "var(--s1)" },
    { key: "fixed", label: "Fixed-rate government bonds", value: held("nominal"), color: "var(--s2)" },
    { key: "bill", label: "Treasury bill (cash)", value: m.assets.bill, color: "#8a968f" },
    { key: "credit", label: "Premiums due and bank cash", value: m.assets.credit, color: "#5f6f68" },
  ].filter((x) => x.value > 0);
  const owe = [
    { key: "bel", label: "Owed to customers (best estimate)", value: m.bel.total, color: "var(--s3)" },
    { key: "rm", label: "Risk margin", value: m.risk_margin, color: "var(--gold)" },
    { key: "own", label: "Own capital", value: m.own_funds, color: "var(--primary-strong)" },
  ];
  const total = m.assets.total;
  const p3 = r.backtest.tests.P3;
  const perPensioner = v.policies.funeral / v.policies.annuitants;
  const onePct = 0.01 * v.scales.annuities * Math.abs(v.exposures.annuities);
  const floor = p?.capital?.levels.find((x) => x.cover < 1.5);
  const floor6 = r.v6?.projection?.capital?.levels.find((x) => x.cover < 1.5);
  const ranked = (Object.entries(m.life) as [string, number][]).sort((a, b) => b[1] - a[1]);
  const [biggest, second] = ranked;
  const cc = v.central_compare;
  const findings: Finding[] = [
    {
      key: "mix",
      figure: `${Math.round(perPensioner)} to 1`,
      pill: <Pill kind="good">Set by rule</Pill>,
      text: (
        <>
          funeral policies to each pensioner. At that mix, a mistake in death rates cancels out: if everyone's death rates were 1% higher, the pensions would
          cost {randM(onePct, 1)} less and the funeral claims {randM(onePct, 1)} more. It cancels a mistake in the level, not the trend: improvement 1 point a
          year faster would still cost {randM(v.trend.total, 1)}.
        </>
      ),
      tab: "customers",
    },
    {
      key: "today",
      figure: coverPct(m.cover),
      pill: <Pill kind="good">Industry median</Pill>,
      text: (
        <>
          solvency cover on {randM(m.own_funds)} of capital, by design: I scaled the whole book until cover matched the median South African life insurer's.
          Half the funeral customers now pay premiums that rise with age, so the book that reaches that cover is bigger than before:{" "}
          {thousands(v.policies.funeral)} funeral policies, against {thousands(v.v6.policies.funeral)}.
        </>
      ),
      tab: "capital",
    },
    ...(p
      ? [
          {
            key: "five",
            figure: pct(p.scenarios.A1.share_covered, 1),
            pill: p.scenarios.A1.pass ? <Pill kind="good">Meets the 95% target</Pill> : <Pill kind="bad">Misses the 95% target</Pill>,
            text: (
              <>
                of 1,000 simulated five-year futures keep cover above 100% at every year-end, against a 95% target I set before running them. With every funeral
                premium level, as before this version, it was {r.v6?.projection ? pct(r.v6.projection.scenarios.A1.share_covered, 1) : "higher"}.
              </>
            ),
            tab: "future" as Tab,
          },
        ]
      : []),
    ...(floor
      ? [
          {
            key: "floor",
            figure: pct(floor.share_covered, 1),
            pill: <Pill kind="bad">At the minimum, much worse</Pill>,
            text: (
              <>
                is the share of futures that stay covered if the company starts at exactly 100%, on {randM(floor.own_funds, 1)} of capital
                {floor6 ? `, against ${pct(floor6.share_covered, 1)} with level premiums only, on about the same capital (${randM(floor6.own_funds, 1)})` : ""}. Most
                that fail do so in the first year ({pct(floor.below_one_by_year?.[1] ?? 0, 0)} of futures).
                {cc &&
                  ` On the expected path, the business earns ${randM(cc.v7.own_funds[1] - cc.v7.own_funds[0], 1)} in its first year, against ${randM(cc.v6.own_funds[1] - cc.v6.own_funds[0], 1)} before, and the charge for fixed-rate risk is ${randM(cc.v7.nominal[1])} against ${randM(cc.v6.nominal[1])}.`}
              </>
            ),
            tab: "future" as Tab,
          },
        ]
      : []),
    {
      key: "risk",
      figure: randM(biggest[1]),
      pill: <Pill kind="warn">Largest insurance risk</Pill>,
      text: (
        <>
          is the charge for {RISK_LABEL[biggest[0]] ?? biggest[0]}, the biggest insurance risk (only the open fixed-rate charge is larger), ahead of {RISK_LABEL[second[0]] ?? second[0]} at{" "}
          {randM(second[1])}. The funeral policies are expected to earn {randM(-m.bel.funeral)} over their lifetime, and both risks eat into that. Longevity,
          the biggest risk when the book was mostly pensions, is {randM(m.life.longevity)}.
        </>
      ),
      tab: "capital",
    },
    {
      key: "sovereign",
      figure: pct(m.sovereign.cover_one, 0),
      pill: <Pill kind="warn">Outside the formula</Pill>,
      text: (
        <>
          off the value of its government bonds and bills would take cover to 100%, and {pct(m.sovereign.own_funds_zero, 0)} would wipe out its capital.
          Almost everything it owns is lent to the South African government, which the regulator's formula charges nothing for. Its charge for the other
          borrowers, the firms that collect premiums and the bank that holds its cash, is {randM(m.credit.default, 1)}.
        </>
      ),
      tab: "capital",
    },
    {
      key: "ranges",
      figure: "Ranges too narrow",
      pill: p3.Male && p3.Female ? <Pill kind="good">Backtest passed</Pill> : <Pill kind="bad">Backtest failed</Pill>,
      text: (
        <>
          The pension mortality forecast's 95% ranges caught fewer than 90% of the death rates that actually happened in the backtest
          {p3.Male !== p3.Female ? ` for ${p3.Male ? "women" : "men"}` : ", for men and women"}, so every pension range on this site, all from the original
          mortality model (v1), is a lower bound on the real uncertainty.
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
          It pays pensions to {thousands(Math.round(b.annuities.n))} retirees and covers {thousands(Math.round(b.funeral.n))} families' funerals, a mix I set
          so that their risks offset. I priced them on Stats SA death records, invested the money on National Treasury bond auctions, tested the capital
          against the Prudential Authority's rules, and projected it five years ahead.
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
        <p className="sub">
          The main results on one screen. The mix and size were set by rules, and each test was measured against a pass mark I wrote down before running it.
        </p>
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
        <Stat label="Pensions paid each year" value={randM(b.annuities.income, 1)} sub={`To ${thousands(Math.round(b.annuities.n))} retirees, median age ${Math.round(b.annuities.median_age)}`} />
        <Stat label="Funeral cover in force" value={b.funeral.cover >= 1e9 ? randBn(b.funeral.cover) : randM(b.funeral.cover)} sub={`${thousands(Math.round(b.funeral.n))} policies, from ${cents(minPremium)} a month`} />
        <Stat label="Total assets" value={randM(total)} sub={`${randM(m.bel.total)} of it is owed to customers; the rest backs the risk margin and own capital`} />
        <Stat label="Solvency cover" value={coverPct(m.cover)} good={m.cover >= 1} sub={`${randM(m.own_funds)} of capital against ${randM(m.scr)} required`} />
      </div>

      <section className="section">
        <h2>How I built it</h2>
        <div className="steps">
          <div className="card step">
            <span className="num-badge">1</span>
            <h3>Pricing the cover</h3>
            <p>
              I forecast how long pensioners live from 26 years of Stats SA death records, on the original mortality model (v1), and priced funeral cover on
              death rates to 2024 that keep improving.
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
              The pensions and the funeral business are invested for together. The funeral profits offset much of the pensions' interest-rate risk, so{" "}
              {nBonds === 1 ? "one long inflation-linked bond covers" : `${nBonds} government bonds cover`} what is owed, and the rest is in Treasury bills.
            </p>
            <div className="figure">{randM(total)}</div>
            <button className="link" onClick={() => go("investments")}>
              See the holdings →
            </button>
          </div>
          <div className="card step">
            <span className="num-badge">3</span>
            <h3>Testing the capital</h3>
            <p>
              The regulator's standard formula asks whether the company could still pay everyone after a 1-in-200 year. I sized the book so that cover is the
              industry median:
            </p>
            <div className="figure">{coverPct(m.cover)}</div>
            <button className="link" onClick={() => go("capital")}>
              What it holds capital against →
            </button>
          </div>
          {p && (
            <div className="card step">
              <span className="num-badge">4</span>
              <h3>Looking five years ahead</h3>
              <p>A thousand simulated paths for interest rates and inflation, and five named disasters. Futures that stay above 100% every year:</p>
              <div className="figure">{pct(p.scenarios.A1.share_covered, 1)}</div>
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
          What the company owns, and who it is for, on {longDate(v.valuation_date)}. Both sides add up to {randM(total)}.
        </p>
        <div className="card">
          {[
            { who: "What it owns", parts: own },
            { who: "Who it's for", parts: owe },
          ].map((row) => (
            <div className="stack-row" key={row.who}>
              <span className="who">{row.who}</span>
              <div className="stack" role="img" aria-label={`${row.who}: ${row.parts.map((x) => `${x.label} ${randM(x.value)}`).join(", ")}`}>
                {row.parts.map((x) => (
                  <div key={x.key} style={{ flex: x.value, background: x.color }} title={`${x.label}: ${randM(x.value)}`}>
                    {x.value / total > 0.12 ? randM(x.value) : ""}
                  </div>
                ))}
              </div>
            </div>
          ))}
          <div className="keylist">
            {[...own, ...owe].map((x) => (
              <span key={x.key}>
                <i style={{ background: x.color }} />
                {x.label} <b>{randM(x.value)}</b>
              </span>
            ))}
          </div>
          <div className="callout">
            <strong>Why so little is owed to customers</strong>
            The pensions are owed {randM(m.bel.annuities)}. Funeral customers are expected to pay {randM(m.bel_parts.premiums)} in future premiums, against{" "}
            {randM(m.bel_parts.claims)} of claims and {randM(m.bel_parts.fun_expenses)} of running costs, and the {randM(-m.bel.funeral)} difference is netted
            off what the pensions are owed, leaving {randM(m.bel.total)}. The risk margin is what another insurer would charge to take the book over; own capital
            is the cushion above that.
          </div>
        </div>
      </section>
    </>
  );
}

// Get a quote -------------------------------------------------------------------------------------------------------

// The mortality model version that prices each sex: v1 for both, final after v1.1 to v1.3 failed (research/RESULTS_v1.3.md).
const PRICED_ON: Record<Sex, string> = { Male: "original mortality model (v1)", Female: "original mortality model (v1)" };

export function Quote({ r }: { r: Research }) {
  const v2 = r.v2!;
  const book = r.v7!.book;
  const [sex, setSex] = useState<Sex>("Female");
  const [age, setAge] = useState(65);
  const [kind, setKind] = useState<"inflation-linked" | "level">("inflation-linked");
  const [monthly, setMonthly] = useState(10_000);
  const p = v2find(v2, sex, age, 0.7)[`${kind} LI`];
  const yearly = monthly * 12;

  const [fsex, setFsex] = useState<Sex>("Female");
  const [fage, setFage] = useState(35);
  const [sum, setSum] = useState(book.sums[1] ?? book.sums[0]);
  const [ptype, setPtype] = useState<PremiumType>("level");
  const sched = book.schedule[fsex][String(fage)];
  const rate = ptype === "level" ? book.premium_rates[fsex].find((x) => x.age === fage)!.level : { per_rand: sched.per_rand[0], fixed: sched.fixed[0] };
  const MARGIN = book.margin;
  const premium = rate.per_rand * sum + rate.fixed;
  const ages = book.premium_rates[fsex].map((x) => x.age);
  const later = [10, 20, 30].filter((j) => fage + j <= 85).map((j) => ({ age: fage + j, premium: ratedPremium(book, fsex, fage, j, sum) }));

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
              <span className="line">
                Priced on the {PRICED_ON[sex]} for {sex === "Male" ? "men" : "women"}.
              </span>
            </div>
          </div>
        </section>

        <section className="card" aria-label="Funeral cover quote">
          <h3>Funeral cover</h3>
          <p>A fixed lump sum to your family when you die. Pay the same premium for life, or one that starts lower and rises as you get older.</p>
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
              <div className="field">
                <span className="label">My premium</span>
                <Segmented
                  label="Premium"
                  value={ptype}
                  onChange={setPtype}
                  options={[
                    { id: "level", label: "Same for life" },
                    { id: "age-rated", label: "Rises with age" },
                  ]}
                />
              </div>
            </div>
            <div className="quote-result" aria-live="polite">
              <span className="line">You pay each month{ptype === "age-rated" ? ", this year" : ""}</span>
              <span className="big">{cents(premium)}</span>
              <span className="line">
                Your family receives <b>{randFull(sum)}</b>
              </span>
              <span className="line" style={{ marginTop: 8 }}>
                <b>{cents((1 - MARGIN) * rate.per_rand * sum)}</b> pays for the cover, <b>{cents((1 - MARGIN) * rate.fixed)}</b> for running the policy, and{" "}
                <b>{cents(MARGIN * premium)}</b> is the {pct(MARGIN, 0)} margin.
              </span>
              {ptype === "age-rated" && (
                <span className="line">
                  Each year is priced on its own, so the premium rises with age
                  {later.length > 0 && <>: {later.map((x, i) => <span key={x.age}>{i ? ", " : ""}<b>{cents(x.premium)}</b> at {x.age}</span>)}</>}. Every{" "}
                  {book.review.every} years the company may reprice the schedule for all age-rated customers together, with no health check and no cap.
                </span>
              )}
              {ptype === "level" && <span className="line">The premium is set when you join and never changes.</span>}
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
          possible futures; the bar is the middle 95% of them. Women live longer, so their pensions cost more. Men's and women's prices both use
          the {PRICED_ON.Male}. Three later revisions were tested and none passed, so it prices both, and its ranges are lower bounds. Of the versions tested, v1 for both sexes is the only one that passes the plausibility gate, applied to both sexes together: women's pensions cost more than men's, and life expectancy at 65 rises for both.
        </p>
        <LowerBound />
        <div className="callout">
          <strong>What a real quote would add</strong>
          These pension prices cover the income alone, with no loading for costs, commission or profit, and no health check. That is also why the
          company's profit from insurance is small: almost all of it comes from investment return. The funeral premiums do include running costs (R
          {Math.round(book.expense / 12)} a month) and a {pct(book.margin, 0)} margin. They are priced on Stats SA registered deaths up to 2024, with
          death rates that keep improving: HIV-related, external and other causes each follow their own trend, fitted on 2012 to 2024 without the Covid
          years. Registration may be incomplete, which would make these premiums too cheap.
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
  return <BarChart label={label} groups={groups} fmt={(x) => thousands(Math.round(x))} height={220} />;
}

export function Customers({ r }: { r: Research }) {
  const v = r.v7!;
  const b = v.book;
  const a = b.annuities, f = b.funeral;
  const rising = (a.types["inflation-linked"] ?? 0) / a.n;
  const women = (f.sexes.Female ?? 0) / f.n;
  const rated = (f.types["age-rated"] ?? 0) / f.n;
  const ago = (n: number) => (n === 0 ? "this year" : n === 1 ? "a year ago" : `${n} years ago`);
  const onePct = (x: number) => randM(0.01 * Math.abs(x), 1);
  return (
    <>
      <PageHead kicker="The customers" title="Who the company covers">
        {thousands(Math.round(a.n))} pensioners and {thousands(Math.round(f.n))} funeral policyholders, all invented. I drew {thousands(b.drawn.annuities)}{" "}
        pensioners and {thousands(b.drawn.funeral)} funeral policies at random, from a fixed seed in{" "}
        <a href={`${REPO}/blob/main/research/book_v3.py`} target="_blank" rel="noreferrer">
          book_v3.py
        </a>
        : pensions bought at 55 to 75 with incomes spread around R60,000 a year, and funeral policies taken out at around 38 for R10,000 to R30,000 of cover,
        half of them on premiums that rise with age. The shapes are my choices, not taken from any insurer's data. The size of each line is not: it is set by the two
        rules below, so each drawn pensioner counts as {num(b.weights.annuities, 2)} of one and each drawn funeral policy as {num(b.weights.funeral, 2)}.
      </PageHead>

      <section className="panel">
        <h2 className="serif">How big each line is, and why</h2>
        <p className="note">
          <strong>The mix.</strong> Pensions and funeral cover are bets on death rates in opposite directions. If people die sooner than expected, the pensions
          cost less and the funeral claims more. I sized the funeral line so that the two cancel: if every death rate in both books were 1% higher, the pensions
          would cost {onePct(v.scales.annuities * v.exposures.annuities)} less and the funeral claims {onePct(v.scales.funeral * v.exposures.funeral)} more. That
          takes {num(v.mix, 1)} times as much of the drawn funeral book as of the drawn pensions, or {Math.round(v.policies.funeral / v.policies.annuitants)}{" "}
          funeral policies to each pensioner.
        </p>
        <p className="note">
          <strong>The size.</strong> With that mix held, I scaled the whole book until solvency cover on {randM(v.main.own_funds)} of capital was{" "}
          {coverPct(v.main.cover)}, the median for South African life insurers in 2025 (SARB, <i>Financial Stability Review</i>, 2026). With every funeral
          premium level, as in the previous version, the same two rules gave {thousands(v.v6.policies.annuitants)} pensioners and{" "}
          {thousands(v.v6.policies.funeral)} funeral policies.
        </p>
        <p className="note caveat">
          The offset holds for a mistake in the level of death rates, not in their trend. Improvement that runs 1 point a year faster than assumed changes the
          pensions by {randM(v.trend.annuities, 1)} and the funeral line by {randM(v.trend.funeral, 1)}, so {randM(v.trend.total, 1)} is left over. The
          regulator's formula treats the two risks as separate, and recognises only part of the offset: see the Capital page.
        </p>
      </section>

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
              <div className="value">{pct(rated, 0)}</div>
              <div className="sub">
                pay premiums that rise with age; median {cents(f.median_premium["age-rated"])} a month this year, against {cents(f.median_premium.level)} for a
                level premium
              </div>
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
        <p className="sub">The first drawn policies of each kind.</p>
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
                  {randFull(p.sum_assured)} <small>cover for {cents(p.premium)} a month, {TYPE_LABEL[p.premium_type]} premium</small>
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
          straight-line guide to the future. The pensions are priced on the original mortality model (v1); funeral cover on its own table, from deaths to 2024.
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
  const v = r.v7!;
  const m = v.main;
  const [curve, setCurve] = useState<"real" | "nominal">("real");
  const kinds = [
    ["real", "Inflation-linked", "var(--s1)"],
    ["nominal", "Fixed-rate", "var(--s2)"],
  ] as const;
  const holdings: Bar[] = [
    ...kinds.flatMap(([kind, note, color]) =>
      Object.entries(m.holdings[kind] ?? {}).map(([bond, x]) => ({ key: bond, name: bond, note, value: x, label: randM(x, 1), color })),
    ),
    { key: "bill", name: "Treasury bill", note: "182 days, cash", value: m.assets.bill, label: randM(m.assets.bill, 1), color: "#8a968f" },
    { key: "credit", name: "Premiums due and bank cash", note: "Owed by collectors, and held at a bank", value: m.assets.credit, label: randM(m.assets.credit, 1), color: "#5f6f68" },
  ].sort((a, b) => b.value - a.value);
  const bonds = holdings.filter((x) => x.key !== "bill" && x.key !== "credit");
  const c = m.credit, sov = m.sovereign;
  const L = m.dv01.liability, P = m.dv01.portfolio;
  const groups: BarGroup[] = KEYS.map((t) => ({
    key: t,
    label: `${t} years`,
    values: [
      { key: "l", label: "What is owed, both lines", color: "var(--s1)", value: L[`${curve} ${t}`] / 1e3 },
      { key: "p", label: "The bonds held", color: "var(--s3)", value: P[`${curve} ${t}`] / 1e3 },
    ],
  }));
  const short = KEYS.filter((t) => L[`nominal ${t}`] < 0);
  const bondNames = bonds.map((x) => `${(x.note ?? "").toLowerCase()} ${x.name}`).join(" and ");
  return (
    <>
      <PageHead kicker="Investments" title="Where the money is">
        The money is in South African government bonds and a Treasury bill. The bonds are chosen so their value moves in step with what the company owes, the
        pensions and the funeral business together.
      </PageHead>

      <section className="card">
        <h3>What the company holds today</h3>
        <p>
          {randM(m.assets.total)} in all. {bonds.length === 1 ? `One bond, the ${bondNames}, covers` : `${bonds.length} bonds cover`} the{" "}
          {randM(m.assets.matched, 1)} owed to customers. {randM(c.receivable, 1)} is a month of premiums that collectors have taken and not yet paid over, and{" "}
          {randM(c.cash, 1)} is cash at a bank, three months of what goes out. The rest, {randM(m.assets.bill)}, is in the bill.
        </p>
        <HBars rows={holdings} />
        <p className="note">
          The collectors and the bank could fail. The regulator's formula charges {pct(0.15, 0)} of the premiums due and, for a bank of middling credit quality,{" "}
          {pct(c.factor, 2)} of the cash: {randM(c.default, 1)} in all, which barely moves cover. Across every credit quality the formula knows, from the best
          to the worst, cover stays between {pct(Math.min(...Object.values(c.by_step)), 2)} and {pct(Math.max(...Object.values(c.by_step)), 2)}.
        </p>
        <p className="note caveat">
          The real exposure is the other borrower. {randM(sov.government_assets)} is lent to the South African government, and the formula charges nothing for
          that. If those bonds and bills lost {pct(sov.cover_one, 0)} of their value, cover would fall to 100%; at {pct(sov.own_funds_zero, 0)} the capital
          would be gone. What is owed to customers would not fall with them. This test is mine, outside the formula.
        </p>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">Matching the whole book, point by point on the curve</h2>
            <p className="eyebrow">
              Value lost if {curve === "real" ? "inflation-linked" : "fixed-rate"} yields rise by 0.01% at one point on the curve, R thousand
            </p>
          </div>
          <Segmented
            label="Curve"
            value={curve}
            onChange={setCurve}
            options={[
              { id: "real", label: "Inflation-linked" },
              { id: "nominal", label: "Fixed-rate" },
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
        <BarChart
          label={`Sensitivity of what is owed and of the bonds held to a 0.01% rise in ${curve === "real" ? "inflation-linked" : "fixed-rate"} yields at 5, 10, 20 and 30 years, R thousand`}
          groups={groups}
          fmt={(x) => `R${num(x, 0)}k`}
          height={260}
        />
        <p className="note">
          When interest rates rise, what the company owes on the pensions falls, and so does the value of the funeral business's future profits. The two pull in
          opposite directions, so much of the risk cancels before any bond is bought. What is left is mostly on the inflation-linked curve, where the bonds are
          held. I chose them by least squares: non-negative holdings worth exactly what is owed, as close as possible to its sensitivity at 5, 10, 20 and 30
          years on both curves at once.
        </p>
        <p className="note">
          On the fixed-rate curve, what is owed{" "}
          {short.length ? (
            <>
              goes up when yields rise at {short.join(" and ")} years (R{num(-L[`nominal ${short[short.length - 1]}`] / 1e3, 0)}k at{" "}
              {short[short.length - 1]} years): the funeral profits, discounted at fixed rates, dominate. Matching that would mean borrowing bonds and selling
              them, which the company does not do, so it is left open. That is why the fixed-rate charge on the Capital page is {randM(m.interest.nominal)}.
            </>
          ) : (
            "is matched with fixed-rate bonds."
          )}
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
  const v = r.v7!;
  const m = v.main;
  const floor = v.projection?.capital?.levels.find((x) => x.cover < 1.5);
  const spike = (k: string) => v.lapse_spike[k];
  const loss = (a: string, b: string) => Math.max(m.rate_losses[a] ?? 0, m.rate_losses[b] ?? 0);
  const realWorst = (m.rate_losses["real down"] ?? 0) >= (m.rate_losses["real up"] ?? 0) ? "fall" : "rise";
  const nomWorst = (m.rate_losses["nominal up"] ?? 0) >= (m.rate_losses["nominal down"] ?? 0) ? "rise" : "fall";
  const stress: Bar[] = [
    { key: "lon", name: "Pensioners live longer", note: "The regulator's test: pensioners' death rates 10% lower, and improving 1 point a year faster", value: m.life.longevity, label: randM(m.life.longevity, 1), color: "var(--s1)" },
    { key: "real", name: `Inflation-linked yields ${realWorst}`, note: "By about half to three quarters", value: loss("real down", "real up"), label: randM(loss("real down", "real up"), 1), color: "var(--s1)" },
    { key: "nom", name: `Fixed-rate yields ${nomWorst}`, note: "By 30% to 50% at most terms", value: loss("nominal up", "nominal down"), label: randM(loss("nominal up", "nominal down"), 1), color: "var(--s1)" },
    { key: "exp", name: "Costs rise", note: "Running costs 10% up, inflation 2 points up", value: m.life.expense, label: randM(m.life.expense, 1), color: "var(--s1)" },
    { key: "lapse", name: "Customers leave", note: "40% of funeral policies cancelled at once", value: m.life.lapse, label: randM(m.life.lapse, 1), color: "var(--s1)" },
    { key: "op", name: "Something breaks", note: "Systems, people or fraud", value: m.op, label: randM(m.op, 1), color: "var(--s1)" },
    { key: "mort", name: "More funeral claims", note: "Death rates 15% higher", value: m.life.mortality, label: randM(m.life.mortality, 1), color: "var(--s1)" },
    { key: "cat", name: "A pandemic", note: "A spike in deaths over three months", value: m.life.catastrophe, label: randM(m.life.catastrophe, 1), color: "var(--s1)" },
    { key: "def", name: "A collector or the bank fails", note: "15% of a month's premiums due, and 4.35% of the bank cash", value: m.credit.default, label: randM(m.credit.default, 1), color: "var(--s1)" },
  ].sort((a, b) => b.value - a.value);
  const sum = stress.reduce((a, x) => a + x.value, 0);
  const { mortality: mo, longevity: lo } = m.life;
  const pair = Math.sqrt(mo * mo + lo * lo - 2 * 0.25 * mo * lo);
  const lapseRows = [
    { k: "0.00", label: "No extra lapses in review years" },
    { k: "main", label: `${pct(v.book.review.lapse_spike, 0)} more of age-rated customers leave in each review year (used)` },
    { k: "0.20", label: "20% more leave" },
  ];
  return (
    <>
      <PageHead kicker="Capital" title="Is there enough capital?">
        The Prudential Authority asks every insurer to hold enough capital to survive a 1-in-200 year: the solvency capital requirement. Solvency cover is the
        capital held divided by that requirement, and it has to be at least 100%. The pensions are valued on the original mortality model (v1); funeral claims on
        the funeral table from deaths to 2024, improving.
      </PageHead>

      <div className="grid three">
        <Stat label="Solvency cover today" value={coverPct(m.cover)} good={m.cover >= 1}>
          <Pill kind="good">The industry median, by design</Pill>
        </Stat>
        <Stat label="Capital required" value={randM(m.scr, 1)} sub="To survive a 1-in-200 year" />
        <Stat
          label="Capital held"
          value={randM(m.own_funds)}
          sub={floor ? `${randM(floor.own_funds, 1)} would give exactly 100%; the Next five years page runs both` : "The book is sized to it"}
        />
      </div>
      <p className="note">
        Cover is {coverPct(m.cover)} because I sized the book to make it so, not because the company earned it: the Customers page explains the rule. With
        every funeral premium level (v6), the same rule gave a smaller funeral book, {thousands(v.v6.policies.funeral)} policies against {thousands(v.policies.funeral)}.
      </p>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="serif">Premiums that rise with age</h2>
            <p className="eyebrow">Half the funeral customers pay a premium priced year by year, which the company may review every {v.book.review.every} years</p>
          </div>
        </div>
        <p className="note">
          The level policies are expected to earn {randM(-m.bel_by_type.level)} over their lifetime and the age-rated ones {randM(-m.bel_by_type["age-rated"])}.
          An age-rated premium is cheap while the customer is young and dear later, so its profit comes later, and depends more on the customer staying.
        </p>
        <p className="note">
          <strong>The review.</strong> Because the company can reprice all age-rated customers together, without a health check, the regulator still treats
          them as long-term policies. If the review were allowed to soften the 15% mortality stress (repricing on the higher death rates from the next review
          on), the charge for more funeral deaths would fall from {randM(m.life.mortality, 1)} to {randM(v.review.life.mortality, 1)}, and cover would rise to{" "}
          {pct(v.review.cover, 1)}. I report that and do not use it: the regulator's text does not say a review may be assumed inside the stress.
        </p>
        <p className="note">
          <strong>Leaving at review time.</strong> I assume {pct(v.book.review.lapse_spike, 0)} more of age-rated customers cancel in each review year, on top of
          the usual rates. The assumption is mine, not fitted.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Extra cancellations in review years</th>
                <th className="num">Owed</th>
                <th className="num">Required</th>
                <th className="num">Cover</th>
              </tr>
            </thead>
            <tbody>
              {lapseRows.map(({ k, label }) => {
                const x = k === "main" ? { bel: m.bel, scr: m.scr, cover: m.cover } : spike(k);
                return x ? (
                  <tr key={k} className={k === "main" ? "total" : undefined}>
                    <td>{label}</td>
                    <td className="num">{x.bel ? randM(x.bel.total, 1) : ""}</td>
                    <td className="num">{randM(x.scr, 1)}</td>
                    <td className="num">{coverPct(x.cover)}</td>
                  </tr>
                ) : null;
              })}
            </tbody>
          </table>
        </div>
        <p className="note">
          These rows hold the book's size, so they show the assumption alone. Cover rises with more review-year cancellations, not falls. I have not split out why;
          the rows are reported as measured.
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
          requirement of {randM(m.scr, 1)}. The largest single loss is a rise in fixed-rate yields, on the funeral profits the company holds no bonds against.
          Among the insurance risks, costs now come first, because the funeral line's running costs stretch decades ahead, with customers leaving close behind:
          the funeral policies are expected to earn {randM(-m.bel.funeral)}, and a 40% wave of cancellations would lose that share of it. Default by the
          collectors or the bank is the smallest charge on the list.
        </p>
        <p className="note">
          The mix offsets a mistake in death rates, but the regulator's formula tests the two directions separately: funeral deaths 15% higher, and pensioners'
          10% lower and improving faster, each with the other book held. It allows only for a correlation of −0.25 between them, so it counts the two together as {randM(pair, 1)},
          not the near-zero the mix gives for a change in both at once. So the offset the book was built on shows up only in part in its capital.
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
                <td className="num">{(m.scr / 1e6).toFixed(1)}</td>
              </tr>
            </tbody>
          </table>
        </TableView>
      </section>

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
              <th>Death rates</th>
              <th className="num">Owed</th>
              <th className="num">Required</th>
              <th className="num">Cover</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ adj, s }) => (
              <tr key={adj}>
                <td>
                  {pct(adj, 0)}
                  {adj === 0.7 ? " (used)" : ""}
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

const SET_LABEL: Record<string, string> = {
  covid: "COVID years left out of the rate model",
  no_rematch: "Bonds bought once and never rebalanced",
  frozen: "The frozen three-factor rate model",
};

/** v7's empty whole-book matches, found after the projection ran, and the read-only replays that measured them. */
function EmptyMatch({ v }: { v: NonNullable<Research["v7"]> }) {
  const e = v.empty_match;
  const split = e.split ? Object.entries(e.split) : null;
  return (
    <li style={{ gridColumn: "1 / -1" }}>
      <strong>Empty bond matches in the frozen rate model's futures (v7), found after seeing; addendum dated 28 Oct 2026</strong>
      <p>
        The projection's log shows {thousands(e.logged)} year-ends outside the main set where the whole-book match bought no bonds, so the company held only the
        bill for the next year. The main set ({e.main ? `replayed: ${e.main.year_ends_empty === 0 ? "none" : e.main.year_ends_empty} in ${thousands(e.main.paths)} paths` : "none"}) and
        the capital run have none.{" "}
        {split ? (
          <>
            A read-only replay (<a href={doc("diag_v7_split.py")} target="_blank" rel="noreferrer"><code>research/diag_v7_split.py</code></a>) puts them by set:{" "}
            {split
              .map(([k, x]) => `${SET_LABEL[k] ?? k}, ${x.year_ends_empty ? `${thousands(x.year_ends_empty)} in ${thousands(x.paths_with_empty_match)} of ${thousands(x.paths)} paths` : "none"}`)
              .join("; ")}
            . Each set's share covered reproduces the published one.
            {split.filter(([, x]) => x.bel_m).map(([k, x]) => (
              <span key={k}>
                {" "}At every one, what the whole book owed was below zero (median {randM(x.bel_m!.median * 1e6)}): the funeral line's expected profit outweighed the
                pensions, and no holding without borrowing can match a negative amount. So this is the matching rule's own answer, not a hedge thrown away.
              </span>
            ))}
          </>
        ) : (
          <>The split by set was not measured.</>
        )}
      </p>
      <p>
        <em>Direction.</em> Own funds at those year-ends are not affected: the assets are valued as held. The interest-rate charge is that of an unhedged book,
        which no long-only holding could have matched; against a company allowed to borrow bonds, cover there is understated. The next year earns the bill's
        return instead of the bonds', which lowers own funds if rates fall and raises them if they rise, so that year's direction depends on the path. Read the
        frozen model's share covered with this in mind; the main set, the other two sets and the capital level are unaffected.
      </p>
      <p>
        No code, cutoff or result was changed. The replays (<a href={doc("diag_v7.py")} target="_blank" rel="noreferrer"><code>research/diag_v7.py</code></a>
        {split ? " and the split" : ""}) only count.
      </p>
    </li>
  );
}

export function Built({ r }: { r: Research }) {
  const t = r.backtest.tests;
  const v2 = r.v2, v3 = r.v3;
  const cross = crossing(r);
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
  const v6 = r.v6, v7 = r.v7, p6 = v7?.projection;
  if (v7) {
    const k = v7.checks;
    checks.push(
      { claim: "The age-rated valuation is right", plain: "A month-by-month loop over one age-rated policy, with its review-year cancellations, agrees with the engine to a hundred-millionth, unstressed and under every stress.", verdicts: <Verdict pass={k.F1.pass} />, code: true },
      { claim: "No extra cancellations, no difference", plain: "With the review-year spike set to 0, an age-rated policy cancels exactly as a level one does.", verdicts: <Verdict pass={k.F3.pass} />, code: true },
      { claim: "The default charge is the regulator's arithmetic", plain: "15% of the premiums due plus 4.35% of the bank cash, exactly; with both set to 0, the requirement is the run without them.", verdicts: <Verdict pass={k.F5.pass} />, code: true },
      { claim: "The pensions are unchanged", plain: "What is owed to pensioners and their longevity charge are v3's scaled by the book's size, to a hundred-millionth.", verdicts: <Verdict pass={k.F6.pass} />, code: true },
      { claim: "The mix is mortality-neutral", plain: "A 1% change in every death rate, both books at once, moves what is owed by less than a billionth of the pensions' change.", verdicts: <Verdict pass={k.D1.pass} />, code: true },
      { claim: "The size gives cover of 1.8", plain: "Solved to within a millionth.", verdicts: <Verdict pass={k.D2.pass} />, code: true },
      { claim: "The bonds are worth what is owed, none borrowed", plain: "The whole-book match holds no negative position and is worth what is owed to customers, to one part in a hundred million.", verdicts: <Verdict pass={k.D5.pass} />, code: true },
    );
  }
  if (p6) {
    const a2 = Object.values(p6.checks.A2);
    checks.push(
      {
        claim: "The projection adds up",
        plain: "Each year's cash flows and the roll-forward of the accounts reconcile with the valuations at either end, to rounding.",
        verdicts: <Verdict pass={p6.checks.R1.pass && p6.checks.R2.pass} />,
        code: true,
      },
      {
        claim: "Simulated rates move like real ones",
        plain: `A year's change in the 10-year yield across the futures is within a third of its spread since 2011. Fixed-rate passes at ${num(p6.checks.E1.nominal.ratio, 2)} against a limit of 1.33, only just. The model as first written failed this for inflation-linked bonds; the change was committed before anything was projected.`,
        verdicts: (["real", "nominal"] as const).map((k) => <Verdict key={k} pass={p6.checks.E1[k].pass} who={k === "real" ? "Inflation-linked" : "Fixed-rate"} />),
      },
      {
        claim: "Cover stays above 100% in 95% of futures",
        plain: `It does in ${pct(p6.checks.A1.share_covered, 1)}, on ${randM(p6.central[0].own_funds)} of capital. At exactly 100% to start it does in ${pct(p6.capital?.levels[0].share_covered ?? 0, 1)}, which is reported, not tested.`,
        verdicts: <Verdict pass={p6.checks.A1.pass} />,
      },
      {
        claim: "Cover stays above 100% under each disaster",
        plain: `${a2.filter(Boolean).length} of ${a2.length} pass. See the next five years.`,
        verdicts: <Verdict pass={a2.every(Boolean)} />,
      },
    );
  }
  // The earlier book, of drawn counts: kept as the record of how the size was reached.
  const history: { claim: string; plain: string; verdicts: ReactNode }[] = [];
  if (v3) {
    history.push(
      {
        claim: "Matching cuts the interest-rate charge below a quarter (v3)",
        plain: `The first portfolio cut it from ${randM(v3.unmatched.market)} with everything in cash to ${randM(v3.main.market)}.`,
        verdicts: <Verdict pass={v3.checks.K3.pass} />,
      },
      { claim: "Longevity is the largest risk (v3)", plain: "On a book of 5,000 pensioners and 50,000 funeral policies it could hardly come out otherwise.", verdicts: <Verdict pass={v3.checks.K4.pass} /> },
    );
    if (v3.key_rate)
      history.push({ claim: "Rebalancing beats the first portfolio (v3)", plain: "Added after the first result was seen, and written down before it was run.", verdicts: <Verdict pass={v3.key_rate.checks.K6.pass} /> });
  }
  if (v6?.projection) {
    const a2 = Object.values(v6.projection.checks.A2);
    history.push(
      { claim: "Cover stays above 100% in 95% of futures (v6)", plain: `It did in ${pct(v6.projection.checks.A1.share_covered, 1)}.`, verdicts: <Verdict pass={v6.projection.checks.A1.pass} /> },
      { claim: "Cover stays above 100% under each disaster (v6)", plain: `${a2.filter(Boolean).length} of ${a2.length} passed.`, verdicts: <Verdict pass={a2.every(Boolean)} /> },
    );
  }
  if (r.v4) {
    const a2 = Object.values(r.v4.checks.A2);
    history.push(
      { claim: "Cover stays above 100% in 95% of futures (v4)", plain: `It did in ${pct(r.v4.checks.A1.share_covered, 1)}.`, verdicts: <Verdict pass={r.v4.checks.A1.pass} /> },
      { claim: "Cover stays above 100% under each disaster (v4)", plain: `${a2.filter(Boolean).length} of ${a2.length} passed.`, verdicts: <Verdict pass={a2.every(Boolean)} /> },
    );
  }
  return (
    <>
      <PageHead kicker="Methods" title="Methods and limitations">
        I built this in seven parts. For each, I wrote down the method, the tests and the pass marks, and committed them before running anything. Later changes
        are dated and committed before the run they affect, or marked as made after seeing a result. Each card links the commit it was frozen at.
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
          <p>Four mortality models backtested on Stats SA registered deaths, 1997 to 2022. The winner, v1, prices the pensions, with ranges from 5,000 simulated futures.</p>
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
          <p>The Prudential Authority's standard formula for solvency (SAM), applied to an invented book of pensions and funeral policies, first on drawn counts.</p>
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
        <div className="card">
          <div className="icon-badge" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19h16M6 19V9l6-5 6 5v10" />
              <path d="M10 19v-5h4v5" />
            </svg>
          </div>
          <h3>Funeral cover on its own table</h3>
          <p>Funeral death rates from Stats SA deaths to 2024, improving by cause, and a funeral benefit that can rise with inflation, capped at 6% a year.</p>
          <p>
            <a href={doc("PROTOCOL_v5.md")} target="_blank" rel="noreferrer">
              Plan
            </a>{" "}
            ·{" "}
            <a href={doc("results/balance_v5.json")} target="_blank" rel="noreferrer">
              Results
            </a>{" "}
            · <Frozen hash="5039d84c999a" when="27 Oct 2026, 09:39" />
          </p>
        </div>
        <div className="card">
          <div className="icon-badge" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3v18M5 7h14M5 7l-3 7h6zM19 7l-3 7h6z" />
            </svg>
          </div>
          <h3>Sizing the book by rule</h3>
          <p>The funeral line sized so a mistake in death rates cancels between the two lines, the whole book sized to the industry's median cover, and matched together.</p>
          <p>
            <a href={doc("PROTOCOL_v6.md")} target="_blank" rel="noreferrer">
              Plan
            </a>{" "}
            ·{" "}
            <a href={doc("results/mix_v6.json")} target="_blank" rel="noreferrer">
              Results
            </a>{" "}
            · <Frozen hash="9e59992c5521" when="27 Oct 2026, 14:15" />
          </p>
        </div>
        <div className="card">
          <div className="icon-badge" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 20l5-6 4 3 7-9" />
              <path d="M4 4v16h16" />
            </svg>
          </div>
          <h3>A premium that rises with age, and credit risk</h3>
          <p>Funeral customers choose a level premium or one priced year by year and reviewable every five years. The regulator's default charge, and a sovereign stress outside it.</p>
          <p>
            <a href={doc("PROTOCOL_v7.md")} target="_blank" rel="noreferrer">
              Plan
            </a>{" "}
            ·{" "}
            <a href={doc("results/balance_v7.json")} target="_blank" rel="noreferrer">
              Results
            </a>{" "}
            · <Frozen hash="3fa2f70e7ae9" when="28 Oct 2026, 11:22" />
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
        <h2>How the book got its size</h2>
        <p className="sub">The earlier versions, kept as they ran. Their results are on the drawn counts, not the book the rest of the site shows.</p>
        <div className="card">
          <ul className="method">
            {v3 && (
              <li>
                <strong>Drawn counts (v3)</strong>
                I first drew {thousands(v3.book?.annuities.n ?? 5000)} pensioners and {thousands(v3.book?.funeral.n ?? 50000)} funeral policies, counts with
                nothing behind them. On {randM(v3.main.own_funds)} of capital, the first portfolio gave cover of {coverPct(v3.main.cover)}
                {v3.key_rate ? `, and rebalancing across 5 to 30 years ${coverPct(v3.key_rate.cover)}` : ""}. Longevity was the largest risk by far.
              </li>
            )}
            {r.v4 && (
              <li>
                <strong>Five years ahead on drawn counts (v4)</strong>
                {pct(r.v4.scenarios.A1.share_covered, 1)} of futures stayed covered every year, short of the 95% target. The exploratory capital levels put the
                crossing between {cross ? `${randM(cross.lo.own_funds)} and ${randM(cross.hi.own_funds)}` : "levels above those run"}, with the extra capital
                spread over every asset.
              </li>
            )}
            {v6 && (
              <li>
                <strong>The funeral table (v5)</strong>
                Repricing the funeral line on its own improving table, with a benefit that can rise, nearly doubled its expected profit (what it owes went from{" "}
                {randM(v3?.main.bel.funeral ?? 0)} to {randM(v6.v5.bel.funeral)}). On the drawn counts the SCR was {randM(v6.v5.scr)} against {randM(v6.v5.own_funds)}{" "}
                of capital, cover {coverPct(v6.v5.cover)}. A result that rested on counts with nothing behind them is why the size was then set by rule.
              </li>
            )}
            {v6 && (
              <li>
                <strong>Size by rule (v6)</strong>
                The mix sets {num(v6.mix, 1)} units of the drawn funeral book per unit of the drawn pensions, and the size sets {num(v6.scales.annuities, 3)} of
                the drawn pensions: {thousands(v6.policies.annuitants)} pensioners and {thousands(v6.policies.funeral)} funeral policies. Every drawn policy keeps
                its age, sex, amount and premium; only its weight changed. Cover stayed above 100% in{" "}
                {pct(v6.projection?.checks.A1.share_covered ?? 0, 1)} of futures, and at the minimum capital in{" "}
                {pct(v6.projection?.capital?.levels[0].share_covered ?? 0, 1)}.
              </li>
            )}
            {v7 && v6 && (
              <li>
                <strong>A choice of premium (v7)</strong>
                The rising benefit was dropped and half the funeral customers given an age-rated premium. The same two rules then set{" "}
                {thousands(v7.policies.annuitants)} pensioners and {thousands(v7.policies.funeral)} funeral policies, against v6's{" "}
                {thousands(v6.policies.annuitants)} and {thousands(v6.policies.funeral)}. This is the book the rest of the site shows.
              </li>
            )}
          </ul>
        </div>
        {history.length > 0 && (
          <div className="card" style={{ marginTop: 14 }}>
            <ul className="checks">
              {history.map((c) => (
                <li key={c.claim}>
                  <strong>{c.claim}</strong>
                  <span className="verdicts">{c.verdicts}</span>
                  <p>{c.plain}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="section">
        <h2>Changes after freezing</h2>
        <div className="card">
          <ul className="method">
            {v7 && <EmptyMatch v={v7} />}
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
              <strong>The cover 1.0 level (v6), after seeing the first run</strong>
              The first solve for own funds stopped at cover 0.99999999991, a hair under 100%, so every future counted as below it at the start and the share
              covered read 0. The solve was changed to step up to at least 100% at <Commit hash="28b6a26" when="27 Oct, 20:04" />, and rerun; nothing else
              changed.
            </li>
            <li>
              <strong>Mortality revisions (v1.1 to v1.3), none adopted</strong>
              Three revisions, each planned and frozen before it ran: completeness scaling, overdispersion and an average of models (v1.1); windows by sex
              (v1.2); a cohort term smoothed over birth years (v1.3, <Frozen hash="e4e524b44d96" when="26 Oct 2026" />). The 2017 to 2019 hold-out guided all
              three, so v1.3 added a second backtest origin. None passed both its tests and a check that women's pensions cost more than men's and that life
              expectancy rises. v1.3's smoothing removed the heaping spikes and the jump-off (the step in life expectancy at 65 from 2019 to 2020, with the period trend held,
              fell from 0.17 years to 0.00 for men and from 0.25 to 0.04 for women), but it cost most of the in-sample fit: deviance rose from 811 to 3,812 for men and
              from 2,344 to 20,201 for women. Targeted interpolation of the round-year cohorts is untried, and left as future work. v1.3 was the last. Both
              sexes stay on v1.{" "}
              <a href={doc("RESULTS_v1.3.md")} target="_blank" rel="noreferrer">
                Results
              </a>
            </li>
            <li>
              <strong>Starting capital (v4), exploratory</strong>
              Added after seeing the first result. The levels and the rule for investing the extra were written at <Commit hash="28e4b67" when="14:51" />,
              before any level was run. After R600m to R1,000m had run, I stopped at R500m rather than narrowing to the nearest R25m, and report the crossing
              as an interval (<Commit hash="55fbcb9" when="16:15" />, before the R500m result). Every level used the same 1,000 futures, regenerated from
              the same seed on the same calibration, and the same five disasters. {cross &&
                `${randM(cross.lo.own_funds)} kept ${pct(cross.lo.share_covered, 1)} of futures covered and ${randM(cross.hi.own_funds)} ${pct(cross.hi.share_covered, 1)}, so the crossing is reported as lying between them. The rule at 55fbcb9 named R627m, the industry-typical cover, as the upper point; once every result was in, I report ${randM(cross.hi.own_funds)} instead, as the lowest completed run above 95%, and keep R627m as a reference point. `}
              Like every capital result on this site, it is final, on the v1
              mortality model.
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
              Seeded random draws, in shapes I chose. The size and mix are set by rule, so they are consistent, but a real book would differ in ages, sizes and
              mix.
            </li>
            <li>
              <strong>The pensioners' death rates are assumed</strong>
              70% of the population's, a round number, not fitted to South African pensioners. The balance sheet history below shows how much it mattered on the
              drawn counts.
            </li>
            <li>
              <strong>Ranges are too narrow</strong>
              The mortality forecast's 95% ranges caught fewer outcomes than they should have, for both sexes. Read every range here as a lower bound.
            </li>
            <li>
              <strong>Birth years on death records are heaped</strong>
              Deaths of people born in a year ending in 0 run about 10% (men) and 14% (women) above the neighbouring years, and 15% and 22% for 1930. Years ending in 5 are not
              heaped, and neither are ages. In 2021 to 2023, where the date of birth is recorded, 1.9% of the dates are 1 January, seven times what chance
              would give, so unknown dates of birth are probably filled in with round years. The cohort term of one model reads this as real differences between
              generations. Checked on 26 October 2026, in <code>research/heaping.py</code>. A targeted fix, treating the round-year cohorts as missing and
              interpolating across them, was considered and not used: the five-year smoothing of the cohort term had been approved before the check, and a
              test on simulated heaped data covers whether it damps the spikes.
            </li>
            <li>
              <strong>Short windows give unstable projections</strong>
              The bootstrap projections in the v1.4 study are unstable when fitted on very short windows: from a few years of data, many paths reach death rates
              above 1. These are reported as they stand, and nothing was tuned to remove them.
            </li>
            <li>
              <strong>The backtests flatter the models</strong>
              Each holdout period was short and was also used to choose between models, so the scores are likely better than out-of-sample performance would be.
            </li>
            <li>
              <strong>Fixed-rate yields fit poorly</strong>
              The fixed-rate curve missed the 0.25% auction-yield target. It drives the level pensions and the funeral discounting, and so the open risk above.
            </li>
            <li>
              <strong>Funeral deaths may be under-registered</strong>
              The funeral table uses registered deaths over the UN's population with no completeness adjustment. If registration is incomplete, the funeral rates
              are too low and the premiums too cheap.
            </li>
            <li>
              <strong>The capital sees only part of the offset</strong>
              The mix cancels a mistake in the level of death rates, not in their trend, and the regulator's formula charges mortality and longevity
              separately.
            </li>
            <li>
              <strong>Fixed-rate risk left open</strong>
              The funeral profits' exposure to fixed-rate yields could only be matched by borrowing bonds to sell, which the company does not do.
            </li>
            <li>
              <strong>One borrower</strong>
              Almost every asset is South African government debt. The standard formula charges nothing for it, so the requirement does not either; the
              sovereign stress on the Investments page measures it outside the formula, as a single loss with no recovery.
            </li>
            <li>
              <strong>Default risk rests on my assumptions</strong>
              Half a month of premiums held by collectors, and a month of outgo in the bank at a credit quality step I chose. No collector or bank is named or
              rated.
            </li>
            <li>
              <strong>The review is simple</strong>
              Repricing is for the whole age-rated book at once, with no cap, and the regulator's stresses are not softened by it in the figures used. The 10%
              extra cancellations in review years is my assumption, not fitted.
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
          <Disclose title="History: balance sheet on the drawn counts (v3)" sub={`SAM standard formula, valuation date ${longDate(v3.valuation_date)}, 5,000 pensioners and 50,000 funeral policies`}>
            <Interest v={v3} />
            <BalanceSheet v={v3} />
            <AnnuitantSensitivity v={v3} />
          </Disclose>
        )}
      </section>

      <section className="section">
        <h2>Data and credits</h2>
        <div className="card">
          <ul className="method">
            <li>
              <strong>Deaths</strong>
              Statistics South Africa, Mortality and Causes of Death 1997 to 2024, unit records, distributed by DataFirst, University of Cape Town. The
              funeral table leaves out 2023, whose registered deaths are essentially missing.
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
              every simplification. The industry's median cover of 1.8: SARB, <i>Financial Stability Review</i>, 2026, Table B.2.
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
  const v = r.v7!.projection!;
  const v6p = r.v6?.projection;
  const em = r.v7!.empty_match;
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
  const [worstKey, worstStress] = Object.entries(v.stresses).sort((a, b) => Math.min(...a[1].cover) - Math.min(...b[1].cover))[0];
  const frozen3 = v.esg.frozen_three_factor;
  const m = (x: number[]) => x.map((y) => y / 1e6);
  return (
    <>
      <PageHead kicker="The next five years" title="Does the cover hold up?">
        A look five years ahead, of the kind the regulator asks every insurer for: a thousand possible paths for interest rates and inflation, and five named
        disasters, each run through the customers, the bonds and the capital, year by year. Age-rated funeral premiums move along their schedule each
        year, and the bonds are rematched to the whole book at every year-end. The pensions are valued on the original mortality model (v1) throughout.
      </PageHead>

      <div className="grid three">
        <Stat label="Solvency cover in five years" value={coverPct(c["50"][5])} sub={`In the middle future, from ${coverPct(c["50"][0])} today`} good={c["50"][5] >= 1} />
        <Stat label="Futures that stay above 100%" value={pct(s.A1.share_covered, 0)} sub="Every year for five years, against the 95% I set beforehand">
          {s.A1.pass ? <Pill kind="good">Meets the target</Pill> : <Pill kind="bad">Misses the target</Pill>}
        </Stat>
        <Stat
          label={`Lowest cover in a disaster: ${(STRESS[worstKey]?.name ?? worstKey).toLowerCase()}`}
          value={coverPct(Math.min(...worstStress.cover))}
          sub={
            worstStress.capital_to_restore > 0
              ? `It would take ${randM(worstStress.capital_to_restore)} of new capital to get back to 100%`
              : "No new capital needed to stay above 100%"
          }
          good={Math.min(...worstStress.cover) >= 1}
        >
          {failed.length ? <Pill kind="bad">{failed.length} of 5 disasters go below 100%</Pill> : <Pill kind="good">Every disaster stays above 100%</Pill>}
        </Stat>
      </div>

      {r.v7!.central_compare && v6p && <Compare r={r} />}

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
          more than the capital it ties up. Rates rarely do what is expected, but at {coverPct(c["50"][0])} the cushion is wide: cover dips below 100% at least
          once in {pct(below, 1)} of the futures, against a limit of 5%, and the 5th percentile never falls below {coverPct(Math.min(...c["5"]))}. The bonds
          match what is owed, not the risk margin and capital requirement the regulator adds on top, so a fall in rates still costs cover.{" "}
          {r.v4 && `On the earlier book of invented counts, at ${coverPct(r.v4.scenarios.cover["50"][0])} to start, ${pct(r.v4.scenarios.below_one_share, 0)} of futures dipped below.`}
        </p>
        <p className="note caveat">
          The rate model was fitted on 2011 to 2026 and judged on the same years, so these ranges are likely narrower than the real ones. With March to May 2020
          left out of the fit, {pct(v.sensitivities.covid_excluded.A1.share_covered, 1)} of futures stay covered rather than {pct(s.A1.share_covered, 1)}. On the
          three-factor rate model I first froze, which failed its own check for inflation-linked rates (it moves them{" "}
          {num(frozen3.checks.E1.real.ratio, 2)} times as much as history), only {pct(frozen3.cover.A1.share_covered, 1)} would: the answer depends on the rate
          model more than on anything else here. The frozen model's futures include {thousands(em.logged)} year-ends where the matching rule bought no bonds at
          all, because the whole book owed less than nothing; the main set has none. Methods explains what that does to its figure.
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
          {failed.length
            ? `${failed.length} of ${Object.keys(v.stresses).length} take cover below 100%.`
            : `None takes cover below 100% on ${randM(v.central[0].own_funds)} of capital.`}{" "}
          The worst is {(STRESS[worstKey]?.name ?? worstKey).toLowerCase()}, at {coverPct(Math.min(...worstStress.cover))}. Pensioners living 20% longer
          would cost {randM(v.stresses["S2 Longevity"].losses + v.stresses["S2 Longevity"].csm_used)}, a harsher test than the regulator's own longevity shock on
          the Capital page, which sets the capital requirement.{" "}
          {Math.min(...v.stresses["S4 Lapse wave"].cover) > v.central[0].cover &&
            "A wave of cancellations raises cover: the profit lost is smaller than the capital the regulator no longer asks for against those customers leaving."}
        </p>
        <div className="callout">
          <strong>What I would do next</strong>
          The futures move interest rates and inflation, not death rates or lapses, which enter only through the named disasters. Simulating those as well, and
          reinsuring part of the lapse and longevity risk, are not modelled here.
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

      {v.capital && v.capital.levels.length > 1 && <CapitalLevels c={v.capital} v6={v6p?.capital ?? null} />}

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

/** v7 against v6: the share of futures covered at the floor, and the central path year by year at R400 million. */
function Compare({ r }: { r: Research }) {
  const v7 = r.v7!, cc = v7.central_compare!;
  const lo7 = v7.projection!.capital!.levels[0], lo6 = r.v6!.projection!.capital!.levels[0];
  const y0 = Number(v7.valuation_date.slice(0, 4));
  const T = [1, 2, 3, 4, 5];
  const d = (x: number[], t: number) => x[t] - x[t - 1];
  const rows: { name: string; f: (c: (typeof cc)["v6"], t: number) => number; cover?: boolean }[] = [
    { name: "Change in own funds", f: (c, t) => d(c.own_funds, t) },
    { name: "IFRS 17 profit", f: (c, t) => c.profit[t - 1] },
    { name: "Funeral premiums less claims and costs", f: (c, t) => c.funeral_net[t - 1] },
    { name: "Capital required", f: (c, t) => c.scr[t] },
    { name: "of which fixed-rate charge", f: (c, t) => c.nominal[t] },
    { name: "Cover", f: (c, t) => c.cover[t], cover: true },
  ];
  const y1 = (c: (typeof cc)["v6"]) => Math.log(c.cover[1] / c.cover[0]);
  const ofShare = Math.log(cc.v7.own_funds[1] / cc.v6.own_funds[1]) / (y1(cc.v7) - y1(cc.v6));
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2 className="serif">The premium choice made the floor much less safe</h2>
          <p className="eyebrow">v7 against v6, both sized to cover 1.8 on R400 million</p>
        </div>
      </div>
      <div className="grid two">
        <Stat label="Futures covered throughout, at the floor" value={pct(lo7.share_covered, 1)} sub={`On ${randM(lo7.own_funds, 1)} of capital. v6: ${pct(lo6.share_covered, 1)} on ${randM(lo6.own_funds, 1)}`} good={false} />
        <Stat label="Cover after a year, rates as expected" value={coverPct(cc.v7.cover[1])} sub={`v6: ${coverPct(cc.v6.cover[1])}, both from 180%`} />
      </div>
      <p className="note">
        The capital at the floor is about the same, and the share of futures that stay above 100% fell from {pct(lo6.share_covered, 1)} to{" "}
        {pct(lo7.share_covered, 1)}. On the central path, two things differ. The business earns less in the first year: own funds rise by{" "}
        {randM(d(cc.v7.own_funds, 1), 1)} against {randM(d(cc.v6.own_funds, 1), 1)}, and pull ahead only in the fourth. And the capital required is higher and stays
        so, mostly through the open fixed-rate charge ({randM(cc.v7.nominal[1])} against {randM(cc.v6.nominal[1])} after a year). Of the gap in first-year
        cover, about {pct(Math.max(0, Math.min(1, ofShare)), 0)} comes from the lower own funds and the rest from the higher requirement.
      </p>
      <p className="note caveat">
        Why, is a hypothesis, not a finding. Age-rated premiums are low at first and high later, so their profit arrives later and its value sits further out on
        the fixed-rate curve, where the company holds no bonds against it. That fits both differences. But v7's funeral book is also bigger ({thousands(v7.policies.funeral)}{" "}
        policies against {thousands(r.v6!.policies.funeral)}), which raises the same charges by itself, and the two have not been separated.
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Rates as expected, R million</th>
              <th></th>
              {T.map((t) => (
                <th key={t} className="num">
                  {y0 + t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.flatMap((row) =>
              (["v6", "v7"] as const).map((k) => (
                <tr key={row.name + k}>
                  <td>{k === "v6" ? row.name : ""}</td>
                  <td>{k}</td>
                  {T.map((t) => (
                    <td key={t} className="num">
                      {row.cover ? coverPct(row.f(cc[k], t)) : randM(row.f(cc[k], t), 1)}
                    </td>
                  ))}
                </tr>
              )),
            )}
          </tbody>
        </table>
      </TableView>
    </section>
  );
}

/** v7's two capital levels: R400 million (cover 1.8, the main run) and the level at which cover starts at 1.0. */
function CapitalLevels({ c, v6 }: { c: NonNullable<NonNullable<Research["v4"]>["capital"]>; v6: NonNullable<Research["v4"]>["capital"] | null }) {
  const L = c.levels;
  const names = Object.keys(L[0].stresses);
  const low = L[0], high = L[L.length - 1];
  const under = names.filter((n) => low.stresses[n] < 1);
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2 className="serif">A company that only just meets the requirement</h2>
          <p className="eyebrow">The same book on two levels of starting capital. Rule: {c.rule}.</p>
        </div>
      </div>
      <p className="note">
        I set both levels before running either. {randM(high.own_funds)} is the industry median, cover {coverPct(high.cover)}. {randM(low.own_funds, 1)} is
        where cover starts at exactly 100%, the regulator's floor, so it shows how often a company that just meets its requirement falls below it. The bonds
        stay matched to what is owed; only the Treasury bill changes. Both use the same 1,000 futures and the same five disasters.
      </p>
      <p className="note">
        At the floor, {pct(low.share_covered, 1)} of futures stay covered every year, against {pct(high.share_covered, 1)} at the median. The first year is the
        risky one: {pct(low.below_one_by_year?.[1] ?? 0, 1)} of futures are below 100% at its end, and{" "}
        {pct(low.below_one_by_year?.[(low.below_one_by_year?.length ?? 1) - 1] ?? 0, 1)} by the fifth, as the business earns its way up.{" "}
        {v6 && `With every funeral premium level (v6), ${pct(v6.levels[0].share_covered, 1)} stayed covered at its floor.`}{" "}
        {under.length > 0 &&
          `${under.length} of ${names.length} disasters take it below: ${under.map((n) => `${(STRESS[n]?.name ?? n).toLowerCase()} (${coverPct(low.stresses[n])})`).join(", ")}.`}
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Starting capital</th>
              <th className="num">Capital required</th>
              <th className="num">Cover today</th>
              <th className="num">Futures covered throughout</th>
              <th className="num">Below 100% after a year</th>
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
                <td>{randM(x.own_funds, 1)}</td>
                <td className="num">{randM(x.scr, 1)}</td>
                <td className="num">{coverPct(x.cover)}</td>
                <td className="num">{pct(x.share_covered, 1)}</td>
                <td className="num">{pct(x.below_one_by_year?.[1] ?? 0, 1)}</td>
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
