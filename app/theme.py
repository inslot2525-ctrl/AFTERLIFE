"""Machine Morgue: the design system shared by Shelf's pages.

AFTERLIFE runs a forensic lab for dead code: a Coroner writes death
certificates, a vigil listens for knocks, the Medium explains resurrections.
The pages read like that lab's case files. Graphite instrument panels on a
blueprint grid, cut corners and corner brackets, case numbers and barcodes,
an angular robotic display face and a monospace for everything measured.

Colour is signal, never decoration:

    hazard    yellow   live, the vigil, attention
    scan      cyan     data, links, instruments
    specimen  green    measured savings, a feature in use
    defib     magenta  resurrection, policy protection
    alarm     red      failures and rollbacks

Plain CSS in the page, no build step. One small script reveals panels as
they scroll in and does nothing when the reader prefers reduced motion.
"""

FONTS = (
    "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
    "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
    "family=Chakra+Petch:ital,wght@0,400;0,500;0,600;0,700;1,500&family=IBM+Plex+Mono:wght@400;500;600&display=swap'>"
)

# A toe tag with a hazard-yellow eyelet: the lab's mark in the browser tab.
FAVICON = (
    "<link rel='icon' href=\"data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='6' fill='%230b0d10'/%3E"
    "%3Cpath d='M10 6h14v20H8V8z' fill='%23d9dee6'/%3E"
    "%3Ccircle cx='12.5' cy='10.5' r='2' fill='%23ffd23f'/%3E"
    "%3Crect x='11' y='16' width='10' height='2' fill='%230b0d10'/%3E"
    "%3Crect x='11' y='20' width='7' height='2' fill='%230b0d10'/%3E%3C/svg%3E\">"
)

BASE = r"""
:root {
  color-scheme: dark;
  --bg: #0b0d10; --panel: #12151a; --panel-hi: #181c22; --steel: #1f242c;
  --line: #262c35; --line-hi: #3a424e; --grid: rgba(120, 160, 200, 0.045);
  --ink: #dfe4ea; --quiet: #8c96a4; --faint: #545d6a;
  --hazard: #ffd23f; --hazard-soft: rgba(255, 210, 63, 0.12);
  --scan: #5fd8ff; --scan-soft: rgba(95, 216, 255, 0.1);
  --specimen: #6ff2a6; --specimen-soft: rgba(111, 242, 166, 0.1);
  --defib: #ff4f9a; --defib-soft: rgba(255, 79, 154, 0.12);
  --alarm: #ff5a4a; --alarm-soft: rgba(255, 90, 74, 0.12);
  /* names older components still use */
  --accent: var(--scan); --good: var(--specimen); --warn: var(--hazard); --card: var(--panel); --stone: var(--steel);
  --display: "Chakra Petch", "Eurostile", "Bank Gothic", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Consolas, monospace;
  --cut: 14px;
  --ease: cubic-bezier(.2, .8, .1, 1);
}
* { box-sizing: border-box; }
html { background: var(--bg); scroll-behavior: smooth; overflow-x: clip; }
body { margin: 0; min-height: 100vh; overflow-x: clip; color: var(--ink);
  font: 400 14px/1.65 var(--mono); -webkit-font-smoothing: antialiased;
  background:
    linear-gradient(var(--grid) 1px, transparent 1px) 0 0 / 32px 32px,
    linear-gradient(90deg, var(--grid) 1px, transparent 1px) 0 0 / 32px 32px,
    radial-gradient(900px 500px at 85% -10%, rgba(95, 216, 255, 0.07), transparent 70%),
    var(--bg); }
::selection { background: var(--hazard); color: var(--bg); }
main { max-width: 1160px; margin: 0 auto; padding: 0 28px 96px; }
a { color: var(--scan); text-decoration: none; transition: color .15s; }
a:hover { color: var(--hazard); }
code, .mono { font-family: var(--mono); font-size: 0.92em; }
code { color: var(--scan); background: var(--scan-soft); padding: 1px 6px; }
b, strong { font-weight: 600; }

/* --- the lab's chrome: cut-corner panels with brackets -------------------- */
.panel { position: relative; background: var(--panel); border: 1px solid var(--line);
  clip-path: polygon(0 0, calc(100% - var(--cut)) 0, 100% var(--cut), 100% 100%, var(--cut) 100%, 0 calc(100% - var(--cut))); }
.brackets { position: relative; }
.brackets::before, .brackets::after { content: ""; position: absolute; width: 14px; height: 14px; pointer-events: none;
  border-color: var(--line-hi); border-style: solid; }
.brackets::before { top: -1px; left: -1px; border-width: 1px 0 0 1px; }
.brackets::after { bottom: -1px; right: -1px; border-width: 0 1px 1px 0; }

/* --- navigation: the lab's status bar ------------------------------------ */
nav { position: sticky; top: 0; z-index: 50; display: flex; align-items: center; gap: 4px;
  margin: 0 calc(50% - 50vw); padding: 0 max(28px, calc(50vw - 552px));
  height: 56px; background: rgba(11, 13, 16, 0.86); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line); font: 500 12px/1 var(--display); letter-spacing: 0.12em; text-transform: uppercase; }
nav .brand { display: inline-flex; align-items: center; gap: 12px; margin-right: auto; color: var(--ink);
  font: 700 15px/1 var(--display); letter-spacing: 0.22em; }
nav .brand i { display: inline-block; width: 10px; height: 10px; background: var(--hazard);
  clip-path: polygon(50% 0, 100% 100%, 0 100%); }
nav .brand small { font: 400 11px/1 var(--mono); letter-spacing: 0.08em; color: var(--faint); text-transform: none; }
nav a:not(.brand) { color: var(--quiet); padding: 9px 14px; border: 1px solid transparent; }
nav a:not(.brand):hover { color: var(--ink); border-color: var(--line); }
nav a[aria-current] { color: var(--bg); background: var(--ink); }
nav .watch { margin-left: 14px; display: inline-flex; align-items: center; gap: 8px; padding: 7px 12px;
  border: 1px solid var(--specimen-soft); color: var(--specimen); font: 500 11px/1 var(--mono); letter-spacing: 0.1em; }
nav .watch b { width: 7px; height: 7px; border-radius: 50%; background: var(--specimen); box-shadow: 0 0 10px var(--specimen);
  animation: blink 1.6s steps(2, start) infinite; font-size: 0; }
@media (max-width: 720px) { nav .brand small, nav .watch { display: none; } }

/* --- case-file hero ------------------------------------------------------ */
.hero { position: relative; padding: 72px 0 52px; }
.case { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 22px; margin-bottom: 34px;
  font: 500 11px/1 var(--mono); letter-spacing: 0.14em; text-transform: uppercase; color: var(--quiet); }
.case .id { color: var(--bg); background: var(--hazard); padding: 6px 10px; font-weight: 600; }
.case .sep { flex: 1 1 60px; height: 1px; background: repeating-linear-gradient(90deg, var(--line-hi) 0 6px, transparent 6px 10px); }
.case .barcode { width: 120px; height: 22px; opacity: .8;
  background: repeating-linear-gradient(90deg, var(--ink) 0 2px, transparent 2px 4px, var(--ink) 4px 5px, transparent 5px 8px,
    var(--ink) 8px 11px, transparent 11px 12px, var(--ink) 12px 13px, transparent 13px 16px); }
.eyebrow { font: 500 12px/1 var(--display); letter-spacing: 0.3em; text-transform: uppercase; color: var(--scan); margin-bottom: 14px; }
h1 { margin: 0; max-width: 15ch; font: 700 clamp(44px, 8vw, 104px)/1.04 var(--display); letter-spacing: -0.01em;
  text-transform: uppercase; }
h1 em { font-style: normal; color: var(--bg); background: var(--hazard); padding: 0 0.1em; line-height: 1.04; box-decoration-break: clone;
  -webkit-box-decoration-break: clone; }
.lead { max-width: 640px; margin: 30px 0 0; color: var(--quiet); font-size: 14.5px; line-height: 1.75; }
.lead em { font-style: normal; color: var(--ink); border-bottom: 1px solid var(--hazard); }

/* --- section headings: §NN // TITLE ------------------------------------- */
h2 { display: flex; align-items: center; gap: 16px; margin: 104px 0 8px; scroll-margin-top: 80px;
  font: 600 clamp(26px, 3.2vw, 38px)/1 var(--display); letter-spacing: 0.02em; text-transform: uppercase; }
h2::before { content: "\00a7" attr(data-index); font: 500 12px/1 var(--mono); letter-spacing: 0.1em; color: var(--bg);
  background: var(--scan); padding: 6px 8px; }
h2:not([data-index])::before { display: none; }
h2::after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, var(--line-hi), transparent); }
h2 .count { order: 3; font: 500 12px/1 var(--mono); color: var(--hazard); border: 1px solid var(--hazard-soft); padding: 6px 9px; }
h2 + .lead { margin: 0 0 26px; font-size: 13.5px; }

/* --- lab log tables ------------------------------------------------------- */
.scroll { overflow-x: auto; border: 1px solid var(--line); background: var(--panel); }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; counter-reset: row; }
th { padding: 12px 16px; text-align: left; white-space: nowrap; background: var(--panel-hi); border-bottom: 1px solid var(--line-hi);
  font: 600 10.5px/1 var(--display); letter-spacing: 0.2em; text-transform: uppercase; color: var(--quiet); }
th:first-child::before { content: "#"; display: inline-block; width: 34px; color: var(--faint); }
td { padding: 15px 16px; border-top: 1px solid var(--line); vertical-align: top; color: var(--quiet); }
tr:not(:first-child) td:first-child::before { counter-increment: row; content: counter(row, decimal-leading-zero);
  display: inline-block; width: 34px; color: var(--faint); font-size: 11px; }
td b { color: var(--ink); font: 600 15px/1.3 var(--display); letter-spacing: 0.04em; }
td .mono { color: var(--scan); }
tr:hover td { background: rgba(95, 216, 255, 0.035); }
th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; color: var(--ink); }
.pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 9px; white-space: nowrap;
  font: 600 10.5px/1 var(--display); letter-spacing: 0.18em; text-transform: uppercase; color: var(--quiet);
  border: 1px solid currentColor; }
.pill::before { content: "["; } .pill::after { content: "]"; }
.pill.alive, .pill.read { color: var(--specimen); }
.pill.candidate, .pill.reading { color: var(--hazard); background: var(--hazard-soft); }
.pill.protected { color: var(--defib); }
.pill.quiet, .pill.to-read { color: var(--faint); }
.empty { color: var(--faint); font-size: 13px; margin: 14px 0; padding: 18px; border: 1px dashed var(--line); }
.empty::before { content: "NO RECORD // "; color: var(--quiet); }

footer { margin-top: 120px; padding-top: 22px; border-top: 1px solid var(--line-hi); display: flex; flex-wrap: wrap;
  justify-content: space-between; gap: 18px; color: var(--faint); font-size: 12px; }
footer .epitaph { font: 600 13px/1 var(--display); letter-spacing: 0.24em; text-transform: uppercase; color: var(--quiet); }
footer .epitaph::before { content: "\25A0  "; color: var(--hazard); }

/* --- motion: instruments, not decoration -------------------------------- */
@keyframes blink { to { visibility: hidden; } }
@keyframes scanline { from { transform: translateX(-100%); } to { transform: translateX(400%); } }
@keyframes boot { from { opacity: 0; transform: translateY(10px); clip-path: inset(0 0 100% 0); }
  to { opacity: 1; transform: none; clip-path: inset(0 0 0 0); } }
.hero > * { animation: boot .9s var(--ease) both; }
.hero > *:nth-child(2) { animation-delay: .08s; } .hero > *:nth-child(3) { animation-delay: .16s; }
.hero > *:nth-child(4) { animation-delay: .26s; }
.reveal { opacity: 0; transform: translateY(14px); transition: opacity .7s var(--ease), transform .7s var(--ease); }
.reveal.seen { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .reveal { opacity: 1; transform: none; }
}
"""

# Reveals panels as they scroll into view; content stays visible without JS.
REVEAL_SCRIPT = """<script>
(function () {
  if (!('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('seen'); io.unobserve(e.target); } });
  }, { rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('[data-reveal]').forEach(function (el) { el.classList.add('reveal'); io.observe(el); });
})();
</script>"""


def head(title: str, style: str) -> str:
    """Everything up to and including <body>, the same on every page."""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<meta name='theme-color' content='#0b0d10'>"
        f"<title>{title}</title>{FAVICON}{FONTS}<style>{BASE}{style}</style></head><body>"
    )


def case_header(case_id: str, label: str) -> str:
    """The strip above a hero: case number, label, a rule and a barcode."""
    return (f"<div class='case'><span class='id'>{case_id}</span><span>{label}</span>"
            "<span class='sep'></span><span class='barcode' aria-hidden='true'></span></div>")
