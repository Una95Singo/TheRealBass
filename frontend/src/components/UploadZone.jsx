import { useRef, useState } from "react";

const ACCEPTED = [".mp3", ".wav", ".m4a"];

export default function UploadZone({ onFile, disabled }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(fileList) {
    if (!fileList || !fileList.length) return;
    const file = fileList[0];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      alert(`Unsupported file type. Allowed: ${ACCEPTED.join(", ")}`);
      return;
    }
    onFile(file);
  }

  return (
    <div
      className={`upload-zone ${dragging ? "dragging" : ""}`}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
    >
      <p>Drop an audio file (.mp3, .wav, .m4a) or click to browse.</p>
      <p style={{ fontSize: 12, color: "#666" }}>Max 50MB</p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(",")}
        style={{ display: "none" }}
        onChange={(e) => handleFiles(e.target.files)}
        disabled={disabled}
      />
    </div>
  );
}
