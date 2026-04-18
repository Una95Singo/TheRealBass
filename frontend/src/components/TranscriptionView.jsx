import { useRef } from "react";
import { jsPDF } from "jspdf";
import { svg2pdf } from "svg2pdf.js";
import NotationRenderer from "./NotationRenderer.jsx";
import MidiPlayer from "./MidiPlayer.jsx";
import { stemAudioUrl, midiUrl } from "../api.js";

export default function TranscriptionView({ data, onReset }) {
  const notationRef = useRef(null);
  const audioUrl = stemAudioUrl(data.bass_audio_url);
  const midiPreviewUrl = midiUrl(data.midi_url);

  async function handleDownloadPdf() {
    const svg = notationRef.current?.querySelector("svg");
    if (!svg) return;
    const bbox = svg.getBoundingClientRect();
    const width = bbox.width || 1100;
    const height = bbox.height || 200;
    const doc = new jsPDF({
      orientation: width >= height ? "landscape" : "portrait",
      unit: "pt",
      format: [width + 40, height + 80],
    });
    doc.setFontSize(16);
    doc.text("TheRealBass — Bass Lead Sheet", 20, 28);
    doc.setFontSize(10);
    doc.text(
      `Key: ${data.key}   BPM: ${data.bpm}   Time: ${data.time_signature}`,
      20,
      46,
    );
    await svg2pdf(svg, doc, { x: 20, y: 60 });
    doc.save("therealbass-lead-sheet.pdf");
  }

  return (
    <div>
      <div className="meta">
        <span><strong>Key:</strong> {data.key}</span>
        <span><strong>BPM:</strong> {data.bpm}</span>
        <span><strong>Time:</strong> {data.time_signature}</span>
      </div>

      <div ref={notationRef}>
        <NotationRenderer data={data} />
      </div>

      {audioUrl && (
        <div className="bass-audio">
          <label>Isolated bass stem</label>
          <audio src={audioUrl} controls preload="metadata" />
        </div>
      )}

      {midiPreviewUrl && <MidiPlayer url={midiPreviewUrl} />}

      <div className="actions">
        <button onClick={handleDownloadPdf} className="primary">
          Download PDF
        </button>
        <button onClick={onReset}>Transcribe another file</button>
      </div>
    </div>
  );
}
