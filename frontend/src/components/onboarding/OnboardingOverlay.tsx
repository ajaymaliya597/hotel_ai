import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useOnboarding } from "@/context/OnboardingContext";
import { ONBOARDING_STEPS } from "./onboardingSteps";

export default function OnboardingOverlay() {
  const { isOpen, complete } = useOnboarding();
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1);
  const reduceMotion = useReducedMotion();
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    setIndex(0);
    setDirection(1);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") complete();
    };
    window.addEventListener("keydown", onKey);
    dialogRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, complete]);

  if (!isOpen) return null;

  const step = ONBOARDING_STEPS[index];
  const isLast = index === ONBOARDING_STEPS.length - 1;
  const isWelcome = index === 0;

  const goTo = (next: number) => {
    setDirection(next > index ? 1 : -1);
    setIndex(next);
  };

  const startBooking = () => {
    complete();
    navigate("/booking");
  };

  const slide = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : {
        initial: { opacity: 0, x: direction * 40 },
        animate: { opacity: 1, x: 0 },
        exit: { opacity: 0, x: direction * -40 },
      };

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/60 p-0 backdrop-blur-sm sm:items-center sm:p-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
        className="relative flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-t-3xl bg-white shadow-card outline-none sm:rounded-3xl"
        initial={reduceMotion ? false : { opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <div className="flex items-center justify-between px-6 pt-5">
          <div className="flex gap-1.5" aria-hidden="true">
            {ONBOARDING_STEPS.map((item, dot) => (
              <span
                key={item.id}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  dot === index ? "w-6 bg-brand-gradient" : dot < index ? "w-1.5 bg-brand-cyan" : "w-1.5 bg-slate-200"
                }`}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={complete}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-ink"
          >
            Skip
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 pb-6 pt-6 sm:px-10">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div key={step.id} {...slide} transition={{ duration: 0.28, ease: "easeOut" }} className="text-center">
              <div className="mb-6">{step.visual}</div>
              {step.eyebrow && (
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-brand-blue">{step.eyebrow}</p>
              )}
              <h2 id="onboarding-title" className="text-2xl font-bold text-ink sm:text-3xl">
                {step.title}
              </h2>
              <p className="mx-auto mt-3 max-w-md text-base text-slate-600">{step.body}</p>
              {step.bullets && (
                <ul className="mx-auto mt-6 grid max-w-sm gap-2 text-left">
                  {step.bullets.map((bullet) => (
                    <li key={bullet.text} className="flex items-center gap-3 rounded-xl bg-brand-light px-4 py-3 text-sm font-medium text-ink">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white text-brand-blue">
                        {bullet.icon}
                      </span>
                      {bullet.text}
                    </li>
                  ))}
                </ul>
              )}
              {step.id === "ready" && (
                <span className="mx-auto mt-6 flex h-10 w-10 items-center justify-center rounded-full bg-brand-gradient text-white">
                  <Check className="h-5 w-5" aria-hidden="true" />
                </span>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="flex flex-col gap-3 border-t border-slate-100 px-6 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-10">
          {isWelcome ? (
            <>
              <Button size="lg" onClick={() => goTo(1)} className="w-full sm:w-auto">
                Let&apos;s Book My Stay <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button variant="ghost" onClick={complete} className="w-full sm:w-auto">
                Explore First
              </Button>
            </>
          ) : isLast ? (
            <>
              <Button variant="ghost" onClick={() => goTo(index - 1)} className="w-full sm:w-auto">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back
              </Button>
              <Button size="lg" onClick={startBooking} className="w-full sm:w-auto">
                Start Booking <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" onClick={() => goTo(index - 1)} className="w-full sm:w-auto">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back
              </Button>
              <Button onClick={() => goTo(index + 1)} className="w-full sm:w-auto">
                Next <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
