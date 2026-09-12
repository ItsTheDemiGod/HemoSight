/* Two failure modes the happy path never exercises.
 *
 * A. The backend stops answering. `await api.run(id)` rejects inside the interval
 *    callback. Does the interval stop, back off, or retry forever?
 * B. The backend answers slowly. setInterval does not wait for the previous request,
 *    so requests can overlap and stack.
 *
 *   node tools/measure_poll_failure.mjs <baseUrl> <apiUrl> <mode: fail|slow> [label]
 */
import fs from "node:fs";
import puppeteer from "puppeteer-core";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = process.argv[2] ?? "http://127.0.0.1:5173";
const API = process.argv[3] ?? "http://127.0.0.1:8000";
const MODE = process.argv[4] ?? "fail";
const LABEL = process.argv[5] ?? `${MODE} @ ${BASE}`;
const CSV = "app/backend/sample_data/02_clean_no_injected_fault.csv";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const fd = new FormData();
fd.append("predictions", new Blob([fs.readFileSync(`../../${CSV}`)]), "sample.csv");
const sub = await (await fetch(`${API}/api/submissions`, { method: "POST", body: fd })).json();

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();
await page.evaluateOnNewDocument((id) => {
  localStorage.setItem("hemosight-audit-session", JSON.stringify({ submissionId: id }));
}, sub.id);

let sabotage = false;
let inFlight = 0;
let maxInFlight = 0;
const polls = [];
const rejections = [];

await page.setRequestInterception(true);
page.on("request", async (r) => {
  const isPoll = /\/api\/runs\/[a-f0-9]+$/.test(r.url()) && r.method() === "GET";
  if (isPoll) {
    polls.push(Date.now());
    inFlight++;
    maxInFlight = Math.max(maxInFlight, inFlight);
  }
  if (isPoll && sabotage) {
    if (MODE === "fail") { inFlight--; return r.abort("failed"); }
    await sleep(3000);                       // three intervals' worth
  }
  try { await r.continue(); } catch { /* page may have gone */ }
  if (isPoll) inFlight--;
});
page.on("pageerror", (e) => rejections.push(String(e)));
page.on("console", (m) => {
  const t = m.text();
  if (m.type() === "error" && !/404/.test(t)) rejections.push(t);
});

await page.goto(`${BASE}/run`, { waitUntil: "networkidle2", timeout: 30000 });
await page.evaluate(() => {
  document.querySelectorAll('input[type="checkbox"]').forEach((c) => { if (c.checked) c.click(); });
});
const labels = await page.evaluate(() =>
  [...document.querySelectorAll('input[type="checkbox"]')].map(
    (c) => c.closest("label")?.innerText.split("\n")[0] ?? ""));
const boxes = await page.$$('input[type="checkbox"]');
const idx = labels.findIndex((l) => /Permutation/i.test(l));
if (idx >= 0) await boxes[idx].click();
const permField = await page.$("input.field.num");
if (permField) { await permField.click({ clickCount: 3 }); await permField.type("400000"); }

const buttons = await page.$$("button");
const startIdx = await page.$$eval("button", (bs) =>
  bs.findIndex((b) => /^Run \d+ check/.test(b.innerText)));
await buttons[startIdx].click();
await sleep(2500);

const before = polls.length;
sabotage = true;
const t0 = Date.now();
await sleep(12000);
const after = polls.filter((p) => p > t0).length;

console.log(`\n========== ${LABEL} ==========`);
console.log(`mode                          ${MODE}`);
console.log(`polls before sabotage         ${before}`);
console.log(`polls during 12s of sabotage  ${after}`);
console.log(`implied interval              ${after ? (12000 / after).toFixed(0) + " ms" : "n/a - stopped"}`);
console.log(`max concurrent poll requests  ${maxInFlight}`);
console.log(`uncaught page errors          ${rejections.length}`);
rejections.slice(0, 4).forEach((r) => console.log(`    ${r.slice(0, 140)}`));
const visible = await page.evaluate(() => document.body.innerText.includes("stopped responding"));
console.log(`UI surfaces the give-up       ${visible}`);
const spinning = await page.evaluate(() => document.body.innerText.includes("Progress updates stopped"));
console.log(`live view taken down          ${spinning}`);

await browser.close();
