import { useEffect, useRef } from "react";
import { Renderer, Stave, StaveNote, Accidental, Formatter, Voice } from "vexflow";

const MEASURE_WIDTH = 260;
const STAVE_HEIGHT = 140;

function toVexKey(pitch) {
  const name = pitch.slice(0, -1);
  const octave = pitch.slice(-1);
  return `${name.toLowerCase()}/${octave}`;
}

function accidentalFor(pitch) {
  if (pitch.includes("#")) return "#";
  if (pitch.toLowerCase().includes("b") && pitch.length > 2) return "b";
  return null;
}

export default function NotationRenderer({ data }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    containerRef.current.innerHTML = "";

    const measures = data.measures || [];
    const perRow = 4;
    const rows = Math.max(1, Math.ceil(measures.length / perRow));
    const width = Math.min(measures.length, perRow) * MEASURE_WIDTH + 40;
    const height = rows * STAVE_HEIGHT + 40;

    const renderer = new Renderer(containerRef.current, Renderer.Backends.SVG);
    renderer.resize(width, height);
    const ctx = renderer.getContext();

    measures.forEach((measure, idx) => {
      const row = Math.floor(idx / perRow);
      const col = idx % perRow;
      const x = 20 + col * MEASURE_WIDTH;
      const y = 20 + row * STAVE_HEIGHT;

      const stave = new Stave(x, y, MEASURE_WIDTH);
      if (col === 0 && row === 0) {
        stave.addClef("bass");
        stave.addTimeSignature(data.time_signature || "4/4");
      } else if (col === 0) {
        stave.addClef("bass");
      }
      stave.setContext(ctx).draw();

      const notes = (measure.notes || []).map((n) => {
        const note = new StaveNote({
          clef: "bass",
          keys: [toVexKey(n.pitch)],
          duration: n.duration,
        });
        const acc = accidentalFor(n.pitch);
        if (acc) note.addModifier(new Accidental(acc), 0);
        return note;
      });

      if (!notes.length) return;

      const voice = new Voice({ num_beats: 4, beat_value: 4 }).setStrict(false);
      voice.addTickables(notes);
      new Formatter().joinVoices([voice]).format([voice], MEASURE_WIDTH - 40);
      voice.draw(ctx, stave);
    });
  }, [data]);

  return <div ref={containerRef} className="notation" />;
}
