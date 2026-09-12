/* One-off screenshots of specific routes at a width: node tools/shot_8b.mjs <base> <outdir> <width> <route...> */
import puppeteer from "puppeteer-core";
import path from "node:path";
const [base, out, width, ...routes] = process.argv.slice(2);
const b = await puppeteer.launch({ executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", headless: "new", args: ["--no-sandbox"] });
const p = await b.newPage();
await p.setViewport({ width: Number(width), height: 900 });
for (const r of routes) {
  await p.goto(base + r, { waitUntil: "networkidle0" });
  await new Promise((res) => setTimeout(res, 800));
  // open the first technical-statement reveal so the layered disclosure is visible
  await p.evaluate(() => { const b = Array.from(document.querySelectorAll("button")).find((x) => /Technical statement/.test(x.textContent || "")); b && b.click(); });
  await new Promise((res) => setTimeout(res, 400));
  const f = path.join(out, `shot_${width}_${r.replace(/[\/:]/g, "_") || "home"}.png`);
  await p.screenshot({ path: f, fullPage: true });
  console.log(f);
}
await b.close();
