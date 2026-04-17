export default function ProcessingView() {
  return (
    <div className="processing">
      <p>Isolating bass, transcribing MIDI, and analyzing key/tempo...</p>
      <p style={{ fontSize: 12, color: "#666" }}>
        First run may take a few minutes while Demucs downloads model weights.
      </p>
    </div>
  );
}
