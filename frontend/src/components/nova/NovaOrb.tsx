import { motion } from "framer-motion";
import { Mic, Sparkles, Volume2 } from "lucide-react";

export type NovaVisualState = "idle" | "listening" | "thinking" | "speaking";

interface NovaOrbProps {
  state: NovaVisualState;
  level: number;
}

const LABELS: Record<NovaVisualState, string> = {
  idle: "Ready when you are",
  listening: "Listening...",
  thinking: "Thinking...",
  speaking: "Speaking...",
};

const BAR_WEIGHTS = [0.5, 0.8, 1, 0.8, 0.5];

export default function NovaOrb({ state, level }: NovaOrbProps) {
  const active = state !== "idle";
  const ringColor = state === "listening" ? "border-brand-cyan/60" : "border-brand-blue/40";

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative flex h-36 w-36 items-center justify-center" aria-hidden="true">
        {active &&
          [0, 1].map((ring) => (
            <motion.span
              key={ring}
              className={`absolute inset-0 rounded-full border-2 ${ringColor}`}
              animate={{ scale: [0.85, 1.3], opacity: [0.6, 0] }}
              transition={{ duration: 2, repeat: Infinity, delay: ring, ease: "easeOut" }}
            />
          ))}
        <motion.span
          className="relative flex h-24 w-24 items-center justify-center rounded-full bg-brand-gradient text-white shadow-glow"
          animate={state === "listening" ? { scale: 1 + level * 0.25 } : { scale: [1, 1.04, 1] }}
          transition={state === "listening" ? { duration: 0.1 } : { duration: 3, repeat: Infinity, ease: "easeInOut" }}
        >
          {state === "speaking" ? <Volume2 className="h-9 w-9" /> : state === "listening" ? <Mic className="h-9 w-9" /> : <Sparkles className="h-9 w-9" />}
        </motion.span>
      </div>

      <div className="flex h-8 items-center gap-1" aria-hidden="true">
        {BAR_WEIGHTS.map((weight, index) => {
          const height = state === "listening" ? 4 + level * 28 * weight : active ? 4 + 8 * weight : 4;
          return (
            <motion.span
              key={index}
              className="w-1.5 rounded-full bg-brand-gradient"
              animate={{ height }}
              transition={{ duration: 0.12, ease: "easeOut" }}
            />
          );
        })}
      </div>

      <p className="text-sm font-semibold text-ink" role="status">{LABELS[state]}</p>
    </div>
  );
}
