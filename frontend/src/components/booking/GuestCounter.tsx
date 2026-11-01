import { AnimatePresence, motion } from "framer-motion";
import { Minus, Plus } from "lucide-react";

interface GuestCounterProps {
  value: number;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
}

export function GuestCounter({ value, onChange, min = 1, max = 10 }: GuestCounterProps) {
  const button =
    "flex h-10 w-10 items-center justify-center rounded-lg text-brand-blue transition hover:bg-brand-light " +
    "active:scale-90 disabled:cursor-not-allowed disabled:text-slate-300 disabled:hover:bg-transparent " +
    "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-cyan/30";

  return (
    <div role="group" aria-label="Number of guests" className="flex h-12 items-center justify-between rounded-xl border border-slate-200 bg-white px-2">
      <button type="button" className={button} onClick={() => onChange(value - 1)} disabled={value <= min} aria-label="Remove a guest">
        <Minus className="h-4 w-4" aria-hidden="true" />
      </button>
      <span className="relative flex h-6 min-w-10 items-center justify-center overflow-hidden text-base font-semibold text-ink" aria-live="polite">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span
            key={value}
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 10, opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            {value} {value === 1 ? "guest" : "guests"}
          </motion.span>
        </AnimatePresence>
      </span>
      <button type="button" className={button} onClick={() => onChange(value + 1)} disabled={value >= max} aria-label="Add a guest">
        <Plus className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}
