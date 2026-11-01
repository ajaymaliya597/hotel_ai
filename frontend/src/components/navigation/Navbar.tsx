import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { CircleHelp, Menu, Sparkles, X } from "lucide-react";
import { useOnboarding } from "@/context/OnboardingContext";

const LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/booking", label: "Book a stay", end: false },
  { to: "/nova", label: "Talk to Nova", end: false },
  { to: "/my-bookings", label: "My bookings", end: false },
];

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { open: openOnboarding } = useOnboarding();
  const location = useLocation();

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `relative rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive ? "text-brand-blue" : "text-slate-600 hover:text-ink"
    }`;

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/85 backdrop-blur-md">
      <div className="container-page flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 rounded-lg focus-visible:ring-4 focus-visible:ring-brand-cyan/40 focus-visible:outline-none">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient text-white shadow-glow">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
          </span>
          <span className="text-lg font-bold tracking-tight text-ink">Nova Hotel</span>
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={linkClass}>
              {({ isActive }) => (
                <>
                  {link.label}
                  <span
                    className={`absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-brand-gradient transition-transform duration-300 ${
                      isActive ? "scale-x-100" : "scale-x-0"
                    }`}
                  />
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={openOnboarding}
            className="hidden items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-brand-light hover:text-brand-blue md:inline-flex"
          >
            <CircleHelp className="h-4 w-4" aria-hidden="true" />
            Help
          </button>
          <Link
            to="/booking"
            className="hidden h-10 items-center rounded-xl bg-brand-gradient px-5 text-sm font-semibold text-white shadow-glow transition hover:brightness-110 active:scale-[0.98] md:inline-flex"
          >
            Book now
          </Link>
          <button
            type="button"
            onClick={() => setMenuOpen((value) => !value)}
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            className="flex h-10 w-10 items-center justify-center rounded-xl text-ink transition hover:bg-brand-light md:hidden"
          >
            {menuOpen ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav id="mobile-menu" aria-label="Mobile" className="border-t border-slate-200 bg-white px-5 py-4 md:hidden">
          <div className="flex flex-col gap-1">
            {LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `rounded-xl px-4 py-3 text-base font-medium ${
                    isActive ? "bg-brand-light text-brand-blue" : "text-ink hover:bg-slate-50"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                openOnboarding();
              }}
              className="flex items-center gap-2 rounded-xl px-4 py-3 text-left text-base font-medium text-ink hover:bg-slate-50"
            >
              <CircleHelp className="h-4 w-4" aria-hidden="true" />
              Replay the Nova introduction
            </button>
          </div>
        </nav>
      )}
    </header>
  );
}
