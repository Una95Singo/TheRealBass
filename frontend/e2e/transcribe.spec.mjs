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
      chord: "G",
      notes: [
        { pitch: "G2", duration: "q", start_beat: 1 },
        { pitch: "D2", duration: "q", start_beat: 2 },
        { pitch: "E2", duration: "q", start_beat: 3 },
        { pitch: "D2", duration: "q", start_beat: 4 },
      ],
    },
    {
      measure_number: 2,
      chord: "C",
      notes: [
        { pitch: "C2", duration: "8", start_beat: 1 },
        { pitch: "E2", duration: "8", start_beat: 1.5 },
        { pitch: "G2", duration: "8", start_beat: 2 },
        { pitch: "B2", duration: "8", start_beat: 2.5 },
        { pitch: "C3", duration: "h", start_beat: 3 },
      ],
    },
    {
      measure_number: 3,
      chord: "Am",
      notes: [
        { pitch: "A2", duration: "q", start_beat: 1 },
        { pitch: "E2", duration: "q", start_beat: 2 },
        { pitch: "A2", duration: "h", start_beat: 3 },
      ],
    },
    {
      measure_number: 4,
      chord: "D7",
      notes: [{ pitch: "D2", duration: "w", start_beat: 1 }],
    },
  ],
  bass_stem_path: "/tmp/therealbass/stems/htdemucs/abc/bass.wav",
  file_id: "abc00000000000000000000000000000",
  bass_audio_url: "/stems/abc00000000000000000000000000000/bass.wav",
  midi_url: "/midi/abc00000000000000000000000000000/bass.mid",
};

const fakeMp3Buffer = Buffer.from([0xff, 0xfb, 0x90, 0x44, 0x00, 0x00, 0x00, 0x00]);

// Minimal valid format-0 MIDI file (header + empty track + end-of-track).
const minimalMidi = Buffer.from([
  0x4d, 0x54, 0x68, 0x64, 0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x01, 0x00, 0x60,
  0x4d, 0x54, 0x72, 0x6b, 0x00, 0x00, 0x00, 0x04, 0x00, 0xff, 0x2f, 0x00,
]);

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
    // Stub the audio endpoint so the <audio> element doesn't emit a real request.
    await page.route("**/stems/**/bass.wav", async (route) => {
      await route.fulfill({ status: 200, contentType: "audio/wav", body: "" });
    });
    await page.route("**/midi/**/bass.mid", async (route) => {
      await route.fulfill({ status: 200, contentType: "audio/midi", body: minimalMidi });
    });
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

    // Chord symbols are rendered above the staves.
    const svgText = await page.locator(".notation svg").innerHTML();
    for (const chord of ["G", "C", "Am", "D7"]) {
      expect(svgText).toContain(`>${chord}</text>`);
    }

    // Isolated bass stem audio element is present and points at the backend.
    const audio = page.locator(".bass-audio audio");
    await expect(audio).toHaveCount(1);
    const src = await audio.getAttribute("src");
    expect(src).toContain("/stems/abc00000000000000000000000000000/bass.wav");

    // PDF download button is present.
    await expect(page.getByRole("button", { name: /Download PDF/i })).toBeVisible();

    // MIDI preview player is mounted with a Play button.
    await expect(page.locator(".midi-player")).toBeVisible();
    await expect(page.getByRole("button", { name: /Play MIDI/i })).toBeVisible();

    // Tab notes are rendered under every measure.
    const tabNoteCount = await page.locator(".notation svg .vf-tabnote").count();
    expect(tabNoteCount).toBeGreaterThan(0);
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

  test("backend 413: shows 250MB limit error", async ({ page }) => {
    await page.route(TRANSCRIBE_URL, async (route) => {
      await route.fulfill({
        status: 413,
        contentType: "application/json",
        body: JSON.stringify({ detail: "File exceeds 250MB limit." }),
      });
    });

    await page.goto("/");
    await uploadFakeMp3(page);

    const err = page.locator(".error");
    await expect(err).toBeVisible();
    await expect(err).toContainText("250MB");
  });
});
