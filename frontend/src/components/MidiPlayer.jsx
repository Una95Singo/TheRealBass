import { useEffect, useRef, useState } from "react";
import * as Tone from "tone";
import { Midi } from "@tonejs/midi";

// Plays back the transcribed MIDI in the browser using a Tone.js synth.
// Exposes Play/Pause/Stop and a read-only progress bar.
export default function MidiPlayer({ url }) {
  const synthRef = useRef(null);
  const partRef = useRef(null);
  const [state, setState] = useState("idle"); // idle | ready | playing | paused
  const [duration, setDuration] = useState(0);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const midi = await Midi.fromUrl(url);
        if (cancelled) return;

        const synth = new Tone.PolySynth(Tone.Synth, {
          oscillator: { type: "triangle" },
          envelope: { attack: 0.005, decay: 0.1, sustain: 0.6, release: 0.2 },
        });
        synth.volume.value = -8;
        synth.toDestination();
        synthRef.current = synth;

        const events = [];
        midi.tracks.forEach((track) => {
          track.notes.forEach((n) => {
            events.push({ time: n.time, name: n.name, duration: n.duration, velocity: n.velocity });
          });
        });

        const part = new Tone.Part((time, ev) => {
          synth.triggerAttackRelease(ev.name, ev.duration, time, ev.velocity);
        }, events);
        part.start(0);
        partRef.current = part;

        setDuration(midi.duration);
        setState("ready");
      } catch (e) {
        if (!cancelled) setError(e.message || "Failed to load MIDI");
      }
    })();

    return () => {
      cancelled = true;
      Tone.Transport.stop();
      Tone.Transport.cancel();
      partRef.current?.dispose();
      synthRef.current?.dispose();
      partRef.current = null;
      synthRef.current = null;
    };
  }, [url]);

  useEffect(() => {
    if (state !== "playing") return undefined;
    const id = setInterval(() => {
      setProgress(Tone.Transport.seconds);
      if (duration > 0 && Tone.Transport.seconds >= duration) {
        Tone.Transport.stop();
        setState("ready");
        setProgress(0);
      }
    }, 100);
    return () => clearInterval(id);
  }, [state, duration]);

  async function handlePlay() {
    if (state === "playing") return;
    await Tone.start();
    if (state === "paused") {
      Tone.Transport.start();
    } else {
      Tone.Transport.stop();
      Tone.Transport.position = 0;
      Tone.Transport.start();
    }
    setState("playing");
  }

  function handlePause() {
    if (state !== "playing") return;
    Tone.Transport.pause();
    setState("paused");
  }

  function handleStop() {
    Tone.Transport.stop();
    setProgress(0);
    setState("ready");
  }

  if (error) {
    return <div className="midi-player error">MIDI preview unavailable: {error}</div>;
  }

  const pct = duration > 0 ? Math.min(100, (progress / duration) * 100) : 0;

  return (
    <div className="midi-player">
      <label>Transcribed MIDI preview</label>
      <div className="midi-controls">
        <button
          type="button"
          onClick={handlePlay}
          disabled={state === "idle" || state === "playing"}
          aria-label="Play MIDI"
        >
          Play
        </button>
        <button
          type="button"
          onClick={handlePause}
          disabled={state !== "playing"}
          aria-label="Pause MIDI"
        >
          Pause
        </button>
        <button
          type="button"
          onClick={handleStop}
          disabled={state === "idle" || state === "ready"}
          aria-label="Stop MIDI"
        >
          Stop
        </button>
        <div className="midi-progress" aria-hidden="true">
          <div className="midi-progress-bar" style={{ width: `${pct}%` }} />
        </div>
        <span className="midi-time">
          {formatTime(progress)} / {formatTime(duration)}
        </span>
      </div>
    </div>
  );
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}
