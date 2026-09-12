/* Measure whether a page settles into an idle state, and what it does when it does not.
 *
 * The observation under investigation was made through a browser extension, which is a
 * lot of machinery between the question and the answer. This asks the underlying
 * question directly through the DevTools protocol: after load, is the main thread busy,
 * is the network quiet, are frames still being scheduled, and can a script be evaluated
 * promptly?
 *
 *   node tools/measure_idle.mjs <url> [label] [idleSeconds]
 */
import puppeteer from "puppeteer-core";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const url = process.argv[2];
const label = process.argv[3] ?? url;
const IDLE_MS = Number(process.argv[4] ?? 10) * 1000;

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();

// Instrument BEFORE any page script runs, so nothing is missed.
await page.evaluateOnNewDocument(() => {
  window.__probe = { raf: 0, timeouts: 0, intervals: 0, sockets: 0, rafActive: 0 };
  const raf = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (cb) => {
    window.__probe.raf++;
    window.__probe.rafActive++;
    return raf((t) => { window.__probe.rafActive--; return cb(t); });
  };
  const si = window.setInterval.bind(window);
  window.setInterval = (...a) => { window.__probe.intervals++; return si(...a); };
  const st = window.setTimeout.bind(window);
  window.setTimeout = (...a) => { window.__probe.timeouts++; return st(...a); };
  const WS = window.WebSocket;
  window.WebSocket = function (...a) { window.__probe.sockets++; return new WS(...a); };
  window.WebSocket.prototype = WS.prototype;
});

const requests = [];
page.on("request", (r) => requests.push({ t: Date.now(), url: r.url(), type: r.resourceType() }));

const t0 = Date.now();
await page.goto(url, { waitUntil: "load", timeout: 30000 });
const loadMs = Date.now() - t0;
const duringLoad = requests.length;

const cdp = await page.createCDPSession();
await cdp.send("Performance.enable");
const metricsOf = async () =>
  Object.fromEntries((await cdp.send("Performance.getMetrics")).metrics.map((m) => [m.name, m.value]));

// Does the page report network idle at all? Resolve either way, never hang.
const networkIdle = await Promise.race([
  page.waitForNetworkIdle({ idleTime: 1000, timeout: 8000 }).then(() => true).catch(() => false),
  new Promise((r) => setTimeout(() => r(false), 9000)),
]);

const before = await metricsOf();
const reqBefore = requests.length;
const probeBefore = await page.evaluate(() => ({ ...window.__probe }));

await new Promise((r) => setTimeout(r, IDLE_MS));

// The key responsiveness measurement: how long a trivial evaluate takes to come back
// while the page is supposedly idle.
const evalStart = Date.now();
const readyState = await Promise.race([
  page.evaluate(() => document.readyState),
  new Promise((r) => setTimeout(() => r("TIMED OUT"), 10000)),
]);
const evalMs = Date.now() - evalStart;

const after = await metricsOf();
const probeAfter = await page.evaluate(() => ({ ...window.__probe }));
const reqAfter = requests.length;

const d = (k) => +(after[k] - before[k]).toFixed(4);
const idleSec = IDLE_MS / 1000;
const idleRequests = requests.slice(reqBefore).filter((r) => r.type !== "websocket");

console.log(`\n========== ${label} ==========`);
console.log(`url                       ${url}`);
console.log(`load event                ${loadMs} ms       readyState "${readyState}"`);
console.log(`reached network idle      ${networkIdle}`);
console.log(`evaluate() round trip     ${evalMs} ms   <- "page is busy" would show here`);
console.log(`--- over ${idleSec}s of supposed idle ---`);
console.log(`main-thread task time     ${d("TaskDuration")} s  (${((d("TaskDuration") / idleSec) * 100).toFixed(2)}% of wall clock)`);
console.log(`script time               ${d("ScriptDuration")} s`);
console.log(`layout time               ${d("LayoutDuration")} s`);
console.log(`recalc style              ${d("RecalcStyleDuration")} s`);
console.log(`layout count              ${d("LayoutCount")}`);
console.log(`style recalc count        ${d("RecalcStyleCount")}`);
console.log(`requests (non-websocket)  ${idleRequests.length}`);
idleRequests.slice(0, 8).forEach((r) => console.log(`    ${r.type.padEnd(10)} ${r.url.slice(0, 96)}`));
console.log(`rAF callbacks scheduled   ${probeAfter.raf - probeBefore.raf}  (still pending: ${probeAfter.rafActive})`);
console.log(`setInterval calls         ${probeAfter.intervals - probeBefore.intervals}`);
console.log(`setTimeout calls          ${probeAfter.timeouts - probeBefore.timeouts}`);
console.log(`WebSockets opened (total) ${probeAfter.sockets}`);
console.log(`requests during load      ${duringLoad}`);

await browser.close();
