import { useState } from "react";
import type { Kind, Research, Rmse, Sex, V2, V3 } from "./api";
import { BarChart, IntervalChart, YearChart, type Band, type BarGroup, type Interval, type Points, type Series } from "./charts";
import { SEX_LABEL, millions, num, pct, thousands } from "./format";
import {
  ADJS, AGES, COLOR, CURVE_COLOR, KEYS, KINDS, KIND_LABEL, MODEL_NAMES, Legend, Metric, SEXES, Segmented, TableView, Verdict, WINDOW_START,
  bp, f1, f2, find, longDate, meanAbs, modelLabel, rand, rm, v2find,
} from "./ui";

export function History({ r }: { r: Research }) {
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
          <p className="eyebrow">South Africa, {h.years[0]} to {h.years[h.years.length - 1]}</p>
          <h2 className="serif">How long people live {measure === "e0" ? "from birth" : "after 65"}</h2>
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

export function FanPanel({ r }: { r: Research }) {
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
            Forecast · v1 mortality model, {sameModel ? MODEL_NAMES[name] : "chosen model by sex"}, fitted {WINDOW_START[window] ?? 1997} to {jump}
          </p>
          <h2 className="serif">How long 65-year-olds are expected to live, to {lastYear}</h2>
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

export function Backtest({ r }: { r: Research }) {
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


const RUN_SHORT: Record<string, string> = {
  wpp: "WPP, CBD, 2023",
  wpp_cbd_2019: "WPP, CBD, 2019",
  wpp_rh_2019: "WPP, RH, 2019",
  statssa_scaled: "Stats SA, scaled",
  statssa: "Stats SA",
};

export function Sources({ r }: { r: Research }) {
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

export function Sensitivity({ r }: { r: Research }) {
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
            These prices discount at a flat 2%, 4% or 6%. The quotes and the balance sheet use the fitted South African government bond curve instead.
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


export function CurvePanel({ v }: { v: V2 }) {
  const [kind, setKind] = useState<Kind>("ilb");
  const [view, setView] = useState<"zero" | "forwards">("zero");
  const c = v.curves[kind];
  const ys = view === "zero" ? c.zero : c.forwards;
  const series: Series[] = [
    { key: "LI", label: "LI zero curve", color: CURVE_COLOR.LI, xs: c.years, ys: ys.LI },
    { key: "NS", label: "Nelson-Siegel", color: CURVE_COLOR.NS, xs: c.years, ys: ys.NS, dash: true },
  ];
  const points: Points[] = view === "zero" ? [{ key: "bonds", label: "Clearing yield", color: "var(--foreground)", xs: c.bonds.map((b) => b.maturity), ys: c.bonds.map((b) => b.yield) }] : [];
  const fl = c.forwards.LI;
  const longest = Math.floor(c.longest);
  const tail = fl[fl.length - 1];
  return (
    <section className="panel" id="curve">
      <div className="panel-head">
        <div>
          <p className="eyebrow">
            {KIND_LABEL[kind]} bonds · auctions in the 91 days to {longDate(c.date)}
          </p>
          <h2 className="serif">{kind === "ilb" ? "The real curve is close to flat at about 4%" : "The nominal curve rises from about 8.5% to 10.5%"}</h2>
        </div>
        <Segmented label="Bonds" value={kind} onChange={setKind} options={KINDS.map((k) => ({ id: k, label: k === "ilb" ? "Real" : "Nominal" }))} />
      </div>
      <div className="controls">
        <div className="control">
          <span className="label">Rate</span>
          <Segmented
            label="Rate"
            value={view}
            onChange={setView}
            options={[
              { id: "zero", label: "Zero rates" },
              { id: "forwards", label: "Forward rates" },
            ]}
          />
        </div>
      </div>
      <Legend
        items={[
          { label: "LI zero curve (chosen)", color: CURVE_COLOR.LI },
          { label: "Nelson-Siegel", color: CURVE_COLOR.NS, kind: "dash" },
          ...(view === "zero" ? [{ label: "Bond clearing yields", color: "var(--foreground)", kind: "dot" as const }] : []),
        ]}
      />
      <YearChart
        label={`${KIND_LABEL[kind]} ${view === "zero" ? "zero rates" : "one-year forward rates"} by years from settlement, ${longDate(c.date)}`}
        series={series}
        points={points}
        notes={[{ x0: c.longest, label: `Longest bond, ${num(c.longest, 1)} years`, short: `${longest}y`, row: 0, anchor: "end" }]}
        fmt={(x) => pct(x, 2)}
        xFmt={(x) => `${x} years`}
        height={280}
      />
      <p className="note">
        {view === "zero"
          ? `Zero rates at semi-annual compounding, beside each bond's clearing yield at its final redemption. The LI zero curve reprices all ${c.bonds.length} bonds exactly; Nelson-Siegel is a smooth fit through them.`
          : `The rate for each single year ahead. The LI zero curve's forwards are constant between bonds and held flat beyond the longest, here at ${pct(tail, 2)}.`}{" "}
        {kind === "fixed"
          ? `Its forwards are lumpy: bonds that mature close together, with yields that differ, need large swings between them to price exactly. ${pct(Math.max(...fl), 2)} beyond ${longest} years against Nelson-Siegel's ${pct(c.forwards.NS[c.forwards.NS.length - 1], 2)}.`
          : "Real forwards stay between about 3.5% and 4.6% out to the longest bond."}
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Bond</th>
              <th className="num">Years to final redemption</th>
              <th className="num">Clearing yield</th>
            </tr>
          </thead>
          <tbody>
            {c.bonds.map((b) => (
              <tr key={b.bond}>
                <td className="mono">{b.bond}</td>
                <td className="num">{num(b.maturity, 1)}</td>
                <td className="num">{pct(b.yield, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <table style={{ marginTop: 16 }}>
          <thead>
            <tr>
              <th className="num">Year</th>
              <th className="num">LI zero</th>
              <th className="num">NS zero</th>
              <th className="num">LI forward</th>
              <th className="num">NS forward</th>
            </tr>
          </thead>
          <tbody>
            {c.years
              .filter((y) => y === 1 || y % 5 === 0)
              .map((y) => (
                <tr key={y}>
                  <td className="num">{y}</td>
                  <td className="num">{pct(c.zero.LI[y - 1], 2)}</td>
                  <td className="num">{pct(c.zero.NS[y - 1], 2)}</td>
                  <td className="num">{pct(c.forwards.LI[y - 1], 2)}</td>
                  <td className="num">{pct(c.forwards.NS[y - 1], 2)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </TableView>
    </section>
  );
}

export function CurveBacktest({ v }: { v: V2 }) {
  const [kind, setKind] = useState<Kind>("fixed");
  const t = v.validation.tests;
  const b = v.by_year[kind];
  const series: Series[] = (["LI", "NS", "B0"] as const).map((k) => ({
    key: k,
    label: k === "B0" ? "Last yield (B0)" : k === "LI" ? "LI (chosen)" : "Nelson-Siegel",
    color: CURVE_COLOR[k],
    xs: b.years,
    ys: b[k],
    dash: k === "B0",
  }));
  const va = v.validation.all;
  const gap = (k: Kind) => t[k].C1_rmse.B0 - t[k].C1_rmse.LI;
  const tests: { id: string; claim: string; verdicts: (boolean | null)[]; plain: string }[] = [
    {
      id: "C1",
      claim: "The curve beats each bond's own last yield",
      verdicts: KINDS.map((k) => t[k].C1),
      plain: `By ${bp(gap("fixed"))} on fixed-rate bonds and ${bp(gap("ilb"))} on inflation-linked. Treasury auctions the same few bonds week after week, so their last yields are recent and a curve adds little.`,
    },
    {
      id: "C2",
      claim: "Svensson beats Nelson-Siegel",
      verdicts: [null, t.fixed.C2 ?? null],
      plain: `${bp(t.fixed.C2_rmse!.NSS)} against ${bp(t.fixed.C2_rmse!.NS)} on fixed-rate bonds. Too few inflation-linked bonds are auctioned to fit Svensson.`,
    },
    {
      id: "C3",
      claim: "Root mean square error under 25bp",
      verdicts: KINDS.map((k) => t[k].C3),
      plain: `${bp(t.ilb.C3_rmse)} on inflation-linked bonds, ${bp(t.fixed.C3_rmse)} on fixed-rate. Without March to May 2020: ${bp(rm(v.validation.without_covid.curves.ilb, "LI")!)} and ${bp(rm(v.validation.without_covid.curves.fixed, "LI")!)}.`,
    },
  ];
  const row = (label: string, s: Record<string, Rmse | number>, cols: string[]) => (
    <tr key={label}>
      <td>{label}</td>
      <td className="num">{thousands(s.n as number)}</td>
      {cols.map((k) => (
        <td key={k} className="num">
          {rm(s, k) == null ? "" : num(rm(s, k)!, 1)}
        </td>
      ))}
    </tr>
  );
  const cols = ["LI", "NS", "NSS", "B0"];
  return (
    <section className="panel" id="curve-backtest">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Backtest · each auction predicted from the 91 days before it · chosen on 2010 to 2017, scored on 2018 to 2026</p>
          <h2 className="serif">The curve only just beats a bond's last yield</h2>
        </div>
      </div>
      <ul className="tests">
        {tests.map((x) => (
          <li key={x.id}>
            <div className="test-head">
              <span className="mono small">{x.id}</span>
              <strong>{x.claim}</strong>
              {x.verdicts.map((p, i) => (p == null ? <span key={i} className="verdict muted">{KIND_LABEL[KINDS[i]]} not tested</span> : <Verdict key={i} pass={p} who={KIND_LABEL[KINDS[i]]} />))}
            </div>
            <p className="plain" style={{ marginLeft: 34 }}>
              {x.plain}
            </p>
          </li>
        ))}
      </ul>

      <div className="panel-head" style={{ marginTop: 28 }}>
        <div>
          <p className="eyebrow">Error by year, on the auctions every method could price</p>
          <h3 className="serif">{KIND_LABEL[kind]} bonds: root mean square error of the predicted clearing yield</h3>
        </div>
        <Segmented label="Bonds" value={kind} onChange={setKind} options={(["fixed", "ilb"] as Kind[]).map((k) => ({ id: k, label: KIND_LABEL[k] }))} />
      </div>
      <Legend items={series.map((s) => ({ label: s.label, color: s.color, kind: s.dash ? ("dash" as const) : undefined }))} />
      <YearChart label={`${KIND_LABEL[kind]} bonds: prediction error by year and method`} series={series} fmt={(x) => `${num(x, 0)}bp`} height={260} notes={[{ x0: 2020, label: "Covid sell-off, March to May 2020", short: "Covid", row: 0, anchor: "start" }]} />
      <p className="note">
        The three lines move together: what is hard to predict is the market, not the curve. Nelson-Siegel would have been {bp(rm(va[kind], "LI")! - rm(va[kind], "NS")!)} better
        than LI over 2018 to 2026, but the design years preferred LI and the choice stands as made.
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Period and bonds</th>
              <th className="num">Auctions</th>
              {cols.map((k) => (
                <th key={k} className="num">
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {KINDS.flatMap((k) => [
              row(`Design, ${KIND_LABEL[k].toLowerCase()}`, v.design.all[k], cols),
              row(`Validation, ${KIND_LABEL[k].toLowerCase()}`, va[k], cols),
              row(`Validation without March to May 2020, ${KIND_LABEL[k].toLowerCase()}`, v.validation.without_covid.all[k], cols),
            ])}
          </tbody>
        </table>
        <p className="note">Root mean square error in basis points, on the auctions all methods could price. {thousands(v.data.usable)} clearing yields in all; {v.data.screened} screened out.</p>
      </TableView>
    </section>
  );
}

export function CurvePrices({ v, r }: { v: V2; r: Research }) {
  const [product, setProduct] = useState<"inflation-linked" | "level">("inflation-linked");
  const [adj, setAdj] = useState(0.7);
  const key = `${product} LI`;
  const rows: Interval[] = SEXES.flatMap((s) =>
    AGES.map((a) => {
      const p = v2find(v, s, a, adj)[key];
      return { key: `${s}${a}`, label: `${SEX_LABEL[s]}, ${a}`, color: COLOR[s], lo: p.lo, median: p.median, hi: p.hi, tag: `· ${pct(p.implied_flat_rate, 2)}` };
    }),
  );
  const ilb = (s: Sex) => v2find(v, s, 65, adj)["inflation-linked LI"];
  const flat4 = (s: Sex) => find(r.annuities[s].prices, 65, 0.04, adj).median;
  const ratio = (s: Sex, a: number) => v2find(v, s, a, adj)["level LI"].median / v2find(v, s, a, adj)["inflation-linked LI"].median;
  const ratios = SEXES.flatMap((s) => AGES.map((a) => ratio(s, a)));
  return (
    <section className="panel" id="curve-price">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Annuity prices on the bond curve · same mortality forecast, bought in 2026</p>
          <h2 className="serif">A flat 4% was close to what the market pays</h2>
        </div>
      </div>
      <section className="hero-figures" aria-label="Inflation-linked annuity at 65 on the real curve">
        {SEXES.map((s) => (
          <Metric key={s} value={`${ilb(s).median / flat4(s) - 1 >= 0 ? "+" : ""}${pct(ilb(s).median / flat4(s) - 1)}`} label={`${SEX_LABEL[s]}, 65, inflation-linked`} sub={`${f2(ilb(s).median)} on the real curve against ${f2(flat4(s))} at a flat 4%`} />
        ))}
      </section>
      <p className="note">
        At factor {adj.toFixed(1)}, the real curve is worth a flat {pct(ilb("Male").implied_flat_rate, 2)} for men and {pct(ilb("Female").implied_flat_rate, 2)} for women at 65, so the
        price moves by less than its own mortality interval.
      </p>
      <div className="controls" style={{ marginTop: 18 }}>
        <div className="control">
          <span className="label">Product</span>
          <Segmented
            label="Product"
            value={product}
            onChange={setProduct}
            options={[
              { id: "inflation-linked", label: "Inflation-linked, real curve" },
              { id: "level", label: "Level, nominal curve" },
            ]}
          />
        </div>
        <div className="control">
          <span className="label">Annuitant factor</span>
          <Segmented label="Annuitant factor" value={adj} onChange={setAdj} options={ADJS.map((x) => ({ id: x, label: x.toFixed(1) }))} />
        </div>
      </div>
      <p className="eyebrow" style={{ margin: "18px 0 8px" }}>
        {product === "inflation-linked" ? "Inflation-linked" : "Level"} annuity of 1 a year: median, 95% interval and the flat rate that gives the same price
      </p>
      <Legend items={SEXES.map((s) => ({ label: SEX_LABEL[s], color: COLOR[s] }))} />
      <IntervalChart label={`${product} annuity price on the bond curve by sex and age, factor ${adj.toFixed(1)}`} rows={rows} fmt={f2} groups={2} />
      <p className="note">
        {product === "level"
          ? `A level annuity costs ${pct(Math.min(...ratios), 0)} to ${pct(Math.max(...ratios), 0)} of an inflation-linked one: its payments are discounted at nominal yields near 10%, and the buyer carries the inflation.`
          : "Payments rise with inflation, so they are discounted on the real (inflation-linked) curve."}{" "}
        Intervals carry mortality uncertainty only; the curve is taken as known. On Nelson-Siegel instead, prices move by under 2%: see the table.
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Sex</th>
              <th className="num">Age</th>
              <th className="num">Flat 2% / 4% / 6%</th>
              <th className="num">Inflation-linked, LI</th>
              <th className="num">Implied</th>
              <th className="num">NS</th>
              <th className="num">Level, LI</th>
              <th className="num">Implied</th>
              <th className="num">NS</th>
            </tr>
          </thead>
          <tbody>
            {SEXES.flatMap((s) =>
              AGES.map((a) => {
                const p = v2find(v, s, a, adj);
                return (
                  <tr key={`${s}${a}`}>
                    <td>{SEX_LABEL[s]}</td>
                    <td className="num">{a}</td>
                    <td className="num">{["0.02", "0.04", "0.06"].map((k) => f2(p.flat[k])).join(" / ")}</td>
                    <td className="num">
                      {f2(p["inflation-linked LI"].median)} [{f2(p["inflation-linked LI"].lo)}, {f2(p["inflation-linked LI"].hi)}]
                    </td>
                    <td className="num">{pct(p["inflation-linked LI"].implied_flat_rate, 2)}</td>
                    <td className="num">{f2(p["inflation-linked NS"].median)}</td>
                    <td className="num">
                      {f2(p["level LI"].median)} [{f2(p["level LI"].lo)}, {f2(p["level LI"].hi)}]
                    </td>
                    <td className="num">{pct(p["level LI"].implied_flat_rate, 2)}</td>
                    <td className="num">{f2(p["level NS"].median)}</td>
                  </tr>
                );
              }),
            )}
          </tbody>
        </table>
      </TableView>
    </section>
  );
}

export function Matching({ v }: { v: V2 }) {
  const [sex, setSex] = useState<Sex>("Female");
  const m = v[sex].matching;
  const held = Object.entries(m.portfolio.holdings_per_100_nominal);
  const per = (x: number) => x * 1e4; // per R10,000 a year of income
  const groups: BarGroup[] = KEYS.map((k) => ({
    key: k,
    label: `${k} years`,
    values: [
      { key: "a", label: "Annuity", color: "var(--s1)", value: per(m.annuity.dv01[k]) },
      { key: "p", label: "Two-bond portfolio", color: "var(--s2)", value: per(m.portfolio.dv01[k]) },
    ],
  }));
  const long = per(m.annuity.dv01["30"]);
  const share = (m.annuity.dv01["20"] + m.annuity.dv01["30"]) / KEYS.reduce((a, k) => a + m.annuity.dv01[k], 0);
  return (
    <section className="panel" id="match">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Matching · inflation-linked annuity at 65, factor 0.7, real LI zero curve</p>
          <h2 className="serif">Two bonds match the duration, not the shape</h2>
        </div>
        <Segmented label="Sex" value={sex} onChange={setSex} options={SEXES.map((s) => ({ id: s, label: SEX_LABEL[s] }))} />
      </div>
      <div className="metrics">
        <Metric className="sans" value={f2(m.annuity.value)} label="Annuity value" sub="per 1 a year" />
        <Metric className="sans" value={`${num(m.annuity.duration, 1)} years`} label="Effective duration" sub="1bp parallel shift of the zero curve" />
        <Metric className="sans" value={held.map(([b]) => b).join(" + ")} label="Matching bonds" sub={held.map(([b]) => `${b} ${num(m.bonds[b].duration, 1)}y`).join(", ")} />
      </div>
      <p className="eyebrow" style={{ margin: "22px 0 8px" }}>
        Key-rate DV01: value lost for a 1bp rise at each key rate, rand per R10,000 a year of income
      </p>
      <Legend
        items={[
          { label: "Annuity", color: "var(--s1)" },
          { label: "Two-bond portfolio", color: "var(--s2)" },
        ]}
      />
      <BarChart label={`Key-rate DV01 of the ${SEX_LABEL[sex].toLowerCase()}'s annuity at 65 and of the matching portfolio`} groups={groups} fmt={(x) => num(x, 0)} />
      <p className="note">
        The two in-issue inflation-linked bonds whose durations bracket the annuity's, held to match its value and duration. A parallel move leaves the book matched.
        But {pct(share, 0)} of the annuity's rate risk sits at 20 and 30 years, where the portfolio holds {num(per(m.portfolio.dv01["30"]), 0)} against the annuity's{" "}
        {num(long, 0)} at 30 years. A move in long real rates alone hits one side of the book only. Closing it needs the longest bonds, I2050 and I2058.
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Key rate</th>
              <th className="num">Annuity</th>
              <th className="num">Portfolio</th>
              <th className="num">Mismatch</th>
            </tr>
          </thead>
          <tbody>
            {KEYS.map((k) => (
              <tr key={k}>
                <td>{k} years</td>
                <td className="num">{num(per(m.annuity.dv01[k]), 1)}</td>
                <td className="num">{num(per(m.portfolio.dv01[k]), 1)}</td>
                <td className="num">{num(per(m.portfolio.dv01[k] - m.annuity.dv01[k]), 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <table style={{ marginTop: 16 }}>
          <thead>
            <tr>
              <th>Bond</th>
              <th className="num">Price per 100</th>
              <th className="num">Duration</th>
              <th className="num">Nominal held per 1 a year</th>
            </tr>
          </thead>
          <tbody>
            {held.map(([b, n]) => (
              <tr key={b}>
                <td className="mono">{b}</td>
                <td className="num">{f2(m.bonds[b].value)}</td>
                <td className="num">{num(m.bonds[b].duration, 2)}</td>
                <td className="num">{f2(n * 100)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableView>
    </section>
  );
}

// Balance sheet --------------------------------------------------------------------------------------------------

export function Interest({ v }: { v: V3 }) {
  const m = v.main, u = v.unmatched, k = v.key_rate;
  const rows = [
    { key: "real" as const, label: "Real rates" },
    { key: "nominal" as const, label: "Nominal rates" },
    { key: "combined" as const, label: "Interest, diversified" },
  ];
  const groups: BarGroup[] = rows.map((x) => ({
    key: x.key,
    label: x.label,
    values: [
      { key: "m", label: "Two bonds, duration", color: "var(--s1)", value: m.interest[x.key] / 1e6 },
      ...(k ? [{ key: "k", label: "Key rates", color: "var(--s3)", value: k.interest[x.key] / 1e6 }] : []),
      { key: "u", label: "Unmatched", color: "var(--s2)", value: u.interest[x.key] / 1e6 },
    ],
  }));
  return (
    <section className="panel" id="interest">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Interest-rate risk · FSI 4.1 §5 · relative shocks to each curve, the other curve held</p>
          <h2 className="serif">{k ? "Matching on key rates, not duration, covers the SCR" : "Matching removes most of the interest charge, not all of it"}</h2>
        </div>
      </div>
      <div className="metrics">
        <Metric className="sans" value={f2(m.cover)} label="Cover, two bonds" sub={`SCR ${rand(m.scr)}, matched on duration`} />
        {k && <Metric className="sans" value={f2(k.cover)} label="Cover, key rates" sub={`SCR ${rand(k.scr)}, ${Object.keys(k.holdings.real).length} inflation-linked bonds incl. I2058`} />}
        <Metric className="sans" value={f2(u.cover)} label="Cover, unmatched" sub={`SCR ${rand(u.scr)}, everything in a 182-day bill`} />
      </div>
      <Legend
        items={[
          { label: "Two bonds, duration", color: "var(--s1)" },
          ...(k ? [{ label: "Key rates", color: "var(--s3)" }] : []),
          { label: "Unmatched", color: "var(--s2)" },
        ]}
      />
      <BarChart label="Interest-rate SCR, matched and unmatched, R million" groups={groups} fmt={(x) => num(x, 0)} />
      <p className="note">
        The bonds match each annuity type's value and duration, but SAM's shocks are relative and large. Real rates fall about 2.4 points at 10 years and 2.75 points beyond 30. The
        annuities pay out to age 120 and gain more from a fall that size than two bonds near 10 years do. Real rates rising gains {rand(-m.rate_losses["real up"])}, which
        confirms it. This is the 30-year gap in the matching panel above, at SAM's size of shock.
        {k &&
          ` Matching value and the 5, 10, 20 and 30-year key rates instead, with every bond of each kind and no shorting, cuts the interest charge to ${rand(k.interest.combined)} and lifts cover to ${f2(k.cover)} on the same capital. That run was added by a protocol amendment after the two-bond result was seen.`}
      </p>
      <TableView>
        <table>
          <thead>
            <tr>
              <th>Shock</th>
              <th className="num">Loss, two bonds (R million)</th>
              {k && <th className="num">Loss, key rates</th>}
            </tr>
          </thead>
          <tbody>
            {Object.entries(m.rate_losses).map(([key, x]) => (
              <tr key={key}>
                <td>{key[0].toUpperCase() + key.slice(1)}</td>
                <td className="num">{millions(x)}</td>
                {k && <td className="num">{millions(k.rate_losses[key])}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </TableView>
    </section>
  );
}

const SENS_LABEL: Record<string, string> = {
  "funeral 0.8": "Funeral mortality ×0.8",
  "funeral 1.2": "Funeral mortality ×1.2",
  "annuitant 0.6": "Annuitant factor 0.6",
  "annuitant 0.8": "Annuitant factor 0.8",
  "NS curves": "Nelson-Siegel curves",
};

export function BalanceSheet({ v }: { v: V3 }) {
  const m = v.main;
  const ilb = Object.keys(m.matching.real.bonds).join(", ");
  const fixed = Object.keys(m.matching.nominal.bonds).join(", ");
  const sheet: [string, number, string, number][] = [
    [`Inflation-linked bonds (${ilb})`, m.matching.real.liability.value, "BEL, annuities", m.bel.annuities],
    [`Fixed-rate bonds (${fixed})`, m.matching.nominal.liability.value, "BEL, funeral", m.bel.funeral],
    ["182-day bill", m.assets.bill, "Risk margin", m.risk_margin],
    ["", NaN, "Own funds (Tier 1)", m.own_funds],
  ];
  const sens = [["main", "Main basis", m] as const, ...Object.entries(v.sensitivities).map(([k, x]) => [k, SENS_LABEL[k] ?? k, x] as const)];
  return (
    <section className="panel" id="sheet">
      <div className="panel-head">
        <div>
          <p className="eyebrow">
            Balance sheet · {thousands(m.policies.annuities)} annuities and {thousands(m.policies.funeral)} funeral policies, invented · R million
          </p>
          <h2 className="serif">The funeral book is an asset. The annuities are almost everything else.</h2>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Assets</th>
              <th className="num">R million</th>
              <th>Liabilities and own funds</th>
              <th className="num">R million</th>
            </tr>
          </thead>
          <tbody>
            {sheet.map(([a, x, l, y]) => (
              <tr key={l}>
                <td>{a}</td>
                <td className="num">{Number.isNaN(x) ? "" : millions(x)}</td>
                <td>{l}</td>
                <td className="num">{millions(y)}</td>
              </tr>
            ))}
            <tr>
              <td>
                <strong>Total</strong>
              </td>
              <td className="num">
                <strong>{millions(m.assets.total)}</strong>
              </td>
              <td>
                <strong>Total</strong>
              </td>
              <td className="num">
                <strong>{millions(m.assets.total)}</strong>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="note">
        Expected funeral premiums ({rand(m.bel_parts.premiums)}) exceed claims ({rand(m.bel_parts.claims)}) plus expenses ({rand(m.bel_parts.fun_expenses)}), so the funeral
        BEL is negative. The risk margin is 6% a year of the life and operational SCR as the book runs off. Expense inflation is the 30-year breakeven, {pct(m.inflation, 2)}.
      </p>
      <p className="eyebrow" style={{ margin: "22px 0 8px" }}>
        Sensitivities
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Basis</th>
              <th className="num">BEL</th>
              <th className="num">Risk margin</th>
              <th className="num">SCR</th>
              <th className="num">Cover</th>
            </tr>
          </thead>
          <tbody>
            {sens.map(([k, label, x]) => (
              <tr key={k}>
                <td>{label}</td>
                <td className="num">{millions(x.bel.total)}</td>
                <td className="num">{millions(x.risk_margin)}</td>
                <td className="num">{millions(x.scr)}</td>
                <td className="num">{f2(x.cover)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">
        The annuitant factor moves the result most. The funeral basis barely matters: lighter funeral mortality makes the book more profitable, which raises the mass-lapse charge
        about as much as it lowers the mortality charge.
      </p>
    </section>
  );
}

