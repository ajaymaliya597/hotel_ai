import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition duration-200 " +
  "active:scale-[0.98] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-cyan/40 " +
  "disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-gradient text-white shadow-glow hover:brightness-110",
  secondary: "border border-brand-blue/25 bg-white text-brand-blue hover:border-brand-blue hover:bg-brand-light",
  ghost: "text-brand-blue hover:bg-brand-light",
};

const SIZES: Record<Size, string> = {
  md: "min-h-11 px-5 text-sm",
  lg: "min-h-12 px-7 text-base",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading = false, disabled, type = "button", className = "", children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
});
