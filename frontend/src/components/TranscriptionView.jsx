import NotationRenderer from "./NotationRenderer.jsx";

export default function TranscriptionView({ data, onReset }) {
  return (
    <div>
      <div className="meta">
        <span><strong>Key:</strong> {data.key}</span>
        <span><strong>BPM:</strong> {data.bpm}</span>
        <span><strong>Time:</strong> {data.time_signature}</span>
      </div>
      <NotationRenderer data={data} />
      <button style={{ marginTop: 16 }} onClick={onReset}>
        Transcribe another file
      </button>
    </div>
  );
}
