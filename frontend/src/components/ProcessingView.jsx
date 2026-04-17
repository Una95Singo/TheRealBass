import { useEffect, useState } from "react";

const STAGES = [
  "Isolating bass stem (Demucs)...",
  "Transcribing notes (Basic Pitch)...",
  "Analyzing key, tempo, and time signature (music21)...",
  "Rendering notation...",
];

export default function ProcessingView() {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStage((s) => (s + 1) % STAGES.length), 2500);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="processing">
      <div className="spinner" aria-hidden="true" />
      <p className="stage" role="status" aria-live="polite">
        {STAGES[stage]}
      </p>
      <p className="hint">
        First run may take a few minutes while Demucs downloads model weights (~1GB).
      </p>
    </div>
  );
}
