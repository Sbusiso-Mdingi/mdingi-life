import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./theme.css";
import { App } from "./App";

const params = new URLSearchParams(location.search);
const embedded = window.self !== window.top || params.has("embed");
if (embedded) document.body.classList.add("embedded");
const root = document.getElementById("root")!;

// Standalone follows the OS. Embedded stays light unless the host asks for ?theme=dark, so it never clashes with the page around it.
const asked = params.get("theme");
const dark = window.matchMedia("(prefers-color-scheme: dark)");
const applyTheme = () => {
  const theme = asked === "dark" || asked === "light" ? asked : !embedded && dark.matches ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
};
applyTheme();
dark.addEventListener("change", applyTheme);

// Let the host page size the iframe to the content.
if (embedded) {
  let last = 0;
  const post = (force = false) => {
    const height = Math.ceil(root.getBoundingClientRect().height);
    if (height === last && !force) return;
    last = height;
    window.parent.postMessage({ type: "preview:height", height }, "*");
  };
  if ("ResizeObserver" in window) new ResizeObserver(() => post()).observe(root);
  window.addEventListener("load", () => post());
  // The host may attach its listener after the first report, so it can ask again.
  window.addEventListener("message", (e) => e.data?.type === "preview:measure" && post(true));
  setInterval(() => post(), 1000);
}

createRoot(root).render(
  <StrictMode>
    <App embedded={embedded} />
  </StrictMode>,
);
