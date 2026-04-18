const API_BASE = "http://127.0.0.1:8000";

export function stemAudioUrl(relativeUrl) {
  if (!relativeUrl) return null;
  return `${API_BASE}${relativeUrl}`;
}

export function midiUrl(relativeUrl) {
  if (!relativeUrl) return null;
  return `${API_BASE}${relativeUrl}`;
}

export async function transcribeFile(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/transcribe`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || "Request failed");
  }
  return res.json();
}
