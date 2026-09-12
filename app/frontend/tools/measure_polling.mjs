/* Drive the real Run -> Results flow and count polling requests at each stage.
 *
 * The Overview page is static, so a polling defect cannot live there. The Run page is
 * where one would actually live: it opens a setInterval against the backend. The three
 * questions that matter are whether that interval stops when the job finishes, when the
 * user navigates away mid-job, and when the backend stops answering.
 *
 *   node tools/measure_polling.mjs <baseUrl> <apiUrl> [label]
 */
import fs from "node:fs";
import puppeteer from "puppeteer-core";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = process.argv[2] ?? "http://127.0.0.1:5173";
const API = process.argv[3] ?? "http://127.0.0.1:8000";
const LABEL = process.argv[4] ?? BASE;
const CSV = "app/backend/sample_data/02_clean_no_injected_fault.csv";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- seed a submission through the API, exactly as the Upload page would ------
const fd = new FormData();
fd.append("predictions", new Blob([fs.readFileSync(`../../${CSV}`)]), "sample.csv");
const sub = await (await fetch(`${API}/api/submissions`, { method: "POST", body: fd })).json();
console.log(`\n========== ${LABEL} ==========`);
console.log(`seeded submission ${sub.id} (${sub.n_rows} rows)`);

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();
// Seed the session ONLY if the page has not already got one. Overwriting it on every
// navigation wiped the runId that the resume-on-return path reads, and made the app
// look as though it had failed to resume when it was the probe destroying the state.
await page.evaluateOnNewDocument((id) => {
  const KEY = "hemosight-audit-session";
  if (!localStorage.getItem(KEY)) {
    localStorage.setItem(KEY, JSON.stringify({ submissionId: id }));
  }
}, sub.id);

const polls = [];
page.on("request", (r) => {
  if (/\/api\/runs\//.test(r.url())) polls.push(Date.now());
});
const failures = [];
page.on("pageerror", (e) => failures.push(String(e)));
page.on("requestfailed", (r) => failures.push(`FAILED ${r.url()}`));
page.on("response", (r) => { if (r.status() === 404) failures.push(`404 ${r.url()}`); });
page.on("console", (m) => { if (m.type() === "error") failures.push(m.text()); });

const since = (t) => polls.filter((p) => p > t).length;

// --- start a run through the UI ----------------------------------------------
await page.goto(`${BASE}/run`, { waitUntil: "networkidle2", timeout: 30000 });

// Only the permutation check, with enough permutations to keep the job alive.
await page.evaluate(() => {
  document.querySelectorAll('input[type="checkbox"]').forEach((c) => {
    if (c.checked) c.click();
  });
});
const boxes = await page.$$('input[type="checkbox"]');
const labels = await page.evaluate(() =>
  [...document.querySelectorAll('input[type="checkbox"]')].map(
    (c) => c.closest("label")?.innerText.split("\n")[0] ?? ""));
const permIdx = labels.findIndex((l) => /Permutation/i.test(l));
if (permIdx >= 0) await boxes[permIdx].click();

const permField = await page.$('input.field.num');
if (permField) { await permField.click({ clickCount: 3 }); await permField.type("15000"); }

const startBtn = await page.$$eval("button", (bs) =>
  bs.findIndex((b) => /^Run \d+ check/.test(b.innerText)));
const buttons = await page.$$("button");
if (startBtn < 0) { console.log("could not find the start button"); await browser.close(); process.exit(1); }

const tStart = Date.now();
await buttons[startBtn].click();
await sleep(4000);
const duringRun = since(tStart);
const urlDuringRun = page.url();
console.log(`polls while the job runs      ${duringRun} in 4s  (url ${new URL(urlDuringRun).pathname})`);

// --- A: navigate away mid-job; polling must stop on unmount ------------------
await page.goto(`${BASE}/`, { waitUntil: "load", timeout: 20000 });
await sleep(1000);
const tAway = Date.now();
await sleep(6000);
console.log(`polls after navigating away   ${since(tAway)} in 6s   <- must be 0`);

// --- B: let the job finish, then watch for stragglers ------------------------
const tBack = Date.now();
await page.goto(`${BASE}/run`, { waitUntil: "networkidle2", timeout: 20000 });
await sleep(3000);
console.log(`polls after returning to /run ${since(tBack)} in 3s   <- must be > 0 (resumed)`);
let settled = false;
for (let i = 0; i < 60; i++) {
  await sleep(1000);
  if (/\/results\//.test(page.url())) { settled = true; break; }
}
const tDone = Date.now();
await sleep(8000);
console.log(`reached results page          ${settled} (${new URL(page.url()).pathname})`);
console.log(`polls after completion        ${since(tDone)} in 8s   <- must be 0`);

// --- C: idle cost of the Results page ---------------------------------------
const cdp = await page.createCDPSession();
await cdp.send("Performance.enable");
const m = async () => Object.fromEntries(
  (await cdp.send("Performance.getMetrics")).metrics.map((x) => [x.name, x.value]));
const b4 = await m();
const t = Date.now();
await sleep(6000);
const af = await m();
console.log(`results page main-thread      ${(af.TaskDuration - b4.TaskDuration).toFixed(4)} s over 6s`);
console.log(`results page api requests     ${since(t)}`);
console.log(`page errors                   ${failures.length}${failures.length ? " -> " + failures.slice(0, 3).join(" | ").slice(0, 300) : ""}`);

await browser.close();
