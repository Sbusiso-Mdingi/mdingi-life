import { useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type RefObject } from "react";

const MAX_W = 760;
const NARROW = 520;

/** Charts draw in a 760-wide space and scale up on wide screens; on narrow ones they draw at their real width so text stays readable. */
function useWidth(ref: RefObject<Element | null>) {
  const [w, setW] = useState(MAX_W);
  useLayoutEffect(() => {
    const el = ref.current?.parentElement;
    if (!el) return;
    const set = () => setW(Math.max(300, Math.min(MAX_W, Math.round(el.getBoundingClientRect().width))));
    set();
    const ro = new ResizeObserver(set);
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

function scaleLinear(d0: number, d1: number, r0: number, r1: number) {
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  return (v: number) => r0 + (v - d0) * k;
}

/** Ticks spanning [min, max], with the first and last pushed out to round values so the axis is labelled at both ends. */
function niceTicks(min: number, max: number, count = 5) {
  const span = max - min || 1;
  const step0 = span / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0) ?? step0;
  return ticks(Math.floor(min / step) * step, Math.ceil(max / step) * step, count);
}

function ticks(min: number, max: number, count = 4) {
  const span = max - min || 1;
  const step0 = span / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0) ?? step0;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-12; v += step) out.push(+v.toFixed(10));
  return out;
}

export type Series = { key: string; label: string; color: string; xs: number[]; ys: (number | null)[]; dash?: boolean };
export type Band = { key: string; label: string; color: string; xs: number[]; lo: number[]; hi: number[] };
export type Points = { key: string; label: string; color: string; xs: number[]; ys: number[] };
export type Note = { x0: number; x1?: number; label: string; short?: string; row?: number; anchor?: "start" | "end" };

const at = (xs: number[], ys: (number | null)[], x: number) => {
  const i = xs.indexOf(x);
  return i < 0 ? null : ys[i];
};

/** Years along x, one value axis. Hover or arrow keys move a crosshair; the tooltip lists every series at that year. */
export function YearChart({
  label,
  series,
  bands = [],
  points = [],
  notes = [],
  fmt,
  xFmt = String,
  height = 300,
}: {
  label: string;
  series: Series[];
  bands?: Band[];
  points?: Points[];
  notes?: Note[];
  fmt: (v: number) => string;
  xFmt?: (x: number) => string;
  height?: number;
}) {
  const H = height;
  const rows = Math.max(0, ...notes.map((n) => (n.row ?? 0) + 1));
  const pad = { l: 44, r: 14, t: 12 + rows * 16, b: 28 };
  const [hover, setHover] = useState<number | null>(null);
  const ref = useRef<SVGSVGElement>(null);
  const W = useWidth(ref);
  const narrow = W < NARROW;
  const xsAll = [...series.flatMap((s) => s.xs), ...bands.flatMap((b) => b.xs), ...points.flatMap((p) => p.xs)];
  const x0 = Math.min(...xsAll);
  const x1 = Math.max(...xsAll);
  const vals = [
    ...series.flatMap((s) => s.ys.filter((v): v is number => v != null)),
    ...bands.flatMap((b) => [...b.lo, ...b.hi]),
    ...points.flatMap((p) => p.ys),
  ];
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const span = hi - lo || 1;
  const yt = niceTicks(lo - span * 0.02, hi + span * 0.02, 5);
  const ymin = Math.min(yt[0], lo);
  const ymax = Math.max(yt[yt.length - 1], hi);
  const x = scaleLinear(x0, x1, pad.l, W - pad.r);
  const y = scaleLinear(ymin, ymax, H - pad.b, pad.t);
  const xt = ticks(x0, x1, narrow ? 4 : 7).filter((t) => Number.isInteger(t));

  const path = (xs: number[], ys: (number | null)[]) => {
    let d = "";
    let pen = false;
    ys.forEach((v, i) => {
      if (v == null) return void (pen = false);
      d += `${pen ? "L" : "M"}${x(xs[i]).toFixed(1)} ${y(v).toFixed(1)}`;
      pen = true;
    });
    return d;
  };
  // Points with no neighbour on either side would vanish as a line, so they get a dot.
  const lonely = (s: Series) => s.ys.map((v, i) => v != null && s.ys[i - 1] == null && s.ys[i + 1] == null);
  const area = (b: Band) =>
    b.xs.map((t, i) => `${i ? "L" : "M"}${x(t).toFixed(1)} ${y(b.hi[i]).toFixed(1)}`).join("") +
    [...b.xs].reverse().map((t, j) => `L${x(t).toFixed(1)} ${y(b.lo[b.xs.length - 1 - j]).toFixed(1)}`).join("") +
    "Z";

  const onMove = (e: PointerEvent) => {
    const box = ref.current?.getBoundingClientRect();
    if (!box) return;
    const px = ((e.clientX - box.left) / box.width) * W;
    const t = Math.round(x0 + ((px - pad.l) / (W - pad.l - pad.r)) * (x1 - x0));
    setHover(t >= x0 && t <= x1 ? t : null);
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const step = e.key === "ArrowLeft" ? -1 : 1;
    setHover((h) => Math.min(x1, Math.max(x0, (h ?? (step > 0 ? x0 - 1 : x1 + 1)) + step)));
  };

  type Row = { key: string; color: string; text: string; value: string; kind: "line" | "dash" | "band" | "dot" };
  const tip: Row[] = [];
  if (hover != null) {
    for (const s of series) {
      const v = at(s.xs, s.ys, hover);
      if (v != null && s.label) tip.push({ key: s.key, color: s.color, text: s.label, value: fmt(v), kind: s.dash ? "dash" : "line" });
    }
    for (const p of points) {
      const v = at(p.xs, p.ys, hover);
      if (v != null) tip.push({ key: p.key, color: p.color, text: p.label, value: fmt(v), kind: "dot" });
    }
    for (const b of bands) {
      const i = b.xs.indexOf(hover);
      if (i >= 0 && b.hi[i] - b.lo[i] > 1e-9)
        tip.push({ key: b.key, color: b.color, text: b.label, value: `${fmt(b.lo[i])} to ${fmt(b.hi[i])}`, kind: "band" });
    }
  }
  const tipW = 230;
  const tipX = hover == null ? 0 : x(hover) + 12 + tipW > W ? x(hover) - 12 - tipW : x(hover) + 12;

  return (
    <svg
      ref={ref}
      className="chart"
      viewBox={`0 0 ${W} ${H}`}
      onPointerMove={onMove}
      onPointerLeave={() => setHover(null)}
      onKeyDown={onKey}
      onBlur={() => setHover(null)}
      tabIndex={0}
      role="img"
      aria-label={`${label}. Use the arrow keys to read values along the axis.`}
    >
      {notes
        .filter((n) => n.x1 != null)
        .map((n) => (
          <rect key={`s${n.label}`} x={x(n.x0)} y={pad.t} width={Math.max(2, x(n.x1!) - x(n.x0))} height={H - pad.b - pad.t} fill="var(--foreground)" opacity=".06" />
        ))}
      {yt.map((t) => (
        <g key={t}>
          <path d={`M${pad.l} ${y(t)}H${W - pad.r}`} stroke="var(--border)" />
          <text x={pad.l - 8} y={y(t) + 3} textAnchor="end">
            {fmt(t)}
          </text>
        </g>
      ))}
      {xt.map((t) => (
        <text key={t} x={x(t)} y={H - 8} textAnchor={x(t) > W - pad.r - 16 ? "end" : "middle"}>
          {t}
        </text>
      ))}
      {notes.map((n) => {
        const row = n.row ?? 0;
        const cx = n.x1 != null ? (n.anchor === "end" ? x(n.x0) : n.anchor === "start" ? x(n.x1) : (x(n.x0) + x(n.x1)) / 2) : x(n.x0);
        const ty = 10 + row * 16;
        const anchor = n.anchor ?? "middle";
        const dx = anchor === "end" ? -4 : anchor === "start" ? 4 : 0;
        return (
          <g key={`n${n.label}`}>
            {n.x1 == null && <path d={`M${x(n.x0)} ${ty + 4}V${H - pad.b}`} stroke="var(--border-strong)" />}
            {n.x1 != null && <path d={`M${cx} ${ty + 4}V${pad.t}`} stroke="var(--border-strong)" />}
            <text x={cx + dx} y={ty} textAnchor={anchor}>
              {narrow && n.short ? n.short : n.label}
            </text>
          </g>
        );
      })}
      {bands.map((b) => (
        <path key={b.key} d={area(b)} fill={b.color} opacity=".16" />
      ))}
      {series.map((s) => (
        <g key={s.key}>
          <path d={path(s.xs, s.ys)} fill="none" stroke={s.color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" strokeDasharray={s.dash ? "5 4" : undefined} />
          {lonely(s).map((on, i) =>
            on ? <circle key={i} cx={x(s.xs[i])} cy={y(s.ys[i]!)} r="4" fill={s.color} stroke="var(--background)" strokeWidth="2" /> : null,
          )}
        </g>
      ))}
      {points.map((p) =>
        p.xs.map((t, i) => <circle key={`${p.key}${t}`} cx={x(t)} cy={y(p.ys[i])} r="4.5" fill="var(--background)" stroke={p.color} strokeWidth="2" />),
      )}
      {hover != null && tip.length > 0 && (
        <g pointerEvents="none">
          <path d={`M${x(hover)} ${pad.t}V${H - pad.b}`} stroke="var(--foreground)" strokeOpacity=".4" />
          <g transform={`translate(${tipX} ${pad.t + 4})`}>
            <rect width={tipW} height={26 + 16 * tip.length} fill="var(--background)" stroke="var(--border-strong)" />
            <text x="10" y="17" style={{ fill: "var(--foreground)" }}>
              {xFmt(hover)}
            </text>
            {tip.map((r, k) => (
              <g key={r.key} transform={`translate(10 ${33 + 16 * k})`}>
                {r.kind === "dot" ? (
                  <circle cx="7" cy="-3.5" r="3.5" fill="none" stroke={r.color} strokeWidth="2" />
                ) : r.kind === "band" ? (
                  <rect x="0" y="-8" width="14" height="9" fill={r.color} opacity=".3" />
                ) : (
                  <path d="M0 -3.5H14" stroke={r.color} strokeWidth="2" strokeDasharray={r.kind === "dash" ? "4 3" : undefined} />
                )}
                <text x="22" y="0" className="tip-value">
                  {r.value}
                </text>
                <text x={tipW - 20} y="0" textAnchor="end">
                  {r.text}
                </text>
              </g>
            ))}
          </g>
        </g>
      )}
    </svg>
  );
}

export type Interval = { key: string; label: string; color: string; lo: number; median: number; hi: number; active?: boolean; tag?: string };

/** One row per interval on a shared value axis: the 95% range as a wash, the median as a dot, values written at the right. */
export function IntervalChart({ label, rows, fmt, groups }: { label: string; rows: Interval[]; fmt: (v: number) => string; groups?: number }) {
  const ref = useRef<SVGSVGElement>(null);
  const W = useWidth(ref);
  const narrow = W < NARROW;
  // Narrow: the values move under the row label instead of sitting at the right.
  const rowH = narrow ? 42 : 30;
  const gap = groups ? 12 : 0;
  const per = groups ? rows.length / groups : rows.length;
  const longest = Math.max(...rows.map((r) => r.label.length));
  const pad = narrow ? { l: 150, r: 14, t: 8, b: 30 } : { l: Math.max(80, 7.2 * longest + 28), r: 190, t: 8, b: 30 };
  const H = pad.t + pad.b + rows.length * rowH + (groups ? (groups - 1) * gap : 0);
  const [hover, setHover] = useState<string | null>(null);
  const lo = Math.min(...rows.map((r) => r.lo));
  const hi = Math.max(...rows.map((r) => r.hi));
  const xt = ticks(lo, hi, 5);
  const xmin = Math.min(xt[0], lo);
  const xmax = Math.max(xt[xt.length - 1], hi);
  const x = scaleLinear(xmin, xmax, pad.l, W - pad.r);
  const top = (i: number) => pad.t + i * rowH + (groups ? Math.floor(i / per) * gap : 0);
  return (
    <svg ref={ref} className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} onPointerLeave={() => setHover(null)}>
      {xt.map((t) => (
        <g key={t}>
          <path d={`M${x(t)} ${pad.t}V${H - pad.b}`} stroke="var(--border)" />
          <text x={x(t)} y={H - 10} textAnchor="middle">
            {fmt(t)}
          </text>
        </g>
      ))}
      {rows.map((r, i) => {
        const cy = top(i) + rowH / 2;
        const lit = r.active || hover === r.key;
        return (
          <g
            key={r.key}
            tabIndex={0}
            onPointerEnter={() => setHover(r.key)}
            onFocus={() => setHover(r.key)}
            onBlur={() => setHover(null)}
            aria-label={`${r.label}: median ${fmt(r.median)}, 95% interval ${fmt(r.lo)} to ${fmt(r.hi)}`}
          >
            <rect x="0" y={top(i)} width={W} height={rowH} fill={lit ? "var(--foreground)" : "transparent"} opacity={lit ? 0.05 : 1} />
            <text x={pad.l - 14} y={narrow ? cy - 4 : cy + 3.5} textAnchor="end" style={{ fontSize: 11, fill: lit ? "var(--foreground)" : undefined }}>
              {r.label}
            </text>
            <rect x={x(r.lo)} y={cy - 6} width={Math.max(2, x(r.hi) - x(r.lo))} height="12" rx="3" fill={r.color} opacity={lit ? 0.32 : 0.2} />
            <path d={`M${x(r.lo)} ${cy}H${x(r.hi)}`} stroke={r.color} strokeWidth="2" />
            <circle cx={x(r.median)} cy={cy} r="5" fill={r.color} stroke="var(--background)" strokeWidth="2" />
            <text
              x={narrow ? pad.l - 14 : W - pad.r + 16}
              y={narrow ? cy + 11 : cy + 3.5}
              textAnchor={narrow ? "end" : "start"}
              style={{ fontSize: narrow ? 10 : 11, fill: lit ? "var(--foreground)" : undefined }}
            >
              <tspan className={lit ? "tip-value" : undefined}>{fmt(r.median)}</tspan> [{fmt(r.lo)}, {fmt(r.hi)}]{r.tag ? ` ${r.tag}` : ""}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export type BarGroup = { key: string; label: string; values: { key: string; label: string; color: string; value: number }[] };

/** Grouped bars from a zero baseline, 4px rounded tops, 2px gaps. Hover or focus a group for its values. */
export function BarChart({ label, groups, fmt, height = 240 }: { label: string; groups: BarGroup[]; fmt: (v: number) => string; height?: number }) {
  const ref = useRef<SVGSVGElement>(null);
  const W = useWidth(ref);
  const H = height;
  const pad = { l: 44, r: 14, t: 12, b: 28 };
  const [hover, setHover] = useState<string | null>(null);
  const hi = Math.max(...groups.flatMap((g) => g.values.map((v) => v.value)), 0);
  const yt = niceTicks(0, hi, 4);
  const y = scaleLinear(0, Math.max(hi, yt[yt.length - 1]), H - pad.b, pad.t);
  const slot = (W - pad.l - pad.r) / groups.length;
  const per = groups[0]?.values.length ?? 1;
  const bw = Math.min(36, (slot * 0.6 - 2 * (per - 1)) / per);
  const bar = (x0: number, v: number) => {
    const top = y(v);
    const h = y(0) - top;
    const r = Math.min(4, h, bw / 2);
    return `M${x0} ${y(0)}V${top + r}Q${x0} ${top} ${x0 + r} ${top}H${x0 + bw - r}Q${x0 + bw} ${top} ${x0 + bw} ${top + r}V${y(0)}Z`;
  };
  const tipW = 200;
  return (
    <svg ref={ref} className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} onPointerLeave={() => setHover(null)}>
      {yt.map((t) => (
        <g key={t}>
          <path d={`M${pad.l} ${y(t)}H${W - pad.r}`} stroke="var(--border)" />
          <text x={pad.l - 8} y={y(t) + 3} textAnchor="end">
            {fmt(t)}
          </text>
        </g>
      ))}
      {groups.map((g, i) => {
        const cx = pad.l + slot * (i + 0.5);
        const x0 = cx - (per * bw + 2 * (per - 1)) / 2;
        const lit = hover === g.key;
        return (
          <g
            key={g.key}
            tabIndex={0}
            onPointerEnter={() => setHover(g.key)}
            onFocus={() => setHover(g.key)}
            onBlur={() => setHover(null)}
            aria-label={`${g.label}: ${g.values.map((v) => `${v.label} ${fmt(v.value)}`).join(", ")}`}
          >
            <rect x={cx - slot / 2} y={pad.t} width={slot} height={H - pad.b - pad.t} fill={lit ? "var(--foreground)" : "transparent"} opacity={lit ? 0.05 : 1} />
            {g.values.map((v, j) =>
              v.value > 0 ? (
                <path key={v.key} d={bar(x0 + j * (bw + 2), v.value)} fill={v.color} />
              ) : (
                <path key={v.key} d={`M${x0 + j * (bw + 2)} ${y(0) - 1}h${bw}`} stroke={v.color} strokeWidth="2" />
              ),
            )}
            <text x={cx} y={H - 8} textAnchor="middle">
              {g.label}
            </text>
          </g>
        );
      })}
      <path d={`M${pad.l} ${y(0)}H${W - pad.r}`} stroke="var(--border-strong)" />
      {hover != null &&
        (() => {
          const i = groups.findIndex((g) => g.key === hover);
          const g = groups[i];
          const cx = pad.l + slot * (i + 0.5);
          const tx = cx + slot / 2 + tipW > W ? cx - slot / 2 - tipW : cx + slot / 2;
          return (
            <g pointerEvents="none" transform={`translate(${tx} ${pad.t + 4})`}>
              <rect width={tipW} height={26 + 16 * g.values.length} fill="var(--background)" stroke="var(--border-strong)" />
              <text x="10" y="17" style={{ fill: "var(--foreground)" }}>
                {g.label}
              </text>
              {g.values.map((v, k) => (
                <g key={v.key} transform={`translate(10 ${33 + 16 * k})`}>
                  <rect x="0" y="-8" width="10" height="9" rx="2" fill={v.color} />
                  <text x="18" y="0" className="tip-value">
                    {fmt(v.value)}
                  </text>
                  <text x={tipW - 20} y="0" textAnchor="end">
                    {v.label}
                  </text>
                </g>
              ))}
            </g>
          );
        })()}
    </svg>
  );
}
