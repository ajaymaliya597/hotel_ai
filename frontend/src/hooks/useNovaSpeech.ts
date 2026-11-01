import { useCallback, useEffect, useRef, useState } from "react";
import { fetchNovaSpeech } from "@/services/novaService";
import { isAbortError } from "@/services/apiClient";
import type { NovaLanguage } from "@/types/api";

export interface NovaSpeech {
  speaking: boolean;
  preparing: boolean;
  speak: (text: string, language: NovaLanguage) => Promise<void>;
  interrupt: () => void;
}

export function useNovaSpeech(onError: (message: string) => void): NovaSpeech {
  const [speaking, setSpeaking] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const release = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
    setSpeaking(false);
    setPreparing(false);
  }, []);

  const interrupt = useCallback(() => release(), [release]);

  const speak = useCallback(
    async (text: string, language: NovaLanguage) => {
      release();
      const controller = new AbortController();
      abortRef.current = controller;
      setPreparing(true);
      try {
        const blob = await fetchNovaSpeech(text, language, controller.signal);
        if (controller.signal.aborted) return;
        const url = URL.createObjectURL(blob);
        urlRef.current = url;
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.onended = () => release();
        audio.onerror = () => {
          release();
          onErrorRef.current("Nova's voice could not play. The text reply is still shown above.");
        };
        setPreparing(false);
        setSpeaking(true);
        await audio.play();
      } catch (error) {
        if (isAbortError(error) || controller.signal.aborted) return;
        release();
        onErrorRef.current(error instanceof Error ? error.message : "Nova's voice is unavailable right now.");
      }
    },
    [release],
  );

  useEffect(() => release, [release]);

  return { speaking, preparing, speak, interrupt };
}
