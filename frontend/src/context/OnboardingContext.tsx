import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

const STORAGE_KEY = "nova-hotel.onboarding.completed";

interface OnboardingContextValue {
  isOpen: boolean;
  open: () => void;
  complete: () => void;
}

const OnboardingContext = createContext<OnboardingContextValue | null>(null);

function readCompleted(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function writeCompleted(): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, "true");
  } catch {
    // Storage can be blocked (private mode); the overlay simply appears again next visit.
  }
}

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(() => !readCompleted());

  const open = useCallback(() => setIsOpen(true), []);
  const complete = useCallback(() => {
    writeCompleted();
    setIsOpen(false);
  }, []);

  const value = useMemo(() => ({ isOpen, open, complete }), [isOpen, open, complete]);
  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}

export function useOnboarding(): OnboardingContextValue {
  const context = useContext(OnboardingContext);
  if (!context) throw new Error("useOnboarding must be used inside OnboardingProvider");
  return context;
}
