import { useEffect, useRef, useState } from "react";
import * as Tone from "tone";
import { Midi } from "@tonejs/midi";

// A/B playback of the isolated bass stem against the synthesized MIDI.
// "Original" plays the bass audio, "MIDI" plays the Tone.js synth, "Both"
// plays them together so the user can hear where the transcription differs.
export default function MidiPlayer({ midiUrl, bassUrl }) {
  const audioRef = useRef(null);
  const synthRef = useRef(null);
  const partRef = useRef(null);

  const [mode, setMode] = useState(bassUrl ? "both" : "midi");
  const [state, setState] = useState("idle"); // idle | ready | playing | paused
  const [midiLoaded, setMidiLoaded] = useState(false);
  const [midiDuration, setMidiDuration] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  // Load MIDI + set up Tone.js synth.
  useEffect(() => {
    if (!midiUrl) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const midi = await Midi.fromUrl(midiUrl);
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

        setMidiDuration(midi.duration);
        setMidiLoaded(true);
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
  }, [midiUrl]);

  const isReady = midiLoaded && (bassUrl ? audioDuration > 0 : true);
  useEffect(() => {
    if (isReady && state === "idle") setState("ready");
  }, [isReady, state]);

  // Apply mode changes to mute/unmute sources.
  useEffect(() => {
    if (synthRef.current) {
      synthRef.current.mute = mode === "original";
    }
    if (audioRef.current) {
      audioRef.current.muted = mode === "midi";
    }
  }, [mode]);

  // Tick progress while playing.
  useEffect(() => {
    if (state !== "playing") return undefined;
    const duration = Math.max(midiDuration, audioDuration);
    const id = setInterval(() => {
      const t =
        audioRef.current && !audioRef.current.paused
          ? audioRef.current.currentTime
          : Tone.Transport.seconds;
      setProgress(t);
      if (duration > 0 && t >= duration) {
        handleStop();
      }
    }, 100);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, midiDuration, audioDuration]);

  async function handlePlay() {
    if (!isReady || state === "playing") return;
    await Tone.start();

    // Reset positions unless resuming from pause.
    if (state !== "paused") {
      Tone.Transport.stop();
      Tone.Transport.position = 0;
      if (audioRef.current) audioRef.current.currentTime = 0;
    }

    // Apply mute state for the selected mode.
    if (synthRef.current) synthRef.current.mute = mode === "original";
    if (audioRef.current) audioRef.current.muted = mode === "midi";

    // Start both together. Missing sources are muted so they're cheap no-ops.
    if (audioRef.current) {
      audioRef.current.play().catch(() => {/* ignore autoplay denial */});
    }
    Tone.Transport.start();
    setState("playing");
  }

  function handlePause() {
    if (state !== "playing") return;
    Tone.Transport.pause();
    audioRef.current?.pause();
    setState("paused");
  }

  function handleStop() {
    Tone.Transport.stop();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setProgress(0);
    setState(isReady ? "ready" : "idle");
  }

  const duration = Math.max(midiDuration, audioDuration);
  const pct = duration > 0 ? Math.min(100, (progress / duration) * 100) : 0;
  const playDisabled = !isReady || state === "playing";
  const pauseDisabled = state !== "playing";
  const stopDisabled = state === "idle" || state === "ready";

  if (error) {
    return <div className="midi-player error">Playback unavailable: {error}</div>;
  }

  return (
    <div className="midi-player">
      <div className="midi-header">
        <label>Playback</label>
        <div className="midi-mode" role="radiogroup" aria-label="Playback source">
          {bassUrl && (
            <label>
              <input
                type="radio"
                name="playback-mode"
                value="original"
                checked={mode === "original"}
                onChange={() => setMode("original")}
              />
              Original
            </label>
          )}
          <label>
            <input
              type="radio"
              name="playback-mode"
              value="midi"
              checked={mode === "midi"}
              onChange={() => setMode("midi")}
            />
            Transcribed MIDI
          </label>
          {bassUrl && (
            <label>
              <input
                type="radio"
                name="playback-mode"
                value="both"
                checked={mode === "both"}
                onChange={() => setMode("both")}
              />
              Both (A/B)
            </label>
          )}
        </div>
      </div>
      <div className="midi-controls">
        <button type="button" onClick={handlePlay} disabled={playDisabled} aria-label="Play">
          Play
        </button>
        <button type="button" onClick={handlePause} disabled={pauseDisabled} aria-label="Pause">
          Pause
        </button>
        <button type="button" onClick={handleStop} disabled={stopDisabled} aria-label="Stop">
          Stop
        </button>
        <div className="midi-progress" aria-hidden="true">
          <div className="midi-progress-bar" style={{ width: `${pct}%` }} />
        </div>
        <span className="midi-time">
          {formatTime(progress)} / {formatTime(duration)}
        </span>
      </div>
      {bassUrl && (
        <audio
          ref={audioRef}
          src={bassUrl}
          preload="metadata"
          onLoadedMetadata={(e) =>
            setAudioDuration(Number.isFinite(e.currentTarget.duration) ? e.currentTarget.duration : 0)
          }
        />
      )}
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
