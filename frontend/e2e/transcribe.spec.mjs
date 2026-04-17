import { test, expect } from "@playwright/test";

const TRANSCRIBE_URL = "http://127.0.0.1:8000/transcribe";

// Duplicated from src/sampleData.js per task instructions (don't import from src).
const sampleTranscription = {
  key: "G major",
  bpm: 120,
  time_signature: "4/4",
  measures: [
    {
      measure_number: 1,
      notes: [
        { pitch: "G2", duration: "q", start_beat: 1 },
        { pitch: "D2", duration: "q", start_beat: 2 },
        { pitch: "E2", duration: "q", start_beat: 3 },
        { pitch: "D2", duration: "q", start_beat: 4 },
      ],
    },
    {
      measure_number: 2,
      notes: [
        { pitch: "G2", duration: "8", start_beat: 1 },
        { pitch: "A2", duration: "8", start_beat: 1.5 },
        { pitch: "B2", duration: "8", start_beat: 2 },
        { pitch: "C3", duration: "8", start_beat: 2.5 },
        { pitch: "D3", duration: "h", start_beat: 3 },
      ],
    },
    {
      measure_number: 3,
      notes: [
        { pitch: "F#2", duration: "q", start_beat: 1 },
        { pitch: "Bb2", duration: "q", start_beat: 2 },
        { pitch: "A2", duration: "h", start_beat: 3 },
      ],
    },
    {
      measure_number: 4,
      notes: [{ pitch: "G2", duration: "w", start_beat: 1 }],
    },
  ],
  bass_stem_path: "/tmp/therealbass/stems",
};

const fakeMp3Buffer = Buffer.from([0xff, 0xfb, 0x90, 0x44, 0x00, 0x00, 0x00, 0x00]);

async function uploadFakeMp3(page) {
  const input = page.locator('input[type="file"]');
  await input.setInputFiles({
    name: "test.mp3",
    mimeType: "audio/mpeg",
    buffer: fakeMp3Buffer,
  });
}

test.describe("TheRealBass /transcribe flow", () => {
  test("happy path: renders key/bpm/time and VexFlow notation", async ({ page }) => {
    await page.route(TRANSCRIBE_URL, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sampleTranscription),
      });
    });

    await page.goto("/");
    await uploadFakeMp3(page);

    await expect(page.locator(".meta")).toContainText("Key:");
    await expect(page.locator(".meta")).toContainText("G major");
    await expect(page.locator(".meta")).toContainText("BPM:");
    await expect(page.locator(".meta")).toContainText("120");
    await expect(page.locator(".meta")).toContainText("Time:");
    await expect(page.locator(".meta")).toContainText("4/4");

    const notation = page.locator(".notation");
    await expect(notation).toBeVisible();
    await page.waitForFunction(() => !!document.querySelector(".notation svg"));
    await expect(notation.locator("svg")).toHaveCount(1);

    const pathCount = await page.locator(".notation svg path").count();
    expect(pathCount).toBeGreaterThan(0);
  });

  test("backend 400: shows Unsupported file type error", async ({ page }) => {
    await page.route(TRANSCRIBE_URL, async (route) => {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Unsupported file type" }),
      });
    });

    await page.goto("/");
    await uploadFakeMp3(page);

    const err = page.locator(".error");
    await expect(err).toBeVisible();
    await expect(err).toContainText("Unsupported file type");
  });

  test("backend 413: shows 50MB limit error", async ({ page }) => {
    await page.route(TRANSCRIBE_URL, async (route) => {
      await route.fulfill({
        status: 413,
        contentType: "application/json",
        body: JSON.stringify({ detail: "File exceeds 50MB limit." }),
      });
    });

    await page.goto("/");
    await uploadFakeMp3(page);

    const err = page.locator(".error");
    await expect(err).toBeVisible();
    await expect(err).toContainText("50MB");
  });
});
