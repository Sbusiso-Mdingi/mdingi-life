"""Download National Treasury's bond auction results and bond schedules, and reduce them to two tables.

Source: National Treasury, Republic of South Africa, investor.treasury.gov.za, Debt Operations and Data
(Historical Results; Schedule of Domestic Debt). Used for non-commercial purposes with acknowledgement. The
spreadsheets and PDFs stay in data/raw/treasury and are git-ignored; the tidy extracts are kept:

- data/raw/treasury/bonds.csv: one row per bond and redemption date (coupon, coupon dates, share redeemed),
  from the March schedule of each year and the latest one. Bonds redeemed in instalments have several rows.
- data/raw/treasury/auctions.csv: one row per bond per auction (clearing yield, best and worst bid, amount).

The 2010-13 workbooks have one row per bond auction; later ones have a sheet per month and a column per bond
per auction day, found by row label because the layout shifts between years. Needs `pdftotext` (poppler).
"""
from __future__ import annotations

import re
import subprocess
import urllib.parse
import urllib.request

import pandas as pd

from mdingilife.data import RAW

TREASURY = RAW / "treasury"
BONDS, AUCTIONS = TREASURY / "bonds.csv", TREASURY / "auctions.csv"
BASE = "https://investor.treasury.gov.za/Debt%20Operations%20and%20Data/"
RESULTS = BASE + "Historical%20Results/"
SCHEDULES = BASE + "Schedule%20of%20Domestic%20Debt/"
KINDS = {"fixed": "Fixed-rate bonds", "ilb": "Inflation-linked bonds"}
ILB = {"R197", "R202", "R210", "R211", "R212"}  # inflation-linked bonds from before the I-prefix
ALIASES = {"R2025": "I2025", "R2050": "I2050", "I212": "R212"}  # labels the auction sheets get wrong
UA = {"User-Agent": "Mozilla/5.0"}
ROWS = {  # field: how its row label starts (lower case)
    "auction_date": "auction date",
    "settlement_date": "settlement date",
    "bond": "bonds auctioned",
    "terms": "bond coupon",
    "allocated": "total amount allocated",
    "clearing": "clearing yield",
    "best": "best bid",
    "worst": "worst bid",
}
LONG = {  # 2010-13 workbooks: field: header
    "bond": ("bond auctioned", "bond"),
    "coupon": ("bond coupon(%)", "coupon"),
    "auction_date": ("auction date", "issue date"),
    "settlement_date": ("settlement date",),
    "allocated": ("allocated amount (r'm)",),
    "clearing": ("clearing yield", "issue yield"),
}
LINE = re.compile(r"^\s*([A-Z]+\d+)[*/ ]*\s+([\d.]+)%\s+(\d{1,2}-\w{3}-\d{2})\s+.*?"
                  r"(\d{1,2}/\d{1,2}\s*&\s*\d{1,2}/\d{1,2})\s+(\d{1,2}-\w{3}-\d{2})\s")


def get(url: str, path) -> None:
    if not path.exists():
        print("downloading", path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read())


def listing(url: str, ext: str) -> list[str]:
    page = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode()
    return sorted(set(re.findall(rf'href="([^"]+\.{ext})"', page)))


def fetch() -> None:
    for kind, folder in KINDS.items():
        url = RESULTS + urllib.parse.quote(folder) + "/"
        for name in listing(url, "xlsx?"):
            get(url + urllib.parse.quote(name), TREASURY / kind / name)
    dated = {n: pd.to_datetime(n.split(" as at ")[1][:-4], errors="coerce") for n in listing(SCHEDULES, "pdf")}
    dated = {n: at for n, at in dated.items() if pd.notna(at)}  # a few names are misspelt; none is a March one
    latest = max(dated, key=dated.get)
    for name, at in dated.items():
        if (at.month == 3 and at.year >= 2011) or name == latest:
            get(SCHEDULES + urllib.parse.quote(name), TREASURY / "ref" / f"schedule-{at:%Y-%m}.pdf")


def bonds() -> pd.DataFrame:
    """Coupon, coupon dates and redemption dates by bond, from the schedules.

    A bond redeemed in instalments (R186, R2044, R2048, I2050) has a line per instalment under its own code in
    the older schedules; later schedules move instalments to neighbouring codes (R187, R188), which are never
    auctioned. So each code gets every redemption date ever listed under it, in equal shares.
    """
    rows = []
    for f in sorted((TREASURY / "ref").glob("*.pdf")):
        text = subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True, check=True).stdout
        for line in text.splitlines():
            if m := LINE.match(line):
                rows.append(dict(at=f.stem[-7:], code=m[1], coupon=float(m[2]), issue=pd.to_datetime(m[3], format="%d-%b-%y"),
                                 coupon_dates=re.sub(r"\s", "", m[4]),
                                 redemption=pd.to_datetime(m[5], format="%d-%b-%y")))
    d = pd.DataFrame(rows)
    d = d[d["code"].str.match(r"^(R\d{3,4}|I\d{4})$")]  # fixed-rate and inflation-linked; no floaters or zeros
    # Schedules disagree on small things (1.88% against 1.875%, the order of the coupon dates, the odd typo);
    # the latest schedule that lists a bond gives its terms.
    dm = lambda x: "{:02d}/{:02d}".format(*map(int, x.split("/")))
    d["coupon_dates"] = d["coupon_dates"].map(lambda c: "&".join(sorted(map(dm, c.split("&")), key=lambda x: x[3:] + x[:2])))
    latest = d.sort_values("at").groupby("code")[["coupon", "issue", "coupon_dates"]].last()
    d = d.drop(columns=["coupon", "issue", "coupon_dates"]).join(latest, on="code")
    d = d.drop_duplicates(["code", "redemption"]).rename(columns={"code": "bond"})
    d["kind"] = d["bond"].map(lambda b: "ilb" if b[0] == "I" or b in ILB else "fixed")
    d["share"] = 1 / d.groupby("bond")["redemption"].transform("size")
    return d[["bond", "kind", "coupon", "issue", "coupon_dates", "redemption", "share"]].sort_values(["bond", "redemption"])


def wide(s: pd.DataFrame) -> pd.DataFrame:
    """One month's sheet as one row per bond per auction day."""
    text = s.astype(str).apply(lambda c: c.str.strip().str.lower())
    at = [c for c in range(s.shape[1]) if text.iloc[:, c].str.startswith(ROWS["clearing"]).any()]
    if not at:
        return pd.DataFrame()
    label = text.iloc[:, at[0]]
    found = {k: label.index[label.str.startswith(v)] for k, v in ROWS.items()}
    if any(len(found[k]) == 0 for k in ("auction_date", "bond", "clearing")):
        return pd.DataFrame()
    d = pd.DataFrame({k: s.loc[i[0]].iloc[at[0] + 1:] for k, i in found.items() if len(i)})
    for k in ("auction_date", "settlement_date"):
        if k in d:
            d[k] = pd.to_datetime(d[k], errors="coerce", dayfirst=True).ffill()
    d["bond"] = d["bond"].astype(str).str.strip()
    terms = d.get("terms", pd.Series("", index=d.index)).astype(str).str.extract(r"([\d.]+)\s*%\s*[;:,]?\s*(\d{4})")
    d["coupon"], d["maturity_year"] = terms[0].astype(float), terms[1].astype(float)
    d["allocated"] = pd.to_numeric(d.get("allocated"), errors="coerce") / 1e6
    return d.drop(columns="terms", errors="ignore")


def long(s: pd.DataFrame) -> pd.DataFrame:
    """A 2010-13 workbook: a header row, then one row per bond auction. Amounts are already in R million."""
    head = s.index[s.iloc[:, 0].astype(str).str.strip().str.lower().isin(["bond auctioned", "bond"])][0]
    s = s.iloc[head + 1:].set_axis(s.loc[head].astype(str).str.strip().str.lower(), axis=1)
    d = pd.DataFrame({k: s[next(h for h in hs if h in s)] for k, hs in LONG.items() if any(h in s for h in hs)})
    code = pd.to_numeric(d["bond"], errors="coerce")
    d["bond"] = "R" + code.astype("Int64").astype(str)
    d["maturity_year"] = pd.to_datetime(s[next(h for h in ("redemption date", "maturity date") if h in s)],
                                        errors="coerce").dt.year
    for k in ("auction_date", "settlement_date"):
        d[k] = pd.to_datetime(d[k], errors="coerce")
    return d[code.notna()]


def auctions(ref: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for kind in KINDS:
        for path in sorted((TREASURY / kind).glob("*.xls*")):
            engine = "xlrd" if path.suffix == ".xls" else None
            for name, s in pd.read_excel(path, sheet_name=None, header=None, engine=engine).items():
                d = long(s) if "2010-13" in path.name else wide(s)
                if len(d):
                    parts.append(d.assign(source=kind, file=path.name, sheet=name))
    d = pd.concat(parts, ignore_index=True)
    for k in ("allocated", "clearing", "best", "worst", "coupon", "maturity_year"):
        d[k] = pd.to_numeric(d.get(k), errors="coerce")
    d["bond"] = d["bond"].astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    d["bond"] = d["bond"].where(~d["bond"].str.fullmatch(r"\d{3,4}"), "R" + d["bond"]).replace(ALIASES)
    # An inflation-linked workbook that labels a bond R20xx means I20xx (R2038 in 2012, before the fixed-rate R2038).
    old = (d["source"] == "ilb") & d["bond"].str.fullmatch(r"R\d{4}")
    d.loc[old, "bond"] = "I" + d.loc[old, "bond"].str[1:]
    d = d[d["bond"].str.fullmatch(r"[RI]\d{1,4}") & d["auction_date"].notna()]  # drops blank and summary columns
    # Most sheets of 2012-16, and single cells elsewhere, hold yields in cells formatted as percentages, which read
    # as fractions (0.0887 for 8.87%). No auction cleared under 0.25%, so a value under 0.25 is multiplied by 100.
    for k in ("clearing", "best", "worst"):
        d.loc[d[k].between(0, 0.25, inclusive="neither"), k] *= 100

    # The bond's terms come from the schedules. The sheets' own coupon and year labels are often copied from a
    # neighbouring column, so the code is trusted and a disagreement is only flagged.
    terms = ref.groupby("bond").agg(kind=("kind", "first"), ref_coupon=("coupon", "first"),
                                    ref_years=("redemption", lambda r: set(r.dt.year)))
    d = d.join(terms, on="bond")
    d["status"] = "ok"
    d.loc[d["kind"].isna(), "status"] = "not in schedules"
    year_ok = [y != y or (isinstance(ys, set) and y in ys) for y, ys in zip(d["maturity_year"], d["ref_years"])]
    wrong = (d["coupon"].notna() & ((d["coupon"] - d["ref_coupon"]).abs() > 0.01)) | ~pd.Series(year_ok, d.index)
    d["terms_flag"] = wrong & (d["status"] == "ok")
    d = d.drop_duplicates(["auction_date", "bond"]).sort_values(["auction_date", "kind", "bond"])
    cols = ["kind", "auction_date", "settlement_date", "bond", "clearing", "best", "worst", "allocated",
            "status", "terms_flag", "file", "sheet"]
    return d[cols]


def main() -> None:
    fetch()
    ref = bonds()
    ref.to_csv(BONDS, index=False, date_format="%Y-%m-%d")
    print(f"wrote {BONDS.relative_to(RAW.parents[1])}: {ref['bond'].nunique()} bonds, {len(ref)} redemption rows")
    a = auctions(ref)
    a.to_csv(AUCTIONS, index=False, date_format="%Y-%m-%d")
    print(f"wrote {AUCTIONS.relative_to(RAW.parents[1])}: {len(a):,} rows")
    print(a.groupby("status").size().to_string())
    print(a[a["status"] != "ok"].groupby(["status", "bond"]).size().to_string())
    ok = a[a["status"] == "ok"]
    print(ok.groupby([ok["auction_date"].dt.year, "kind"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
