import { Fragment } from "react";
import { motion } from "framer-motion";
import { Check } from "lucide-react";

const STEPS = ["Dates & guests", "Choose room", "Your details", "Confirmed"];

export default function BookingStepper({ current }: { current: number }) {
  const progress = (current / (STEPS.length - 1)) * 100;

  return (
    <nav aria-label="Booking progress" className="w-full">
      <ol className="flex items-start justify-between gap-2">
        {STEPS.map((label, index) => {
          const done = index < current;
          const active = index === current;
          return (
            <Fragment key={label}>
              <li className="flex min-w-0 flex-col items-center gap-2 text-center" aria-current={active ? "step" : undefined}>
                <span
                  className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold transition-colors duration-300 ${
                    done || active ? "bg-brand-gradient text-white shadow-glow" : "bg-slate-200 text-slate-600"
                  }`}
                >
                  {done ? <Check className="h-4 w-4" aria-hidden="true" /> : index + 1}
                </span>
                <span className={`text-xs sm:text-sm ${active ? "font-semibold text-ink" : "text-slate-500"}`}>{label}</span>
              </li>
            </Fragment>
          );
        })}
      </ol>
      <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-slate-200" aria-hidden="true">
        <motion.div
          className="h-full rounded-full bg-brand-gradient"
          initial={false}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
    </nav>
  );
}
