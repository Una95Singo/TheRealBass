// Hardcoded sample conforming to the backend /transcribe JSON shape.
// Used to verify NotationRenderer independently of the backend.
export const sampleTranscription = {
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
      notes: [
        { pitch: "D2", duration: "w", start_beat: 1 },
      ],
    },
  ],
  bass_stem_path: "/tmp/therealbass/stems/htdemucs/sample/bass.wav",
  file_id: "00000000000000000000000000000000",
  bass_audio_url: null,
};
