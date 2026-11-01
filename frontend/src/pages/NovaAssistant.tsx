import { useCallback, useRef, useState } from "react";
import { CalendarDays, CircleAlert, RotateCcw, X } from "lucide-react";
import ChatMessages, { type ChatMessage } from "@/components/nova/ChatMessages";
import Composer from "@/components/nova/Composer";
import NovaOrb, { type NovaVisualState } from "@/components/nova/NovaOrb";
import { useNovaSpeech } from "@/hooks/useNovaSpeech";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import { errorMessage, isAbortError } from "@/services/apiClient";
import { sendNovaText, sendNovaVoice } from "@/services/novaService";
import type { NovaHistoryItem, NovaLanguage, NovaMode } from "@/types/api";

type Attempt = { kind: "text"; text: string } | { kind: "voice"; blob: Blob };

const LANGUAGES: { value: NovaLanguage; label: string }[] = [
  { value: "auto", label: "Auto-detect" },
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi" },
  { value: "hinglish", label: "Hinglish" },
  { value: "ta", label: "Tamil" },
  { value: "te", label: "Telugu" },
];

const MODES: { value: NovaMode; label: string; hint: string }[] = [
  { value: "booking", label: "Book a hotel", hint: "Find rooms and reserve a stay" },
  { value: "cancel", label: "Cancel booking", hint: "Cancel an existing reservation" },
];

function nextId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

function toHistory(messages: ChatMessage[]): NovaHistoryItem[] {
  return messages
    .filter((message) => !message.error)
    .map((message) => ({ role: message.role, content: message.text }));
}

export default function NovaAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [thinking, setThinking] = useState(false);
  const [mode, setMode] = useState<NovaMode>("booking");
  const [language, setLanguage] = useState<NovaLanguage>("auto");
  const [banner, setBanner] = useState<string | null>(null);

  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const attemptsRef = useRef(new Map<string, Attempt>());
  const abortRef = useRef<AbortController | null>(null);
  const languageRef = useRef(language);
  languageRef.current = language;
  const modeRef = useRef(mode);
  modeRef.current = mode;

  const speech = useNovaSpeech(setBanner);

  const pushError = useCallback((message: string, attempt: Attempt) => {
    const id = nextId("error");
    attemptsRef.current.set(id, attempt);
    setMessages((prev) => [...prev, { id, role: "assistant", text: message, error: true, canRetry: true }]);
  }, []);

  const runTurn = useCallback(
    async (attempt: Attempt) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const turnId = typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
      const input = {
        language: languageRef.current,
        history: toHistory(messagesRef.current),
        mode: modeRef.current,
        turnId,
      };
      setBanner(null);
      setThinking(true);

      const userId = nextId("user");
      if (attempt.kind === "text") {
        setMessages((prev) => [...prev, { id: userId, role: "user", text: attempt.text }]);
      }

      try {
        const response =
          attempt.kind === "text"
            ? await sendNovaText(attempt.text, input, controller.signal)
            : await sendNovaVoice(attempt.blob, input, controller.signal);
        if (controller.signal.aborted) return;

        setMessages((prev) => {
          const withUser =
            attempt.kind === "voice"
              ? [...prev, { id: userId, role: "user" as const, text: response.transcript || "Voice message" }]
              : prev;
          return [...withUser, { id: nextId("assistant"), role: "assistant", text: response.reply }];
        });
        if (attempt.kind === "voice") {
          void speech.speak(response.spoken_reply || response.reply, languageRef.current);
        }
      } catch (error) {
        if (isAbortError(error) || controller.signal.aborted) return;
        if (attempt.kind === "text") {
          setMessages((prev) => prev.filter((message) => message.id !== userId));
        }
        pushError(errorMessage(error, "Nova could not reply just now. Please try again."), attempt);
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
          setThinking(false);
        }
      }
    },
    [pushError, speech],
  );

  const recorder = useVoiceRecorder((blob) => {
    void runTurn({ kind: "voice", blob });
  });

  const handleMicToggle = async () => {
    if (recorder.state === "recording") {
      const blob = await recorder.stop();
      if (blob && blob.size > 0) void runTurn({ kind: "voice", blob });
      return;
    }
    speech.interrupt();
    try {
      await recorder.start();
    } catch (error) {
      setBanner(errorMessage(error, "The microphone is unavailable. Type your message instead."));
    }
  };

  const handleSendText = (text: string) => {
    speech.interrupt();
    void runTurn({ kind: "text", text });
  };

  const handleRetry = (errorId: string) => {
    const attempt = attemptsRef.current.get(errorId);
    attemptsRef.current.delete(errorId);
    setMessages((prev) => prev.filter((message) => message.id !== errorId));
    if (attempt) void runTurn(attempt);
  };

  const resetConversation = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setThinking(false);
    speech.interrupt();
    recorder.cancel();
    attemptsRef.current.clear();
    setMessages([]);
    setBanner(null);
  };

  const handleModeChange = (next: NovaMode) => {
    if (next === mode) return;
    resetConversation();
    setMode(next);
  };

  const visualState: NovaVisualState =
    recorder.state === "recording" ? "listening" : thinking ? "thinking" : speech.speaking ? "speaking" : "idle";

  const busy = thinking || recorder.state !== "idle";

  return (
    <div className="container-page py-8 sm:py-12">
      <header className="mb-8 flex flex-col gap-2">
        <p className="text-sm font-semibold uppercase tracking-wider text-brand-blue">Nova assistant</p>
        <h1 className="text-3xl font-bold text-ink sm:text-4xl">Talk to Nova</h1>
        <p className="max-w-2xl text-slate-600">
          Book or cancel a stay by voice or text. Nova checks real availability and reads back every detail before anything is saved.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr] lg:items-start">
        <aside className="flex flex-col gap-6 rounded-3xl bg-white p-6 shadow-card ring-1 ring-slate-100">
          <NovaOrb state={visualState} level={recorder.level} />

          <div className="flex flex-col gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500" id="nova-mode-label">What do you need?</span>
            <div role="radiogroup" aria-labelledby="nova-mode-label" className="grid grid-cols-2 gap-2 rounded-2xl bg-slate-100 p-1">
              {MODES.map((option) => {
                const active = option.value === mode;
                return (
                  <button
                    key={option.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => handleModeChange(option.value)}
                    className={`rounded-xl px-3 py-2.5 text-sm font-semibold transition duration-200 active:scale-[0.98] ${
                      active ? "bg-white text-brand-blue shadow-card" : "text-slate-600 hover:text-ink"
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
            <p className="flex items-center gap-2 text-xs text-slate-500">
              <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
              {MODES.find((option) => option.value === mode)?.hint}
            </p>
          </div>

          <label className="flex flex-col gap-2 text-sm font-medium text-ink">
            Language
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value as NovaLanguage)}
              disabled={busy}
              className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm text-ink outline-none focus:border-brand-blue focus:ring-4 focus:ring-brand-cyan/25 disabled:opacity-60"
            >
              {LANGUAGES.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </aside>

        <section className="flex min-h-[32rem] flex-col overflow-hidden rounded-3xl bg-white shadow-card ring-1 ring-slate-100 lg:h-[calc(100vh-14rem)]" aria-label="Nova conversation">
          {banner && (
            <div role="alert" className="flex items-start justify-between gap-3 border-b border-amber-100 bg-amber-50 px-5 py-3 text-sm text-amber-900">
              <span className="flex items-start gap-2">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                {banner}
              </span>
              <button type="button" onClick={() => setBanner(null)} aria-label="Dismiss" className="rounded-md p-1 hover:bg-amber-100">
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            <ChatMessages
              messages={messages}
              thinking={thinking}
              onRetry={() => {
                const lastError = [...messages].reverse().find((message) => message.canRetry);
                if (lastError) handleRetry(lastError.id);
              }}
            />
          </div>

          {messages.length > 0 && !busy && (
            <div className="flex justify-end px-5">
              <button
                type="button"
                onClick={resetConversation}
                className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-semibold text-slate-500 hover:bg-slate-100 hover:text-ink"
                title="Clear this conversation"
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Clear conversation
              </button>
            </div>
          )}

          <Composer
            disabled={thinking}
            recorderState={recorder.state}
            recorderSupported={recorder.supported}
            speaking={speech.speaking || speech.preparing}
            onSendText={handleSendText}
            onMicToggle={() => void handleMicToggle()}
            onStopSpeaking={speech.interrupt}
          />
        </section>
      </div>
    </div>
  );
}
