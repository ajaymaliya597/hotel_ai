import { apiBlob, apiFetch } from "./apiClient";
import type { NovaHistoryItem, NovaLanguage, NovaMode, NovaTurnResponse } from "@/types/api";

const NOVA_TURN_TIMEOUT_MS = 90_000;
const SPEECH_TIMEOUT_MS = 45_000;

interface NovaTurnInput {
  language: NovaLanguage;
  history: NovaHistoryItem[];
  mode: NovaMode;
  turnId: string;
}

function appendTurnFields(form: FormData, input: NovaTurnInput): void {
  form.append("language", input.language);
  form.append("history", JSON.stringify(input.history.slice(-40)));
  form.append("mode", input.mode);
  form.append("client_turn_id", input.turnId);
}

export function sendNovaText(message: string, input: NovaTurnInput, signal?: AbortSignal): Promise<NovaTurnResponse> {
  const form = new FormData();
  form.append("message", message);
  appendTurnFields(form, input);
  return apiFetch<NovaTurnResponse>("/api/chat", { method: "POST", body: form, signal }, NOVA_TURN_TIMEOUT_MS);
}

export function sendNovaVoice(audio: Blob, input: NovaTurnInput, signal?: AbortSignal): Promise<NovaTurnResponse> {
  const form = new FormData();
  form.append("audio", audio, "nova-recording.webm");
  appendTurnFields(form, input);
  return apiFetch<NovaTurnResponse>("/api/voice", { method: "POST", body: form, signal }, NOVA_TURN_TIMEOUT_MS);
}

export function fetchNovaSpeech(text: string, language: NovaLanguage, signal?: AbortSignal): Promise<Blob> {
  const form = new FormData();
  form.append("text", text);
  form.append("language", language);
  return apiBlob("/api/tts", form, signal, SPEECH_TIMEOUT_MS);
}
