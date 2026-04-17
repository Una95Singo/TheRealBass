import { useState } from "react";
import UploadZone from "./components/UploadZone.jsx";
import ProcessingView from "./components/ProcessingView.jsx";
import TranscriptionView from "./components/TranscriptionView.jsx";
import { transcribeFile } from "./api.js";
import { sampleTranscription } from "./sampleData.js";

export default function App() {
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleFile(file) {
    setStatus("processing");
    setError(null);
    try {
      const data = await transcribeFile(file);
      setResult(data);
      setStatus("done");
    } catch (e) {
      setError(e.message);
      setStatus("idle");
    }
  }

  function reset() {
    setResult(null);
    setStatus("idle");
    setError(null);
  }

  return (
    <div className="app">
      <h1>TheRealBass</h1>
      <p>Upload a track, get a Real Book-style bass lead sheet.</p>

      {status === "idle" && (
        <>
          <UploadZone onFile={handleFile} />
          <button
            style={{ marginTop: 12 }}
            onClick={() => {
              setResult(sampleTranscription);
              setStatus("done");
            }}
          >
            Load sample notation (dev)
          </button>
          {error && <p className="error">{error}</p>}
        </>
      )}
      {status === "processing" && <ProcessingView />}
      {status === "done" && result && (
        <TranscriptionView data={result} onReset={reset} />
      )}
    </div>
  );
}
