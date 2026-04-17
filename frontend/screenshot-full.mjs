// Screenshot the full TranscriptionView (audio player + PDF button) by
// stubbing the backend via route interception. Complements screenshot.mjs,
// which only drives the dev-only "Load sample notation" button.
import { chromium } from "playwright";

const URL = process.env.URL || "http://127.0.0.1:5173";
const OUT_DONE = "../artifacts/transcription-view.png";
const OUT_PROCESSING = "../artifacts/processing-view.png";

const sample = {
  key: "G major",
  bpm: 120,
  time_signature: "4/4",
  measures: [
    { measure_number: 1, notes: [
      { pitch: "G2", duration: "q", start_beat: 1 },
      { pitch: "D2", duration: "q", start_beat: 2 },
      { pitch: "E2", duration: "q", start_beat: 3 },
      { pitch: "D2", duration: "q", start_beat: 4 },
    ]},
    { measure_number: 2, notes: [
      { pitch: "F#2", duration: "q", start_beat: 1 },
      { pitch: "Bb2", duration: "q", start_beat: 2 },
      { pitch: "A2", duration: "h", start_beat: 3 },
    ]},
  ],
  bass_stem_path: "/tmp/therealbass/stems/htdemucs/abc/bass.wav",
  file_id: "abc00000000000000000000000000000",
  bass_audio_url: "/stems/abc00000000000000000000000000000/bass.wav",
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();

page.on("pageerror", (e) => console.error("PAGE ERROR:", e));
page.on("console", (msg) => console.log(`[${msg.type()}] ${msg.text()}`));
page.on("request", (req) => {
  if (req.url().includes("transcribe") || req.url().includes("stems")) {
    console.log("REQ", req.method(), req.url());
  }
});

// ---- processing view ----
await page.route("http://127.0.0.1:8000/transcribe", async (route) => {
  await new Promise((r) => setTimeout(r, 2500));
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(sample),
  });
});
await page.route("**/stems/**/bass.wav", async (route) => {
  await route.fulfill({ status: 200, contentType: "audio/wav", body: "" });
});

await page.goto(URL);
const [_req] = await Promise.all([
  page.waitForRequest("http://127.0.0.1:8000/transcribe"),
  page.locator('input[type="file"]').setInputFiles({
    name: "test.mp3",
    mimeType: "audio/mpeg",
    buffer: Buffer.from([0xff, 0xfb, 0x90, 0x44]),
  }),
]);
// Capture the processing view while the route handler still holds the response.
await page.locator(".processing").waitFor({ state: "visible", timeout: 5000 });
await page.waitForTimeout(800);
await page.locator(".processing").screenshot({ path: OUT_PROCESSING });

// ---- done view ----
await page.locator(".bass-audio").waitFor({ state: "visible" });
await page.waitForFunction(() => !!document.querySelector(".notation svg"));
await page.screenshot({ path: OUT_DONE, fullPage: true });

console.log("Saved", OUT_DONE, "and", OUT_PROCESSING);
await browser.close();
