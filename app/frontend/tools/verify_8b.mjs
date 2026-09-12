/* Phase 8B verification: every page at desktop / tablet / mobile widths, with motion on
   and with the OS reduced-motion preference emulated, in headless Chrome.
   Records per page x width x mode: console errors, the html[data-motion] and
   [data-cursor] state, whether every `.reveal` element ended visible, whether the first
   Tab lands on a focusable element with a visible outline, and a screenshot.

     node tools/verify_8b.mjs http://localhost:4173 <outdir>
*/
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import path from "node:path";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const base = process.argv[2] ?? "http://localhost:4173";
const out = process.argv[3] ?? "verify_8b";
fs.mkdirSync(out, { recursive: true });

const PAGES = ["/", "/prereg", "/upload", "/run", "/results", "/report", "/case-study", "/glossary"];
const WIDTHS = { desktop: [1440, 900], tablet: [834, 1112], mobile: [390, 844] };
const MODES = ["motion", "reduced"];

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"] });
const results = [];

for (const mode of MODES) {
  for (const [wname, [w, h]] of Object.entries(WIDTHS)) {
    const page = await browser.newPage();
    await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: mode === "reduced" ? "reduce" : "no-preference" }]);
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e.message)));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    for (const p of PAGES) {
      await page.goto(base + p, { waitUntil: "networkidle0", timeout: 30000 });
      await new Promise((r) => setTimeout(r, 400));
      // scroll to the bottom and back so scroll-triggered reveals fire
      // scroll like a reader: wheel steps ~120 ms apart, so frame-throttled scroll
      // listeners (ScrollTrigger) see every position, then return to the top
      const total = await page.evaluate(() => document.body.scrollHeight);
      for (let y = 0; y < total; y += Math.floor(h * 0.5)) {
        await page.mouse.wheel({ deltaY: Math.floor(h * 0.5) });
        await new Promise((r) => setTimeout(r, 120));
      }
      await new Promise((r) => setTimeout(r, 700));
      await page.evaluate(() => window.scrollTo(0, 0));
      await new Promise((r) => setTimeout(r, 500));
      const state = await page.evaluate(() => {
        const html = document.documentElement;
        const reveals = Array.from(document.querySelectorAll(".reveal"));
        const hidden = reveals.filter((el) => Number(getComputedStyle(el).opacity) < 0.9).length;
        const canvas = document.querySelectorAll("canvas").length;
        return { motion: html.getAttribute("data-motion"), cursor: html.getAttribute("data-cursor"),
                 reveals: reveals.length, revealsHidden: hidden, canvas,
                 h1: document.querySelector("h1")?.textContent?.trim().slice(0, 60) ?? null,
                 horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1 };
      });
      // keyboard: first Tab should land on the skip link (or a nav link) with a visible outline
      await page.keyboard.press("Tab");
      const focus = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return { tag: null, outline: null };
        const cs = getComputedStyle(el);
        return { tag: el.tagName + (el.textContent ? ":" + el.textContent.trim().slice(0, 30) : ""),
                 outline: cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0,
                 cursorAttr: document.documentElement.getAttribute("data-cursor") };
      });
      const shot = path.join(out, `${mode}_${wname}${p === "/" ? "_home" : p.replace(/\//g, "_")}.png`);
      await page.screenshot({ path: shot, fullPage: p === "/" && wname === "desktop" });
      results.push({ mode, width: wname, page: p, ...state, focus, errors: errors.splice(0), shot: path.basename(shot) });
      console.log(`${mode.padEnd(8)} ${wname.padEnd(8)} ${p.padEnd(12)} motion=${state.motion} cursor=${state.cursor} reveals=${state.reveals}/${state.revealsHidden} hidden canvas=${state.canvas} focus=${focus.outline} overflow=${state.horizontalOverflow} errors=${results[results.length-1].errors.length}`);
    }
    await page.close();
  }
}
await browser.close();
fs.writeFileSync(path.join(out, "verify_8b.json"), JSON.stringify(results, null, 2));
const bad = results.filter((r) => r.errors.length || r.revealsHidden || r.horizontalOverflow || !r.focus.outline);
console.log(`\n${results.length} page states checked; ${bad.length} with a problem`);
for (const b of bad) console.log("  PROBLEM", b.mode, b.width, b.page, JSON.stringify({ errors: b.errors, hidden: b.revealsHidden, overflow: b.horizontalOverflow, focus: b.focus }));
