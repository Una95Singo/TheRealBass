import { useEffect, useRef } from "react";
import {
  Renderer,
  Stave,
  StaveNote,
  Accidental,
  Formatter,
  Voice,
  TabStave,
  TabNote,
  StaveConnector,
} from "vexflow";

const MEASURE_WIDTH = 260;
const STAVE_GAP = 90;        // vertical distance from standard stave to tab stave
const ROW_HEIGHT = 230;      // total vertical footprint per row (standard + tab + pad)
const CHORD_PAD = 26;

// 4-string bass, standard tuning. VexFlow numbers strings top-to-bottom in tab
// (string 1 = highest-pitched). Open-string MIDI for [G2, D2, A1, E1].
const OPEN_STRING_MIDI = [43, 38, 33, 28];

const PITCH_CLASS = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };

function pitchToMidi(pitchStr) {
  const m = pitchStr.match(/^([A-G])(#{1,2}|b{1,2})?(-?\d+)$/);
  if (!m) return null;
  const [, letter, acc, octStr] = m;
  let semitone = PITCH_CLASS[letter];
  if (acc === "#") semitone += 1;
  else if (acc === "##") semitone += 2;
  else if (acc === "b") semitone -= 1;
  else if (acc === "bb") semitone -= 2;
  return (parseInt(octStr, 10) + 1) * 12 + semitone;
}

export function pitchToStringFret(midi) {
  let best = null;
  for (let s = 0; s < OPEN_STRING_MIDI.length; s++) {
    const fret = midi - OPEN_STRING_MIDI[s];
    if (fret >= 0 && fret <= 24) {
      if (best === null || fret < best.fret) {
        best = { str: s + 1, fret };
      }
    }
  }
  if (best) return best;
  // Out of range — clamp to the nearest playable fret on string 4.
  const clamped = Math.max(0, Math.min(24, midi - OPEN_STRING_MIDI[3]));
  return { str: 4, fret: clamped };
}

function toVexKey(pitch) {
  const octave = pitch.slice(-1);
  const name = pitch.slice(0, -1);
  return `${name.toLowerCase()}/${octave}`;
}

function accidentalFor(pitch) {
  const mid = pitch.slice(1, -1);
  if (mid === "#" || mid === "##") return mid;
  if (mid === "b" || mid === "bb") return mid;
  return null;
}

export default function NotationRenderer({ data }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    containerRef.current.innerHTML = "";

    const measures = data.measures || [];
    const [numBeats, beatValue] = (data.time_signature || "4/4")
      .split("/")
      .map(Number);
    const perRow = 4;
    const rows = Math.max(1, Math.ceil(measures.length / perRow));
    const width = Math.min(measures.length, perRow) * MEASURE_WIDTH + 40;
    const height = rows * ROW_HEIGHT + CHORD_PAD + 20;

    const renderer = new Renderer(containerRef.current, Renderer.Backends.SVG);
    renderer.resize(width, height);
    const ctx = renderer.getContext();

    measures.forEach((measure, idx) => {
      const row = Math.floor(idx / perRow);
      const col = idx % perRow;
      const x = 20 + col * MEASURE_WIDTH;
      const y = 20 + row * ROW_HEIGHT + CHORD_PAD;

      const stave = new Stave(x, y, MEASURE_WIDTH);
      if (col === 0 && row === 0) {
        stave.addClef("bass");
        stave.addTimeSignature(data.time_signature || "4/4");
      } else if (col === 0) {
        stave.addClef("bass");
      }
      stave.setContext(ctx).draw();

      if (measure.chord) {
        ctx.save();
        if (typeof ctx.setFont === "function") {
          try {
            ctx.setFont("Helvetica", 14, "bold");
          } catch (_) {
            /* SVG context font signature varies; ignore. */
          }
        }
        ctx.fillText(measure.chord, x + 4, y - 6);
        ctx.restore();
      }

      // Tab stave below the standard stave.
      let tabStave = null;
      if (typeof ctx.openGroup === "function") ctx.openGroup("therealbass-tab");
      tabStave = new TabStave(x, y + STAVE_GAP, MEASURE_WIDTH, { num_lines: 4 });
      if (col === 0) {
        tabStave.addClef("tab");
      }
      tabStave.setContext(ctx).draw();

      // Left-edge connector between standard + tab staves (only on first measure of row).
      if (col === 0) {
        new StaveConnector(stave, tabStave)
          .setType(StaveConnector.type.SINGLE_LEFT)
          .setContext(ctx)
          .draw();
      }
      if (typeof ctx.closeGroup === "function") ctx.closeGroup();

      const rawNotes = measure.notes || [];
      if (!rawNotes.length) return;

      const staveNotes = rawNotes.map((n) => {
        const note = new StaveNote({
          clef: "bass",
          keys: [toVexKey(n.pitch)],
          duration: n.duration,
        });
        const acc = accidentalFor(n.pitch);
        if (acc) note.addModifier(new Accidental(acc), 0);
        return note;
      });

      const tabNotes = rawNotes.map((n) => {
        const midi = pitchToMidi(n.pitch);
        const { str, fret } = midi != null
          ? pitchToStringFret(midi)
          : { str: 1, fret: 0 };
        return new TabNote({
          positions: [{ str, fret }],
          duration: n.duration,
        });
      });

      const staveVoice = new Voice({
        num_beats: numBeats,
        beat_value: beatValue,
      }).setStrict(false);
      staveVoice.addTickables(staveNotes);

      const tabVoice = new Voice({
        num_beats: numBeats,
        beat_value: beatValue,
      }).setStrict(false);
      tabVoice.addTickables(tabNotes);

      new Formatter()
        .joinVoices([staveVoice])
        .joinVoices([tabVoice])
        .format([staveVoice, tabVoice], MEASURE_WIDTH - 40);

      staveVoice.draw(ctx, stave);
      if (typeof ctx.openGroup === "function") ctx.openGroup("therealbass-tab");
      tabVoice.draw(ctx, tabStave);
      if (typeof ctx.closeGroup === "function") ctx.closeGroup();
    });
  }, [data]);

  return <div ref={containerRef} className="notation" />;
}
