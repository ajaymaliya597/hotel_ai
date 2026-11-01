import { Link } from "react-router-dom";
import { CircleHelp, Sparkles } from "lucide-react";
import { useOnboarding } from "@/context/OnboardingContext";

export default function Footer() {
  const { open } = useOnboarding();
  return (
    <footer className="mt-24 border-t border-slate-200 bg-white">
      <div className="container-page grid gap-10 py-12 sm:grid-cols-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient text-white">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="text-lg font-bold text-ink">Nova Hotel</span>
          </div>
          <p className="mt-3 max-w-xs text-sm text-slate-600">
            Comfortable stays, effortless bookings and personal help from Nova, our AI hotel assistant.
          </p>
        </div>
        <nav aria-label="Footer" className="flex flex-col gap-3 text-sm">
          <Link to="/booking" className="text-slate-600 hover:text-brand-blue">Find a room</Link>
          <Link to="/nova" className="text-slate-600 hover:text-brand-blue">Talk to Nova</Link>
          <Link to="/my-bookings" className="text-slate-600 hover:text-brand-blue">My bookings</Link>
        </nav>
        <div className="flex flex-col gap-3 text-sm">
          <button
            type="button"
            onClick={open}
            className="inline-flex w-fit items-center gap-2 text-slate-600 hover:text-brand-blue"
          >
            <CircleHelp className="h-4 w-4" aria-hidden="true" />
            Replay the Nova introduction
          </button>
          <a href="/admin" className="text-slate-600 hover:text-brand-blue">Staff admin portal</a>
        </div>
      </div>
      <div className="border-t border-slate-100 py-5 text-center text-xs text-slate-500">
        © {new Date().getFullYear()} Nova Hotel. All rights reserved.
      </div>
    </footer>
  );
}
