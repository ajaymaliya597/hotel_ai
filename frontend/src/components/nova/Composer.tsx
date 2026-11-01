import { useState, type FormEvent, type KeyboardEvent } from "react";
import { Mic, Send, Square, VolumeOff } from "lucide-react";
import type { RecorderState } from "@/hooks/useVoiceRecorder";

interface ComposerProps {
  disabled: boolean;
  recorderState: RecorderState;
  recorderSupported: boolean;
  speaking: boolean;
  onSendText: (text: string) => void;
  onMicToggle: () => void;
  onStopSpeaking: () => void;
}

export default function Composer({
  disabled, recorderState, recorderSupported, speaking, onSendText, onMicToggle, onStopSpeaking,
}: ComposerProps) {
  const [text, setText] = useState("");
  const recording = recorderState === "recording";
  const requesting = recorderState === "requesting";

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSendText(trimmed);
    setText("");
  };

  const handleKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-slate-100 bg-white p-4 sm:p-5">
      <div className="mb-3 flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={onMicToggle}
          disabled={!recorderSupported || disabled || requesting}
          aria-pressed={recording}
          aria-label={recording ? "Stop recording and send" : "Start speaking to Nova"}
          className={`relative flex h-16 w-16 items-center justify-center rounded-full text-white shadow-glow transition duration-200 active:scale-95 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-cyan/40 disabled:cursor-not-allowed disabled:opacity-50 ${
            recording ? "bg-rose-500 hover:bg-rose-600" : "bg-brand-gradient hover:brightness-110"
          }`}
        >
          {recording && (
            <span className="absolute inset-0 animate-ping rounded-full bg-rose-400/40" aria-hidden="true" />
          )}
          {recording ? <Square className="h-6 w-6 fill-white" aria-hidden="true" /> : <Mic className="h-7 w-7" aria-hidden="true" />}
        </button>
        {speaking && (
          <button
            type="button"
            onClick={onStopSpeaking}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-ink transition hover:border-brand-blue hover:text-brand-blue active:scale-[0.98]"
          >
            <VolumeOff className="h-4 w-4" aria-hidden="true" /> Stop Nova speaking
          </button>
        )}
      </div>
      {!recorderSupported && (
        <p className="mb-3 text-center text-xs text-slate-500">Voice needs a current Chrome, Edge or Safari browser. You can type below instead.</p>
      )}

      <form onSubmit={submit} className="flex items-end gap-3">
        <label className="sr-only" htmlFor="nova-input">Message to Nova</label>
        <textarea
          id="nova-input"
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKey}
          rows={1}
          maxLength={4000}
          disabled={disabled}
          placeholder="Type a message, e.g. 2 guests from 12 Nov for 2 nights"
          className="max-h-32 min-h-12 flex-1 resize-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-brand-blue focus:ring-4 focus:ring-brand-cyan/25 disabled:bg-slate-50"
        />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          aria-label="Send message"
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-gradient text-white shadow-glow transition hover:brightness-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send className="h-5 w-5" aria-hidden="true" />
        </button>
      </form>
    </div>
  );
}
