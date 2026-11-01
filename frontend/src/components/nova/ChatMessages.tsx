import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, RotateCcw, Sparkles } from "lucide-react";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  error?: boolean;
  canRetry?: boolean;
}

interface ChatMessagesProps {
  messages: ChatMessage[];
  thinking: boolean;
  onRetry: () => void;
}

export default function ChatMessages({ messages, thinking, onRetry }: ChatMessagesProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, thinking]);

  if (messages.length === 0 && !thinking) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-6 py-12 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-gradient text-white shadow-glow">
          <Sparkles className="h-6 w-6" aria-hidden="true" />
        </span>
        <p className="text-lg font-semibold text-ink">Hi, I'm Nova.</p>
        <p className="max-w-sm text-sm text-slate-600">
          Tell me your dates and number of guests, or ask about rooms. Speak with the microphone or type below.
        </p>
      </div>
    );
  }

  return (
    <ol className="flex flex-col gap-4 p-4 sm:p-6" aria-live="polite" aria-label="Conversation with Nova">
      <AnimatePresence initial={false}>
        {messages.map((message) => {
          const isUser = message.role === "user";
          return (
            <motion.li
              key={message.id}
              layout="position"
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className={`flex ${isUser ? "justify-end" : "justify-start"}`}
            >
              <div className={`max-w-[85%] sm:max-w-[75%] ${isUser ? "" : "flex items-start gap-3"}`}>
                {!isUser && (
                  <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-white" aria-hidden="true">
                    <Sparkles className="h-4 w-4" />
                  </span>
                )}
                <div>
                  <div
                    className={`whitespace-pre-line rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      isUser
                        ? "rounded-br-md bg-brand-gradient text-white shadow-glow"
                        : message.error
                          ? "rounded-bl-md bg-rose-50 text-rose-800 ring-1 ring-rose-100"
                          : "rounded-bl-md bg-brand-light text-ink"
                    }`}
                  >
                    {message.error && <AlertCircle className="mb-1 h-4 w-4" aria-hidden="true" />}
                    {message.text}
                  </div>
                  {message.canRetry && (
                    <button
                      type="button"
                      onClick={onRetry}
                      className="mt-2 inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-semibold text-brand-blue hover:bg-brand-light"
                    >
                      <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Try again
                    </button>
                  )}
                </div>
              </div>
            </motion.li>
          );
        })}
      </AnimatePresence>

      {thinking && (
        <li className="flex justify-start" aria-label="Nova is typing">
          <div className="flex items-center gap-1 rounded-2xl rounded-bl-md bg-brand-light px-4 py-3">
            {[0, 1, 2].map((dot) => (
              <motion.span
                key={dot}
                className="h-2 w-2 rounded-full bg-brand-blue"
                animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
                transition={{ duration: 1, repeat: Infinity, delay: dot * 0.15 }}
              />
            ))}
          </div>
        </li>
      )}
      <div ref={endRef} />
    </ol>
  );
}
