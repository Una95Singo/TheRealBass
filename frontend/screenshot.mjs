import { chromium } from "playwright";

const URL = process.env.URL || "http://127.0.0.1:5173";
const OUT_FULL = process.argv[2] || "../artifacts/sample-notation-full.png";
const OUT_STAVE = process.argv[3] || "../artifacts/sample-notation.png";

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();

page.on("pageerror", (err) => console.error("PAGE ERROR:", err));
page.on("console", (msg) => {
  if (msg.type() === "error") console.error("CONSOLE:", msg.text());
});

await page.goto(URL, { waitUntil: "domcontentloaded" });
await page.getByRole("button", { name: /Load sample notation/i }).click();

const notation = page.locator(".notation");
await notation.waitFor({ state: "visible" });
await page.waitForFunction(() => !!document.querySelector(".notation svg"));

await page.screenshot({ path: OUT_FULL, fullPage: true });
await notation.screenshot({ path: OUT_STAVE });

console.log("Saved", OUT_FULL, "and", OUT_STAVE);
await browser.close();
