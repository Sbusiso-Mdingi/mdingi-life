import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type Price, type Quote, type Research, type Rolling, type Sex } from "./api";
import { IntervalChart, YearChart, type Band, type Interval, type Points, type Series } from "./charts";
import { SEX_LABEL, num, pct, thousands } from "./format";

const SEXES: Sex[] = ["Male", "Female"];
const COLOR: Record<Sex, string> = { Male: "var(--men)", Female: "var(--women)" };
const AGES = [55, 65, 75];
const RATES = [0.02, 0.04, 0.06];
const ADJS = [0.6, 0.7, 0.8];
const REPO = "https://github.com/Sbusiso-Mdingi/mdingi-life";
const MODEL_NAMES: Record<string, string> = { B0: "No improvement", LC: "Lee-Carter", CBD: "Cairns-Blake-Dowd", RH: "Renshaw-Haberman" };
const WINDOW_START: Record<string, number> = { full: 1997, "post-peak": 2006 };
const WINDOW_TEXT: Record<string, string> = { full: "from 1997", "post-peak": "from 2006", rolling: "last 10 years", "last three": "last three years" };
const modelLabel = (k: string) => {
  const [name, ...rest] = k.split(" ");
  return `${MODEL_NAMES[name] ?? name}, ${WINDOW_TEXT[rest.join(" ")] ?? rest.join(" ")}`;
};
const MODEL_COLOR: Record<string, string> = { B0: "var(--muted-foreground)", LC: "var(--m-lc)", CBD: "var(--m-cbd)", RH: "var(--m-rh)" };

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
          <span>{r.source === "statssa" ? "Data: Stats SA registered deaths" : "Data: UN WPP 2024"}</span>
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
        annuitant factor 0.7. Mortality uncertainty alone moves the price across a range about {Math.round((at65("Male").width_pct + at65("Female").width_pct) / 2)}%
        wide{SEXES.some((s) => !p3[s]) ? ", and the true range is wider" : ""}.
      </p>

      {r.history && <History r={r} />}
      <FanPanel r={r} />
      <Backtest r={r} />
      {r.rolling && <RollingPanel r={r} />}
      <Explorer r={r} />
      {r.compare && <Sources r={r} />}
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
  const [name, window] = r.fan.Male.model.split(" ");
  const sameModel = SEXES.every((s) => r.fan[s].model === r.fan.Male.model);
  // Covid years inside the forecast that fell below the band, for men and women.
  const below = (s: Sex) =>
    r.fan[s].covid.filter((y) => {
      const i = r.fan[s].years.indexOf(y);
      return i >= 0 && r.fan[s].observed[r.fan[s].observed_years.indexOf(y)] < r.fan[s].lo[i];
    });
  return (
    <section className="panel" id="fan">
      <div className="panel-head">
        <div>
          <p className="eyebrow">
            Forecast · {sameModel ? MODEL_NAMES[name] : "chosen model by sex"}, fitted {WINDOW_START[window] ?? 1997} to {jump}
          </p>
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
          { x0: jump, label: `Forecast from ${jump}`, short: "Forecast", row: 1, anchor: "end" },
        ]}
      />
      <p className="note">
        By {lastYear} the median is {f1(end("Male", "median"))} years for men and {f1(end("Female", "median"))} for women, with 95% bands of{" "}
        {f1(end("Male", "lo"))} to {f1(end("Male", "hi"))} and {f1(end("Female", "lo"))} to {f1(end("Female", "hi"))}. The bands come from 5,000
        simulated paths over 500 bootstrap refits.
        {r.source === "statssa" ? " Observed life expectancy here comes from registered deaths, so it sits above WPP's life tables wherever deaths go unregistered." : ""}
        {SEXES.some((s) => below(s).length > 0)
          ? ` Covid years fell below the band (men: ${below("Male").join(", ") || "none"}; women: ${below("Female").join(", ") || "none"}): a pandemic is not something the model was asked to expect.`
          : ""}
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
      plain: `The bands caught ${pct(cov("Male"), 0)} of rates for men and ${pct(cov("Female"), 0)} for women. ${
        t.P3.Male && t.P3.Female
          ? "Both pass."
          : !t.P3.Male && !t.P3.Female
            ? "Both fail, so every price interval here is reported as a lower bound."
            : `${t.P3.Male ? "Women's" : "Men's"} price intervals are therefore lower bounds.`
      }`,
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
        Annuity error is the average miss on the price at 65. The protocol chooses on deviance alone: {SEXES.map((s) => `${modelLabel(chosen[s])} for ${SEX_LABEL[s].toLowerCase()}`).join(", ")}.{" "}
        {MODEL_NAMES.LC}'s bands caught only {pct(v[lc].Male.coverage, 0)} and {pct(v[lc].Female.coverage, 0)}.
      </p>
    </section>
  );
}

function RollingPanel({ r }: { r: Research }) {
  const g = r.rolling!;
  const [sex, setSex] = useState<Sex>("Male");
  const n = g.origins.length;
  const first = g.origins[0];
  const last = g.origins[n - 1];
  const cand = (s: Sex) => g.by_sex[s].candidates;
  const keys = Object.keys(cand("Male")).sort((a, b) => cand("Male")[a].deviance + cand("Female")[a].deviance - cand("Male")[b].deviance - cand("Female")[b].deviance);
  const fam = (k: string) => k.split(" ")[0];
  const held = SEXES.every((s) => g.readings.R1[s]);
  const family = SEXES.every((s) => fam(g.readings.lowest[s]) === fam(g.chosen[s]));
  const title = held
    ? `The chosen model holds up over ${n} jump-offs`
    : family
      ? `Over ${n} jump-offs the model holds up, its fitting window less so`
      : `Over ${n} jump-offs, the protocol's choice is not the best`;
  const wins = (s: Sex) => cand(s)[g.chosen[s]].wins;
  const famWins = (s: Sex) => g.by_sex[s].winners.filter((w) => fam(w) === fam(g.chosen[s])).length;
  const rp = g.reprice[sex];
  const quoted = Object.keys(rp.quotes);
  const series: Series[] = quoted.map((k) => ({
    key: k,
    label: modelLabel(k),
    color: MODEL_COLOR[fam(k)],
    xs: rp.jump_offs,
    ys: rp.quotes[k].map((q) => q.price),
    dash: fam(k) === "B0",
  }));
  const dots: Points[] = quoted.map((k) => ({
    key: `${k}-pts`,
    label: "",
    color: MODEL_COLOR[fam(k)],
    xs: rp.jump_offs.filter((_, i) => rp.quotes[k][i].price != null),
    ys: rp.quotes[k].flatMap((q) => (q.price == null ? [] : [q.price])),
  }));
  const gaps = quoted.flatMap((k) => {
    const miss = rp.jump_offs.filter((_, i) => rp.quotes[k][i].price == null);
    return miss.length ? [`${modelLabel(k)} (${miss[0]}${miss.length > 1 ? ` to ${miss[miss.length - 1]}` : ""})`] : [];
  });
  const swing = (k: string) => {
    const v = rp.quotes[k].flatMap((q) => (q.price == null ? [] : [q.price]));
    return v.length > 1 ? (Math.max(...v) - Math.min(...v)) / Math.min(...v) : 0;
  };
  const chosenKey = g.chosen[sex];
  const b = r.blend;
  const blendRows: Interval[] = b
    ? SEXES.flatMap((s) =>
        AGES.flatMap((a) => {
          const c = find(r.annuities[s].prices, a, 0.04, 0.7);
          const m = find(b[s].prices, a, 0.04, 0.7);
          return [
            { key: `${s}${a}c`, label: `${SEX_LABEL[s]}, ${a} · chosen`, color: COLOR[s], lo: c.lo, median: c.median, hi: c.hi },
            { key: `${s}${a}b`, label: `${SEX_LABEL[s]}, ${a} · blend`, color: COLOR[s], lo: m.lo, median: m.median, hi: m.hi, active: true },
          ];
        }),
      )
    : [];
  const w = (s: Sex) => Object.entries(g.weights[s]).map(([k, v]) => `${k} ${pct(v, 0)}`).join(", ");
  const bw = (s: Sex) => find(b![s].prices, 65, 0.04, 0.7);
  const other = r.compare?.rolling_wpp;
  const rank = (x: Rolling, s: Sex) => {
    const c = x.by_sex[s].candidates;
    return Object.keys(c).sort((p, q) => c[p].deviance - c[q].deviance).indexOf(x.chosen[s]) + 1;
  };
  return (
    <section className="panel" id="rolling">
      <div className="panel-head">
        <div>
          <p className="eyebrow">
            Rolling origins · jump-off {first} to {last}, each scored {g.horizon} years ahead · added after validation
          </p>
          <h2 className="serif">{title}</h2>
        </div>
      </div>
      <p className="plain">
        One three-year validation block chose the model above. Here every jump-off from {first} to {last} is refitted and scored, for ten candidates:
        each model fitted from 1997, from 2006, and on a rolling 10-year window, plus no improvement. This is a robustness check written into the
        protocol before any rolling fit. It changes nothing above.
      </p>
      <ul className="tests">
        <li>
          <div className="test-head">
            <span className="mono small">R1</span>
            <strong>The chosen model has the lowest rolling deviance of the ten</strong>
            {SEXES.map((s) => (
              <Verdict key={s} pass={g.readings.R1[s]} who={SEX_LABEL[s]} />
            ))}
          </div>
          <p className="plain" style={{ marginLeft: 34 }}>
            {SEXES.map((s) =>
              g.readings.R1[s]
                ? `${SEX_LABEL[s]}: ${modelLabel(g.chosen[s])} is lowest, best at ${wins(s)} of ${n} jump-offs. `
                : `${SEX_LABEL[s]}: ${modelLabel(g.readings.lowest[s])} is lower; the chosen ${modelLabel(g.chosen[s])} is best at ${wins(s)} of ${n} jump-offs. `,
            )}
            {family ? `${MODEL_NAMES[fam(g.chosen.Male)]} on some window is best at ${famWins("Male")} of ${n} for men and ${famWins("Female")} of ${n} for women.` : ""}
          </p>
        </li>
        <li>
          <div className="test-head">
            <span className="mono small">R2</span>
            <strong>Its 95% bands catch at least 90% of rates across all jump-offs</strong>
            {SEXES.map((s) => (
              <Verdict key={s} pass={g.readings.R2[s]} who={SEX_LABEL[s]} />
            ))}
          </div>
          <p className="plain" style={{ marginLeft: 34 }}>
            They caught {pct(cand("Male")[g.chosen.Male].coverage, 0)} for men and {pct(cand("Female")[g.chosen.Female].coverage, 0)} for women.{" "}
            {SEXES.every((s) => Object.entries(cand(s)).every(([k, c]) => fam(k) === "B0" || c.coverage < 0.9))
              ? "No candidate reaches 90%. The bands hold process uncertainty only, and the shortfall is not a one-off."
              : ""}
          </p>
        </li>
      </ul>

      <div className="table-wrap" style={{ marginTop: 18 }}>
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Window</th>
              <th className="num">Deviance, men</th>
              <th className="num">Deviance, women</th>
              <th className="num">Best of {n}, men</th>
              <th className="num">Best of {n}, women</th>
              <th className="num">Coverage, men</th>
              <th className="num">Coverage, women</th>
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => {
              const [name, ...rest] = k.split(" ");
              const isChosen = SEXES.some((s) => g.chosen[s] === k);
              const isLowest = SEXES.some((s) => g.readings.lowest[s] === k);
              return (
                <tr key={k} className={isChosen ? "final" : undefined}>
                  <td>
                    {MODEL_NAMES[name] ?? name}
                    {isChosen && <span className="tag">Chosen</span>}
                    {isLowest && <span className="tag">Lowest{SEXES.filter((s) => g.readings.lowest[s] === k).length === 1 ? `, ${SEX_LABEL[SEXES.find((s) => g.readings.lowest[s] === k)!].toLowerCase()}` : ""}</span>}
                  </td>
                  <td className="muted">{WINDOW_TEXT[rest.join(" ")]}</td>
                  {SEXES.map((s) => (
                    <td key={s} className="num">
                      {thousands(cand(s)[k].deviance)}
                    </td>
                  ))}
                  {SEXES.map((s) => (
                    <td key={s} className="num">
                      {cand(s)[k].wins}
                    </td>
                  ))}
                  {SEXES.map((s) => (
                    <td key={s} className="num">
                      {name === "B0" ? "n/a" : pct(cand(s)[k].coverage, 0)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="note">
        Deviance is summed over the {n} jump-offs and {g.horizon} years ahead of each, ages 50 to 89.
        {other
          ? ` On UN WPP deaths the same check is harsher: the protocol's ${modelLabel(other.chosen.Male)} ranks ${rank(other, "Male")} of 10 for men and ${rank(other, "Female")} of 10 for women, and ${modelLabel(other.readings.lowest.Male)} is lowest${other.readings.lowest.Female === other.readings.lowest.Male ? " for both" : " for men"}.`
          : ""}
      </p>

      <div className="panel-head" style={{ marginTop: 28 }}>
        <div>
          <p className="eyebrow">Repricing · a life aged 65 in the year after each jump-off, 4%, factor 0.7</p>
          <h3 className="serif">What each model would have quoted, refitted every year</h3>
        </div>
        <Segmented label="Sex" value={sex} onChange={setSex} options={SEXES.map((s) => ({ id: s, label: SEX_LABEL[s] }))} />
      </div>
      <Legend items={quoted.map((k) => ({ label: modelLabel(k), color: MODEL_COLOR[fam(k)], kind: fam(k) === "B0" ? "dash" : "line" }))} />
      <YearChart label={`Annuity price at 65 by jump-off year and model, ${SEX_LABEL[sex].toLowerCase()}`} series={series} points={dots} fmt={f2} height={280} />
      <p className="note">
        Median of 5,000 simulated paths per quote, process uncertainty only. {modelLabel(chosenKey)} moves {pct(swing(chosenKey), 0)} between its lowest
        and highest quote, no improvement {pct(swing(quoted.find((k) => fam(k) === "B0")!), 0)}.
        {gaps.length
          ? ` No quote for ${gaps.join(", ")}: fitted on only a few years from 2006, the loading on the oldest ages comes out negative, so rates there rise as the rest improve and pass 1 before 89.`
          : ""}
      </p>

      {b && (
        <>
          <div className="panel-head" style={{ marginTop: 28 }}>
            <div>
              <p className="eyebrow">Blended price · bought in 2026, 4%, factor 0.7</p>
              <h3 className="serif">
                {SEXES.every((s) => bw(s).width_pct > find(r.annuities[s].prices, 65, 0.04, 0.7).width_pct)
                  ? "Weighting the models by their rolling record widens the interval"
                  : "Weighting the models by their rolling record"}
              </h3>
            </div>
          </div>
          <Legend items={SEXES.map((s) => ({ label: SEX_LABEL[s], color: COLOR[s] }))} />
          <IntervalChart label="Chosen-model and blended annuity prices by sex and age" rows={blendRows} fmt={f2} groups={2} />
          <p className="note">
            The blend pools each model's production paths in proportion to 1 / its rolling deviance: {w("Male")} for men, {w("Female")} for women. At 65 it
            prices {f2(bw("Male").median)} [{f2(bw("Male").lo)}, {f2(bw("Male").hi)}] for men and {f2(bw("Female").median)} [{f2(bw("Female").lo)},{" "}
            {f2(bw("Female").hi)}] for women, an interval {num(bw("Male").width_pct, 0)}% and {num(bw("Female").width_pct, 0)}% wide against{" "}
            {num(find(r.annuities.Male.prices, 65, 0.04, 0.7).width_pct, 0)}% and {num(find(r.annuities.Female.prices, 65, 0.04, 0.7).width_pct, 0)}% for the
            chosen model.{" "}
            {SEXES.every((s) => bw(s).width_pct > find(r.annuities[s].prices, 65, 0.04, 0.7).width_pct)
              ? "It carries some of the model risk the single model leaves out. "
              : ""}
            It is shown next to the chosen price, not in its place.
          </p>
          <TableView>
            <table>
              <thead>
                <tr>
                  <th>Sex</th>
                  <th className="num">Age</th>
                  <th className="num">Chosen</th>
                  <th className="num">Blend</th>
                </tr>
              </thead>
              <tbody>
                {SEXES.flatMap((s) =>
                  AGES.map((a) => {
                    const c = find(r.annuities[s].prices, a, 0.04, 0.7);
                    const m = find(b[s].prices, a, 0.04, 0.7);
                    return (
                      <tr key={`${s}${a}`}>
                        <td>{SEX_LABEL[s]}</td>
                        <td className="num">{a}</td>
                        <td className="num">
                          {f2(c.median)} [{f2(c.lo)}, {f2(c.hi)}]
                        </td>
                        <td className="num">
                          {f2(m.median)} [{f2(m.lo)}, {f2(m.hi)}]
                        </td>
                      </tr>
                    );
                  }),
                )}
              </tbody>
            </table>
            <table style={{ marginTop: 16 }}>
              <thead>
                <tr>
                  <th>Jump-off</th>
                  {quoted.map((k) => (
                    <th key={k} className="num">
                      {modelLabel(k)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rp.jump_offs.map((y, i) => (
                  <tr key={y}>
                    <td>{y}</td>
                    {quoted.map((k) => (
                      <td key={k} className="num">
                        {rp.quotes[k][i].price == null ? `none (${pct(rp.quotes[k][i].failed, 0)} of paths fail)` : f2(rp.quotes[k][i].price!)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </TableView>
        </>
      )}
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
        The annuitant factor scales population death rates down, because people who buy annuities live longer. The interval carries parameter and
        process uncertainty within the chosen model, not the choice of model: see the model risk panel below.
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

const RUN_SHORT: Record<string, string> = {
  wpp: "WPP, CBD, 2023",
  wpp_cbd_2019: "WPP, CBD, 2019",
  wpp_rh_2019: "WPP, RH, 2019",
  statssa_scaled: "Stats SA, scaled",
  statssa: "Stats SA",
};

function Sources({ r }: { r: Research }) {
  const c = r.compare!;
  const [view, setView] = useState<"deaths" | "population">("deaths");
  const runs = c.runs;
  const at = (k: string, s: Sex) => find(runs.find((x) => x.key === k)![s].prices, 65, 0.04, 0.7);
  const has = (k: string) => runs.some((x) => x.key === k);
  const rows: Interval[] = SEXES.flatMap((s) =>
    runs.map((x) => {
      const p = find(x[s].prices, 65, 0.04, 0.7);
      return { key: `${s}${x.key}`, label: `${SEX_LABEL[s]} · ${RUN_SHORT[x.key] ?? x.key}${x.exploratory ? " †" : ""}`, color: COLOR[s], lo: p.lo, median: p.median, hi: p.hi, active: x.key === r.source };
    }),
  );
  const gap = (k: string, s: Sex) => at(k, s).median / at("wpp", s).median - 1;
  const t = view === "deaths" ? c.completeness : c.exposure;
  const series: Series[] = SEXES.map((s) => ({ key: s, label: SEX_LABEL[s], color: COLOR[s], xs: t.years, ys: t[s] }));
  return (
    <section className="panel" id="sources">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Model risk · price at 65, 4%, factor 0.7</p>
          <h2 className="serif">Choosing the model moves the price more than the interval admits</h2>
        </div>
      </div>
      <Legend items={SEXES.map((s) => ({ label: SEX_LABEL[s], color: COLOR[s] }))} />
      <IntervalChart label="Annuity price at 65 by data source and model, men and women" rows={rows} fmt={f2} groups={2} />
      <p className="note">
        The Stats SA run prices an annuity at 65 {pct(gap("statssa", "Male"), 0)} above the UN WPP run for men and {pct(gap("statssa", "Female"), 0)}{" "}
        for women. Each row changes one thing from the row above.
        {has("wpp_rh_2019") && has("wpp_cbd_2019")
          ? ` On WPP's own deaths, ending the fit in 2019 adds ${pct(gap("wpp_cbd_2019", "Male"), 0)} and ${pct(gap("wpp_cbd_2019", "Female"), 0)}, and switching to ${MODEL_NAMES.RH} from 2006 takes the gap to ${pct(gap("wpp_rh_2019", "Male"), 0)} and ${pct(gap("wpp_rh_2019", "Female"), 0)}. Swapping in registered deaths, scaled for under-registration, then gives ${pct(gap("statssa_scaled", "Male"), 0)} and ${pct(gap("statssa_scaled", "Female"), 0)}. Most of the gap is the model and its window, not the deaths data, and no single model's 95% interval is wide enough to show it. Rows marked † are exploratory, outside the protocol.`
          : ""}
      </p>

      <div className="panel-head" style={{ marginTop: 28 }}>
        <div>
          <p className="eyebrow">Two drifts, both making mortality look as if it improves faster</p>
          <h3 className="serif">{view === "deaths" ? "Registered deaths as a share of WPP's, ages 50 to 89" : "WPP population over Stats SA's, ages 50 to 79"}</h3>
        </div>
        <Segmented
          label="Check"
          value={view}
          onChange={setView}
          options={[
            { id: "deaths", label: "Deaths" },
            { id: "population", label: "Population" },
          ]}
        />
      </div>
      <Legend items={SEXES.map((s) => ({ label: SEX_LABEL[s], color: COLOR[s] }))} />
      <YearChart
        label={view === "deaths" ? "Registered deaths at 50 to 89 over WPP deaths by year and sex" : "WPP population at 50 to 79 over Stats SA P0302 by year and sex"}
        series={series}
        fmt={(v) => pct(v, 0)}
        height={260}
        notes={[{ x0: 2006, label: "Post-peak fit starts", short: "2006", row: 0, anchor: "end" }]}
      />
      <p className="note">
        {view === "deaths"
          ? "Registration peaked around 2003 to 2010 and fell after it. The post-peak fit starts at the top of that fall, so part of the improvement it sees is fewer deaths being registered. The sensitivity row scales each year's deaths back up to WPP's level."
          : "WPP counts fewer people aged 50 to 79 than Stats SA until 2016, then catches up by 2020. Rates on WPP's population therefore fall faster over 2016 to 2019 than they would on Stats SA's. This is reported, not corrected: Stats SA single-age estimates were not available."}
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Run</th>
              {SEXES.map((s) => (
                <th key={s} className="num">
                  {SEX_LABEL[s]}, 65
                </th>
              ))}
              {SEXES.map((s) => (
                <th key={s} className="num">
                  {SEX_LABEL[s]}, vs WPP
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map((x) => (
              <tr key={x.key} className={x.key === r.source ? "final" : undefined}>
                <td>
                  {x.label}
                  {x.exploratory && <span className="tag">Exploratory</span>}
                </td>
                {SEXES.map((s) => (
                  <td key={s} className="num">
                    {f2(at(x.key, s).median)} [{f2(at(x.key, s).lo)}, {f2(at(x.key, s).hi)}]
                  </td>
                ))}
                {SEXES.map((s) => (
                  <td key={s} className="num">
                    {x.key === "wpp" ? "base" : `${gap(x.key, s) >= 0 ? "+" : ""}${pct(gap(x.key, s))}`}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <table style={{ marginTop: 16 }}>
          <thead>
            <tr>
              <th>Year</th>
              {SEXES.map((s) => (
                <th key={s} className="num">
                  {SEX_LABEL[s]}, deaths registered
                </th>
              ))}
              {SEXES.map((s) => (
                <th key={s} className="num">
                  {SEX_LABEL[s]}, WPP / Stats SA population
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {c.completeness.years.map((y, i) => {
              const j = c.exposure.years.indexOf(y);
              return (
                <tr key={y}>
                  <td>{y}</td>
                  {SEXES.map((s) => (
                    <td key={s} className="num">
                      {pct(c.completeness[s][i])}
                    </td>
                  ))}
                  {SEXES.map((s) => (
                    <td key={s} className="num">
                      {j < 0 ? "n/a" : num(c.exposure[s][j], 3)}
                    </td>
                  ))}
                </tr>
              );
            })}
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
          <h2 className="serif">
            The annuitant assumption {swing * 100 >= m(0.7).width_pct ? "moves the price more than the model interval does" : "matters as much as the model interval"}
          </h2>
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
          {r.source === "statssa" ? (
            <p>
              <strong>A modelled population</strong>
              Deaths are Stats SA registrations, but the population under them is UN WPP's: Stats SA's single-age estimates could not be obtained.
              Both drift against each other over time; see the data panel above.
            </p>
          ) : (
            <p>
              <strong>Smoothed data</strong>
              These results run on UN WPP 2024, which are model estimates and smoother than registered deaths. Every fit here looks better than it
              will on raw data.
            </p>
          )}
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
          Statistics South Africa, Mortality and Causes of Death 1997 to 2022, unit records, distributed by DataFirst, University of Cape Town.
          United Nations, Population Division (2024), World Population Prospects 2024, CC BY 3.0 IGO: population for every year, and the deaths
          and life tables of the comparison run. Statistics South Africa, P0302 projections, for the population check.
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
