import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type Price, type Quote, type Research, type Sex } from "./api";
import { IntervalChart, YearChart, type Band, type Interval, type Points, type Series } from "./charts";
import { SEX_LABEL, num, pct, thousands } from "./format";

const SEXES: Sex[] = ["Male", "Female"];
const COLOR: Record<Sex, string> = { Male: "var(--men)", Female: "var(--women)" };
const AGES = [55, 65, 75];
const RATES = [0.02, 0.04, 0.06];
const ADJS = [0.6, 0.7, 0.8];
const REPO = "https://github.com/Sbusiso-Mdingi/mdingi-life";
const MODEL_NAMES: Record<string, string> = { B0: "No improvement", LC: "Lee-Carter", CBD: "Cairns-Blake-Dowd", RH: "Renshaw-Haberman" };

const find = (prices: Price[], age: number, rate: number, adj: number) =>
  prices.find((p) => p.age === age && Math.abs(p.rate - rate) < 1e-9 && Math.abs(p.adj - adj) < 1e-9)!;
const meanAbs = (v: number[]) => v.reduce((a, b) => a + Math.abs(b), 0) / v.length;
const f2 = (v: number) => num(v, 2);
const f1 = (v: number) => num(v, 1);

function Metric({ value, label, sub, className, children }: { value: string; label: string; sub?: string; className?: string; children?: ReactNode }) {
  return (
    <div className="metric">
      <div className={`value ${className ?? ""}`}>{value}</div>
      <div className="label">{label}</div>
      {sub && <div className="sub">{sub}</div>}
      {children}
    </div>
  );
}

function Icon({ pass }: { pass: boolean }) {
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

function Verdict({ pass, who }: { pass: boolean; who?: string }) {
  return (
    <span className={`verdict ${pass ? "pass" : "fail"}`}>
      <Icon pass={pass} />
      {who ? `${who} ` : ""}
      {pass ? "Pass" : "Fail"}
    </span>
  );
}

function LowerBound() {
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

function Segmented<T extends string | number>({ options, value, onChange, label }: { options: { id: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
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

function Legend({ items }: { items: { label: string; color: string; kind?: "line" | "dash" | "band" | "dot" }[] }) {
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

function TableView({ children }: { children: ReactNode }) {
  return (
    <details className="table-view">
      <summary>Table view</summary>
      <div className="table-wrap">{children}</div>
    </details>
  );
}

export function App({ embedded }: { embedded: boolean }) {
  const [research, setResearch] = useState<Research | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.research().then(setResearch, (e) => setError(String(e)));
  }, []);

  if (error) return <div className="preview loading">Could not load the results: {error}</div>;
  if (!research) return <div className="preview loading">Loading results…</div>;

  const r = research;
  const at65 = (s: Sex) => find(r.annuities[s].prices, 65, 0.04, 0.7);
  const p3 = r.backtest.tests.P3;

  return (
    <div className="preview">
      <header className="head" id="hero">
        <div>
          <p className="eyebrow">Live preview · Mdingi Life · v1 Liabilities</p>
          <h1 className="serif">
            Mdingi Life is a fictional South African life insurer. <em>v1 prices its annuities.</em>
          </h1>
          <p className="lede">
            How much does uncertainty about future South African mortality move the price of a life annuity? Four models were backtested on rules
            written down before any fit. The best one prices the annuities, with a 95% interval.
          </p>
        </div>
        <div className="status">
          <span>
            <i className="dot" />
            Protocol {r.protocol}
          </span>
          <span>Data: UN WPP 2024</span>
          <span>Forecast from {r.annuities.Male.jump_off}</span>
        </div>
      </header>

      <section className="hero-figures" aria-label="Headline">
        {SEXES.map((s) => (
          <Metric
            key={s}
            value={`${p3[s] ? "" : "≥ "}${num(at65(s).width_pct, 1)}%`}
            label={`${SEX_LABEL[s]}, 65`}
            sub={`${f2(at65(s).median)} [${f2(at65(s).lo)}, ${f2(at65(s).hi)}]`}
          >
            {!p3[s] && <LowerBound />}
          </Metric>
        ))}
      </section>
      <p className="note">
        Width of the 95% interval of the price of a life annuity bought at 65, as a share of the median: 1 a year paid monthly, 4% discount rate,
        annuitant factor 0.7. Mortality uncertainty alone moves the price across a range about 14% wide.
      </p>

      {r.history && <History r={r} />}
      <FanPanel r={r} />
      <Backtest r={r} />
      <Explorer r={r} />
      <Sensitivity r={r} />
      <Method r={r} />

      <p className="footer-note">
        Mdingi Life is a fictional company. The mortality data and the methods are real. Research output, not an actuarial opinion or a quote.
        {embedded ? "" : " Source: github.com/Sbusiso-Mdingi/mdingi-life."}
      </p>
    </div>
  );
}

function History({ r }: { r: Research }) {
  const h = r.history!;
  const [measure, setMeasure] = useState<"e0" | "e65">("e0");
  const v = h[measure];
  const yr = (y: number) => h.years.indexOf(y);
  const series: Series[] = SEXES.map((s) => ({ key: s, label: SEX_LABEL[s], color: COLOR[s], xs: h.years, ys: v[s] }));
  const fall = (s: Sex, from: [number, number], to: [number, number]) => {
    const seg = (a: number, b: number) => h.e0[s].slice(yr(a), yr(b) + 1);
    return Math.max(...seg(...from)) - Math.min(...seg(...to));
  };
  const covid = (s: Sex) => h.e65[s][yr(2019)] - h.e65[s][yr(2021)];
  return (
    <section className="panel" id="history">
      <div className="panel-head">
        <div>
          <p className="eyebrow">South African mortality since {h.years[0]}</p>
          <h2 className="serif">Life expectancy {measure === "e0" ? "at birth" : "at 65"}</h2>
        </div>
        <Segmented
          label="Measure"
          value={measure}
          onChange={setMeasure}
          options={[
            { id: "e0", label: "At birth" },
            { id: "e65", label: "At 65" },
          ]}
        />
      </div>
      <Legend items={SEXES.map((s) => ({ label: SEX_LABEL[s], color: COLOR[s] }))} />
      <YearChart
        label={`Life expectancy ${measure === "e0" ? "at birth" : "at 65"} in South Africa by year and sex, ${h.years[0]} to ${h.years[h.years.length - 1]}`}
        series={series}
        fmt={f1}
        notes={[
          { x0: 2004, x1: 2006, label: "HIV deaths peak", short: "HIV peak", row: 0 },
          { x0: 2004, label: "Public ARV rollout, 2004", short: "ARVs, 2004", row: 1, anchor: "end" },
          { x0: 2020, x1: 2022, label: "Covid-19", short: "Covid", row: 0, anchor: "end" },
        ]}
      />
      <p className="note">
        Life expectancy at birth fell by {Math.round(fall("Male", [1985, 1995], [2000, 2010]))} years for men and{" "}
        {Math.round(fall("Female", [1985, 1995], [2000, 2010]))} for women between about 1990 and 2005 as HIV deaths rose, and recovered once
        treatment reached people. At 65 the HIV hump barely shows: it killed mostly younger adults. Covid took {f1(covid("Male"))} years off
        men's life expectancy at 65 in 2021. Source: UN WPP 2024 life tables.
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Year</th>
              {SEXES.map((s) => (
                <th key={s} className="num">
                  {SEX_LABEL[s]}, at birth
                </th>
              ))}
              {SEXES.map((s) => (
                <th key={s} className="num">
                  {SEX_LABEL[s]}, at 65
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {h.years.map((y, i) => (
              <tr key={y}>
                <td>{y}</td>
                {SEXES.map((s) => (
                  <td key={s} className="num">
                    {f1(h.e0[s][i])}
                  </td>
                ))}
                {SEXES.map((s) => (
                  <td key={s} className="num">
                    {f1(h.e65[s][i])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableView>
    </section>
  );
}

function FanPanel({ r }: { r: Research }) {
  const jump = r.fan.Male.jump_off;
  const series: Series[] = [];
  const bands: Band[] = [];
  const points: Points[] = [];
  for (const s of SEXES) {
    const f = r.fan[s];
    const last = f.observed[f.observed_years.indexOf(f.jump_off)];
    const xs = [f.jump_off, ...f.years];
    bands.push({ key: `${s}band`, label: `${SEX_LABEL[s]}, 95% band`, color: COLOR[s], xs, lo: [last, ...f.lo], hi: [last, ...f.hi] });
    series.push({
      key: `${s}obs`,
      label: `${SEX_LABEL[s]}, observed`,
      color: COLOR[s],
      xs: f.observed_years,
      ys: f.observed_years.map((y, i) => (f.covid.includes(y) ? null : f.observed[i])),
    });
    series.push({ key: `${s}med`, label: `${SEX_LABEL[s]}, median`, color: COLOR[s], xs, ys: [null, ...f.median], dash: true });
    series.push({ key: `${s}join`, label: "", color: COLOR[s], xs: xs.slice(0, 2), ys: [last, f.median[0]], dash: true });
    const cv = f.observed_years.map((y, i) => [y, f.observed[i]] as const).filter(([y]) => f.covid.includes(y));
    points.push({ key: `${s}covid`, label: `${SEX_LABEL[s]}, Covid year`, color: COLOR[s], xs: cv.map((c) => c[0]), ys: cv.map((c) => c[1]) });
  }
  const end = (s: Sex, k: "median" | "lo" | "hi") => r.fan[s][k][r.fan[s][k].length - 1];
  const lastYear = r.fan.Male.years[r.fan.Male.years.length - 1];
  return (
    <section className="panel" id="fan">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Forecast · {MODEL_NAMES.CBD}, fitted 1997 to {jump}</p>
          <h2 className="serif">Life expectancy at 65, forecast to {lastYear}</h2>
        </div>
      </div>
      <Legend
        items={[
          ...SEXES.map((s) => ({ label: SEX_LABEL[s], color: COLOR[s] })),
          { label: "Median forecast", color: "var(--muted-foreground)", kind: "dash" as const },
          { label: "95% band", color: "var(--muted-foreground)", kind: "band" as const },
          { label: "Covid years, not fitted", color: "var(--muted-foreground)", kind: "dot" as const },
        ]}
      />
      <YearChart
        label={`Observed and forecast period life expectancy at 65 by sex, 1997 to ${lastYear}, with 95% bands`}
        series={series}
        bands={bands}
        points={points}
        fmt={f1}
        height={320}
        notes={[
          { x0: 2020, x1: 2022, label: "Covid-19, left out of the fit", short: "Covid", row: 0, anchor: "end" },
          { x0: jump, label: `Forecast from ${jump}`, short: "Forecast", row: 0, anchor: "start" },
        ]}
      />
      <p className="note">
        By {lastYear} the median is {f1(end("Male", "median"))} years for men and {f1(end("Female", "median"))} for women, with 95% bands of{" "}
        {f1(end("Male", "lo"))} to {f1(end("Male", "hi"))} and {f1(end("Female", "lo"))} to {f1(end("Female", "hi"))}. The bands come from 5,000
        simulated paths over 500 bootstrap refits. The 2021 Covid point falls far below anything the model was asked to expect.
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Year</th>
              {SEXES.map((s) => (
                <th key={s} className="num">
                  {SEX_LABEL[s]}
                </th>
              ))}
              {SEXES.map((s) => (
                <th key={s} className="num">
                  {SEX_LABEL[s]}, 95% band
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {r.fan.Male.observed_years.map((y, i) => (
              <tr key={y}>
                <td>
                  {y}
                  {r.fan.Male.covid.includes(y) && <span className="tag">Covid, not fitted</span>}
                </td>
                {SEXES.map((s) => (
                  <td key={s} className="num">
                    {f1(r.fan[s].observed[i])}
                  </td>
                ))}
                {SEXES.map((s) => (
                  <td key={s} className="num muted">
                    observed
                  </td>
                ))}
              </tr>
            ))}
            {r.fan.Male.years.map((y, i) => (
              <tr key={y}>
                <td>{y}</td>
                {SEXES.map((s) => (
                  <td key={s} className="num">
                    {f1(r.fan[s].median[i])}
                  </td>
                ))}
                {SEXES.map((s) => (
                  <td key={s} className="num">
                    {f1(r.fan[s].lo[i])} to {f1(r.fan[s].hi[i])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableView>
    </section>
  );
}

function Backtest({ r }: { r: Research }) {
  const t = r.backtest.tests;
  const v = r.backtest.validation;
  const chosen = t.chosen;
  const cov = (s: Sex) => v[chosen[s]][s].coverage;
  const err = (s: Sex) => meanAbs(v[chosen[s]][s].annuity_error);
  const lc = Object.keys(v).find((k) => k.startsWith("LC"))!;
  const tests: { id: "P1" | "P2" | "P3" | "P4"; claim: string; plain: string }[] = [
    {
      id: "P1",
      claim: "Improvement is real",
      plain: "The best model beat the no-improvement baseline for men and women. Mortality kept falling over 2017 to 2019.",
    },
    {
      id: "P2",
      claim: "The HIV hump",
      plain: "Lee-Carter fitted from 2006 beat Lee-Carter fitted from 1997. The rise in deaths before 2006 bends a single-trend model.",
    },
    {
      id: "P3",
      claim: "Honest intervals: 95% bands catch at least 90% of observed rates",
      plain: `The bands caught ${pct(cov("Male"), 0)} of rates for men and ${pct(cov("Female"), 0)} for women. Men's price intervals are therefore lower bounds. Women pass exactly at the line.`,
    },
    {
      id: "P4",
      claim: "Annuity price error at 65 under 2%",
      plain: `Annuity factors from the forecast missed the observed ones by ${pct(err("Male"))} for men and ${pct(err("Female"))} for women on average.`,
    },
  ];
  return (
    <section className="panel" id="backtest">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Backtest · fit to 2016, score 2017 to 2019, ages 50 to 89</p>
          <h2 className="serif">Four tests, set before the first fit</h2>
        </div>
      </div>
      <ul className="tests">
        {tests.map((x) => (
          <li key={x.id}>
            <div className="test-head">
              <span className="mono small">{x.id}</span>
              <strong>{x.claim}</strong>
              {SEXES.map((s) => (
                <Verdict key={s} pass={t[x.id][s]} who={SEX_LABEL[s]} />
              ))}
            </div>
            <p className="plain" style={{ marginLeft: 34 }}>
              {x.plain}
            </p>
          </li>
        ))}
      </ul>

      <h3 className="eyebrow" style={{ margin: "30px 0 12px" }}>
        Models compared on the validation years
      </h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Window</th>
              <th className="num">Deviance, men</th>
              <th className="num">Deviance, women</th>
              <th className="num">95% coverage, men</th>
              <th className="num">95% coverage, women</th>
              <th className="num">Annuity error, men</th>
              <th className="num">Annuity error, women</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(v).map(([k, row]) => {
              const [name, ...rest] = k.split(" ");
              const isChosen = SEXES.some((s) => chosen[s] === k);
              return (
                <tr key={k} className={isChosen ? "final" : undefined}>
                  <td>
                    {MODEL_NAMES[name] ?? name}
                    {isChosen && <span className="tag">Chosen</span>}
                  </td>
                  <td className="muted">{name === "B0" ? "last three years" : rest.join(" ")}</td>
                  {SEXES.map((s) => (
                    <td key={s} className="num">
                      {thousands(row[s].deviance)}
                    </td>
                  ))}
                  {SEXES.map((s) => (
                    <td key={s} className="num">
                      {name === "B0" ? "n/a" : pct(row[s].coverage, 0)}
                    </td>
                  ))}
                  {SEXES.map((s) => (
                    <td key={s} className="num">
                      {pct(meanAbs(row[s].annuity_error))}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="note">
        Lower deviance is a closer fit to observed deaths. Coverage is the share of observed rates inside the 95% band; it should be near 95%.
        Annuity error is the average miss on the price at 65. {MODEL_NAMES.CBD} wins on all three for both sexes; {MODEL_NAMES.LC}'s
        bands caught only {pct(v[lc].Male.coverage, 0)} and {pct(v[lc].Female.coverage, 0)}.
      </p>
    </section>
  );
}

function Explorer({ r }: { r: Research }) {
  const [sex, setSex] = useState<Sex>("Male");
  const [age, setAge] = useState(65);
  const [rate, setRate] = useState(0.04);
  const [adj, setAdj] = useState(0.7);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setBusy(true);
    api.price(sex, age, rate, adj).then(
      (q) => live && (setQuote(q), setError(null), setBusy(false)),
      (e) => live && (setError(String(e.message ?? e)), setBusy(false)),
    );
    return () => {
      live = false;
    };
  }, [sex, age, rate, adj]);

  const rows: Interval[] = SEXES.flatMap((s) =>
    AGES.map((a) => {
      const p = find(r.annuities[s].prices, a, rate, adj);
      return { key: `${s}${a}`, label: `${SEX_LABEL[s]}, ${a}`, color: COLOR[s], lo: p.lo, median: p.median, hi: p.hi, active: s === sex && a === age };
    }),
  );
  const all = useMemo(() => SEXES.flatMap((s) => r.annuities[s].prices.map((p) => ({ s, ...p }))), [r]);

  return (
    <section className="panel" id="price">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Price explorer · bought in 2026</p>
          <h2 className="serif">What a life annuity of 1 a year costs</h2>
        </div>
      </div>
      <div className="controls">
        <div className="control">
          <span className="label">Sex</span>
          <Segmented label="Sex" value={sex} onChange={setSex} options={SEXES.map((s) => ({ id: s, label: SEX_LABEL[s] }))} />
        </div>
        <div className="control">
          <span className="label">Age</span>
          <Segmented label="Age" value={age} onChange={setAge} options={AGES.map((a) => ({ id: a, label: String(a) }))} />
        </div>
        <div className="control">
          <span className="label">Discount rate</span>
          <Segmented label="Discount rate" value={rate} onChange={setRate} options={RATES.map((x) => ({ id: x, label: pct(x, 0) }))} />
        </div>
        <div className="control">
          <span className="label">Annuitant factor</span>
          <Segmented label="Annuitant factor" value={adj} onChange={setAdj} options={ADJS.map((x) => ({ id: x, label: x.toFixed(1) }))} />
        </div>
      </div>
      {error && <p className="note error">Could not price this: {error}</p>}
      {quote && (
        <div className={`metrics refetch${busy ? " busy" : ""}`}>
          <Metric className="sans" value={f2(quote.median)} label="Median price" sub="per 1 a year, paid monthly" />
          <Metric className="sans" value={`${f2(quote.lo)} to ${f2(quote.hi)}`} label="95% interval" sub="mortality uncertainty only" />
          <Metric className="sans" value={`${quote.lower_bound ? "≥ " : ""}${num(quote.width_pct, 1)}%`} label="Interval width" sub="as a share of the median">
            {quote.lower_bound && <LowerBound />}
          </Metric>
        </div>
      )}
      <div style={{ marginTop: 22 }}>
        <p className="eyebrow" style={{ marginBottom: 8 }}>
          Every age at {pct(rate, 0)} and factor {adj.toFixed(1)}: median and 95% interval
        </p>
        <Legend items={SEXES.map((s) => ({ label: SEX_LABEL[s], color: COLOR[s] }))} />
        <IntervalChart label={`Annuity price by sex and age at ${pct(rate, 0)} and annuitant factor ${adj.toFixed(1)}`} rows={rows} fmt={f2} groups={2} />
      </div>
      <p className="note">
        The annuitant factor scales population death rates down, because people who buy annuities live longer. The relative width grows with age:
        an older buyer's price rests on fewer, nearer years, where the model's age-slope uncertainty bites hardest.
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Sex</th>
              <th className="num">Age</th>
              <th className="num">Rate</th>
              <th className="num">Factor</th>
              <th className="num">Median</th>
              <th className="num">95% interval</th>
              <th className="num">Width</th>
            </tr>
          </thead>
          <tbody>
            {all.map((p) => (
              <tr key={`${p.s}${p.age}${p.rate}${p.adj}`}>
                <td>{SEX_LABEL[p.s]}</td>
                <td className="num">{p.age}</td>
                <td className="num">{pct(p.rate, 0)}</td>
                <td className="num">{p.adj.toFixed(1)}</td>
                <td className="num">{f2(p.median)}</td>
                <td className="num">
                  {f2(p.lo)} to {f2(p.hi)}
                </td>
                <td className="num">
                  {r.backtest.tests.P3[p.s] ? "" : "≥ "}
                  {num(p.width_pct, 1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableView>
    </section>
  );
}

function Sensitivity({ r }: { r: Research }) {
  const rows: Interval[] = SEXES.flatMap((s) =>
    ADJS.map((a) => {
      const p = find(r.annuities[s].prices, 65, 0.04, a);
      return { key: `${s}${a}`, label: `${SEX_LABEL[s]}, ${a.toFixed(1)}`, color: COLOR[s], lo: p.lo, median: p.median, hi: p.hi };
    }),
  );
  const m = (a: number) => find(r.annuities.Male.prices, 65, 0.04, a);
  const swing = (m(0.6).median - m(0.8).median) / m(0.6).median;
  return (
    <section className="panel" id="change">
      <div className="panel-head">
        <div>
          <p className="eyebrow">What would change this</p>
          <h2 className="serif">The annuitant assumption matters as much as the model</h2>
        </div>
      </div>
      <div>
        <div>
          <p className="eyebrow" style={{ marginBottom: 8 }}>
            Price at 65 and 4%, by annuitant factor
          </p>
          <Legend items={SEXES.map((s) => ({ label: SEX_LABEL[s], color: COLOR[s] }))} />
          <IntervalChart label="Annuity price at 65 and 4% by sex and annuitant factor" rows={rows} fmt={f2} groups={2} />
          <p className="note">
            Moving the factor from 0.6 to 0.8 cuts the men's price from {f2(m(0.6).median)} to {f2(m(0.8).median)}, a {pct(swing, 0)} swing. The
            whole model interval at 0.7 is {pct(m(0.7).width_pct / 100, 0)} wide.
          </p>
        </div>
        <div className="facts" style={{ marginTop: 26 }}>
          <p>
            <strong>The factor is an assumption</strong>
            No public South African annuitant experience is used. 0.6, 0.7 and 0.8 are shown side by side, not estimated.
          </p>
          <p>
            <strong>Smoothed data</strong>
            These results run on UN WPP 2024, which are model estimates and smoother than registered deaths. Every fit here looks better than it
            will on raw data.
          </p>
          <p>
            <strong>Stats SA to follow</strong>
            A rerun on Stats SA registered deaths will be added beside this one, not replace it.
          </p>
          <p>
            <strong>Flat discount rate</strong>
            v1 discounts at a flat 2%, 4% or 6%. v2 replaces it with the fitted South African government bond curve.
          </p>
        </div>
      </div>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Sex</th>
              <th className="num">Factor</th>
              <th className="num">Median</th>
              <th className="num">95% interval</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.key}>
                <td>{x.label.split(",")[0]}</td>
                <td className="num">{x.label.split(", ")[1]}</td>
                <td className="num">{f2(x.median)}</td>
                <td className="num">
                  {f2(x.lo)} to {f2(x.hi)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableView>
    </section>
  );
}

function Method({ r }: { r: Research }) {
  return (
    <section className="panel" id="method">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Method and sources</p>
          <h2 className="serif">How it was done</h2>
        </div>
      </div>
      <ul className="method">
        <li>
          <strong>Protocol first</strong>
          Rules, tests and pass marks were written before any model was fitted, and frozen at commit <span className="mono">{r.protocol}</span>.{" "}
          <a href={`${REPO}/blob/main/research/PROTOCOL.md`} target="_blank" rel="noreferrer">
            Protocol
          </a>{" "}
          ·{" "}
          <a href={`${REPO}/blob/main/research/RESULTS.md`} target="_blank" rel="noreferrer">
            Results
          </a>
        </li>
        <li>
          <strong>Models</strong>
          No improvement, Lee-Carter, Cairns-Blake-Dowd and Renshaw-Haberman, by sex, on ages 50 to 89. Rates above 89 follow a Kannisto curve to
          120. Covid years 2020 to 2022 are left out of every fit.
        </li>
        <li>
          <strong>Uncertainty</strong>
          500 bootstrap refits of the deaths and 5,000 simulated paths, so the interval carries both parameter and process uncertainty.
        </li>
        <li>
          <strong>Product</strong>
          Level life annuity of 1 a year, paid monthly in advance, no guarantee period, bought in 2026. Death rates follow the buyer's cohort.
        </li>
        <li>
          <strong>Sources</strong>
          United Nations, Population Division (2024), World Population Prospects 2024, CC BY 3.0 IGO. Statistics South Africa, P0309.3 and P0302,
          via DataFirst: <span className="tag">To follow</span>
        </li>
        <li>
          <strong>Fictional company</strong>
          Mdingi Life does not exist and sells nothing. It is a portfolio project. The data and methods are real.{" "}
          <a href={REPO} target="_blank" rel="noreferrer">
            Code
          </a>
        </li>
      </ul>
    </section>
  );
}
