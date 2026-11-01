import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { addDays, todayISO } from "@/utils/format";
import { GuestCounter } from "./GuestCounter";

export interface StaySearch {
  checkIn: string;
  checkOut: string;
  guests: number;
}

interface StaySearchFormProps {
  initial: StaySearch;
  onSubmit: (search: StaySearch) => void;
  loading?: boolean;
  submitLabel?: string;
}

const FIELD_CLASS =
  "h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-ink outline-none transition " +
  "focus:border-brand-blue focus:ring-4 focus:ring-brand-cyan/25";

export default function StaySearchForm({ initial, onSubmit, loading = false, submitLabel = "Search rooms" }: StaySearchFormProps) {
  const [values, setValues] = useState<StaySearch>(initial);
  const [error, setError] = useState<string | null>(null);
  const today = todayISO();

  const handleCheckIn = (checkIn: string) => {
    setValues((current) => ({
      ...current,
      checkIn,
      checkOut: current.checkOut > checkIn ? current.checkOut : addDays(checkIn, 1),
    }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!values.checkIn || !values.checkOut) {
      setError("Choose both check-in and check-out dates.");
      return;
    }
    if (values.checkIn < today) {
      setError("Check-in cannot be in the past.");
      return;
    }
    if (values.checkOut <= values.checkIn) {
      setError("Check-out must be after check-in.");
      return;
    }
    setError(null);
    onSubmit(values);
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="grid gap-4" aria-label="Search for rooms">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-1">
        <label className="grid gap-2 text-sm font-medium text-ink">
          Check-in
          <input
            type="date"
            className={FIELD_CLASS}
            min={today}
            value={values.checkIn}
            onChange={(event) => handleCheckIn(event.target.value)}
            required
          />
        </label>
        <label className="grid gap-2 text-sm font-medium text-ink">
          Check-out
          <input
            type="date"
            className={FIELD_CLASS}
            min={addDays(values.checkIn || today, 1)}
            value={values.checkOut}
            onChange={(event) => setValues((current) => ({ ...current, checkOut: event.target.value }))}
            required
          />
        </label>
      </div>
      <div className="grid gap-2 text-sm font-medium text-ink">
        <span id="guest-label">Guests</span>
        <GuestCounter value={values.guests} onChange={(guests) => setValues((current) => ({ ...current, guests }))} />
      </div>
      {error && (
        <p role="alert" className="rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
          {error}
        </p>
      )}
      <Button type="submit" size="lg" loading={loading} className="w-full">
        {submitLabel}
      </Button>
    </form>
  );
}
