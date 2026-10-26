import { useEffect, useState } from "react";
import { api, type Research } from "./api";
import { Built, Capital, Customers, Future, Investments, Overview, Quote, type Tab } from "./pages";
import { REPO } from "./ui";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "quote", label: "Pricing" },
  { id: "customers", label: "Customers" },
  { id: "investments", label: "Investments" },
  { id: "capital", label: "Capital" },
  { id: "future", label: "Next five years" },
  { id: "built", label: "Methods" },
];
const fromHash = (): Tab => {
  const h = location.hash.slice(1) as Tab;
  return TABS.some((t) => t.id === h) ? h : "overview";
};

function Logo() {
  return (
    <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="var(--primary)" />
      <path d="M8 22V11l8 7 8-7v11" fill="none" stroke="var(--primary-foreground)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function App({ embedded }: { embedded: boolean }) {
  const [research, setResearch] = useState<Research | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>(fromHash);

  useEffect(() => {
    api.research().then(setResearch, (e) => setError(String(e)));
    const sync = () => setTab(fromHash());
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  const go = (t: Tab) => {
    history.replaceState(null, "", t === "overview" ? location.pathname + location.search : `#${t}`);
    setTab(t);
    if (!embedded) window.scrollTo({ top: 0 });
  };

  const ready = research?.v2 && research.v3?.book;
  return (
    <div className="site">
      <header className="topbar">
        <div className="topbar-inner">
          <button className="brand" onClick={() => go("overview")} aria-label="Mdingi Life, overview">
            <Logo />
            <span>Mdingi</span> Life
          </button>
          <nav className="nav" role="tablist" aria-label="Sections">
            {TABS.map((t) => (
              <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => go(t.id)}>
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="page" role="tabpanel" aria-label={TABS.find((t) => t.id === tab)!.label}>
        {error && <div className="loading">Could not load Mdingi Life: {error}</div>}
        {!error && !research && <div className="loading">Opening the books…</div>}
        {research && !ready && <div className="loading">The results are incomplete: run the export again.</div>}
        {research && ready && (
          <>
            {tab === "overview" && <Overview r={research} go={go} />}
            {tab === "quote" && <Quote r={research} />}
            {tab === "customers" && <Customers r={research} />}
            {tab === "investments" && <Investments r={research} />}
            {tab === "capital" && <Capital r={research} />}
            {tab === "future" && (research.v4 ? <Future r={research} /> : <div className="loading">The five-year projection has not been run yet.</div>)}
            {tab === "built" && <Built r={research} />}
          </>
        )}
      </main>
      <footer className="footer">
        Mdingi Life is fictional and sells nothing. The data and the regulator's rules are real; the customers are invented. A portfolio project by Sbusiso Mdingi
        {embedded ? "." : (
          <>
            {" "}
            ·{" "}
            <a href={REPO} target="_blank" rel="noreferrer">
              Code on GitHub
            </a>
          </>
        )}
      </footer>
    </div>
  );
}
