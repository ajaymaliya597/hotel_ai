import { useCallback, useEffect, useRef, useState } from "react";

const MAX_RECORDING_MS = 30_000;
const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];

export type RecorderState = "idle" | "requesting" | "recording";

export interface VoiceRecorder {
  state: RecorderState;
  level: number;
  supported: boolean;
  start: () => Promise<void>;
  stop: () => Promise<Blob | null>;
  cancel: () => void;
}

function pickMimeType(): string | undefined {
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type));
}

export function useVoiceRecorder(onAutoStop: (blob: Blob) => void): VoiceRecorder {
  const [state, setState] = useState<RecorderState>("idle");
  const [level, setLevel] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const frameRef = useRef<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const onAutoStopRef = useRef(onAutoStop);
  onAutoStopRef.current = onAutoStop;

  const supported = typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia && "MediaRecorder" in window;

  const teardown = useCallback(() => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    frameRef.current = null;
    timerRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    void audioCtxRef.current?.close().catch(() => undefined);
    audioCtxRef.current = null;
    analyserRef.current = null;
    recorderRef.current = null;
    setLevel(0);
    setState("idle");
  }, []);

  const measure = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(data);
    const average = data.reduce((sum, value) => sum + value, 0) / data.length;
    setLevel(Math.min(1, average / 110));
    frameRef.current = requestAnimationFrame(measure);
  }, []);

  const finish = useCallback(
    (autoStop: boolean): Promise<Blob | null> => {
      const recorder = recorderRef.current;
      if (!recorder) return Promise.resolve(null);
      return new Promise((resolve) => {
        recorder.onstop = () => {
          const blob = chunksRef.current.length
            ? new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" })
            : null;
          chunksRef.current = [];
          teardown();
          if (autoStop && blob) onAutoStopRef.current(blob);
          resolve(blob);
        };
        if (recorder.state !== "inactive") recorder.stop();
        else recorder.onstop?.(new Event("stop"));
      });
    },
    [teardown],
  );

  const start = useCallback(async () => {
    if (!supported || recorderRef.current) return;
    setState("requesting");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch {
      setState("idle");
      throw new Error("Microphone access was blocked. Allow microphone access or type your message instead.");
    }
    streamRef.current = stream;

    const mimeType = pickMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    chunksRef.current = [];
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorderRef.current = recorder;

    try {
      const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      ctx.createMediaStreamSource(stream).connect(analyser);
      audioCtxRef.current = ctx;
      analyserRef.current = analyser;
      frameRef.current = requestAnimationFrame(measure);
    } catch {
      // The level meter is decorative; recording works without it.
    }

    recorder.start();
    setState("recording");
    timerRef.current = window.setTimeout(() => {
      void finish(true);
    }, MAX_RECORDING_MS);
  }, [finish, measure, supported]);

  const stop = useCallback(() => finish(false), [finish]);

  const cancel = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder) {
      recorder.ondataavailable = null;
      recorder.onstop = null;
      if (recorder.state !== "inactive") recorder.stop();
    }
    chunksRef.current = [];
    teardown();
  }, [teardown]);

  useEffect(() => () => cancel(), [cancel]);

  return { state, level, supported, start, stop, cancel };
}
