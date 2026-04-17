// Hardcoded sample conforming to the backend /transcribe JSON shape.
// Used to verify NotationRenderer independently of the backend.
export const sampleTranscription = {
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
      notes: [
        { pitch: "G2", duration: "w", start_beat: 1 },
      ],
    },
  ],
  bass_stem_path: "/tmp/therealbass/stems",
};
