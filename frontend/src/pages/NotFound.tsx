import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <div className="container-page flex min-h-[60vh] flex-col items-center justify-center gap-4 py-20 text-center">
      <p className="text-sm font-semibold uppercase tracking-wider text-brand-blue">Page not found</p>
      <h1 className="text-3xl font-bold text-ink">We couldn&apos;t find that page.</h1>
      <p className="text-slate-600">The link may be out of date. Head back to the home page to continue.</p>
      <Link to="/">
        <Button>Back to home</Button>
      </Link>
    </div>
  );
}
