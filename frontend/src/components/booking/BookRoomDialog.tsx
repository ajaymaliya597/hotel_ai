import { useEffect, useState, type FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import type { Room } from "@/types/api";
import { formatINR, formatStayDate } from "@/utils/format";

export interface GuestDetails {
  guestName: string;
  phone: string;
  specialRequests: string;
}

interface BookRoomDialogProps {
  room: Room;
  checkIn: string;
  checkOut: string;
  guests: number;
  nights: number;
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (details: GuestDetails) => void;
}

const FIELD_CLASS =
  "h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-ink outline-none transition " +
  "placeholder:text-slate-400 focus:border-brand-blue focus:ring-4 focus:ring-brand-cyan/25";

export default function BookRoomDialog({
  room, checkIn, checkOut, guests, nights, submitting, error, onClose, onSubmit,
}: BookRoomDialogProps) {
  const [guestName, setGuestName] = useState("");
  const [phone, setPhone] = useState("");
  const [specialRequests, setSpecialRequests] = useState("");
  const [validation, setValidation] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !submitting) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, submitting]);

  const pricePerNight = Number(room.price_per_night);
  const total = pricePerNight * nights;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (guestName.trim().length < 2) {
      setValidation("Enter the guest's full name.");
      return;
    }
    if (phone.replace(/\D/g, "").length < 10) {
      setValidation("Enter a mobile number with at least 10 digits.");
      return;
    }
    setValidation(null);
    onSubmit({ guestName: guestName.trim(), phone: phone.trim(), specialRequests: specialRequests.trim() });
  };

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-end justify-center bg-ink/60 backdrop-blur-sm sm:items-center sm:p-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={() => !submitting && onClose()}
      >
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-labelledby="book-room-title"
          className="flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-t-3xl bg-white shadow-card sm:rounded-3xl"
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 32 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          onClick={(event) => event.stopPropagation()}
        >
          <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-brand-blue">Step 3 of 4</p>
              <h2 id="book-room-title" className="mt-1 text-xl font-bold text-ink">Your details</h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              aria-label="Close"
              className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-ink disabled:opacity-50"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>

          <form onSubmit={handleSubmit} noValidate className="flex flex-1 flex-col gap-5 overflow-y-auto px-6 py-5">
            <div className="rounded-2xl bg-brand-light p-4 text-sm">
              <p className="font-semibold text-ink">{room.room_type} - Room {room.room_number}</p>
              <p className="mt-1 text-slate-600">
                {formatStayDate(checkIn)} to {formatStayDate(checkOut)} · {guests} {guests === 1 ? "guest" : "guests"}
              </p>
              <div className="mt-3 flex items-center justify-between border-t border-brand-blue/10 pt-3">
                <span className="text-slate-600">{formatINR(pricePerNight)} x {nights} {nights === 1 ? "night" : "nights"}</span>
                <span className="text-lg font-bold text-ink">{formatINR(total)}</span>
              </div>
            </div>

            <label className="grid gap-2 text-sm font-medium text-ink">
              Full name
              <input
                className={FIELD_CLASS}
                value={guestName}
                onChange={(event) => setGuestName(event.target.value)}
                autoComplete="name"
                autoFocus
                maxLength={120}
                required
              />
            </label>
            <label className="grid gap-2 text-sm font-medium text-ink">
              Mobile number
              <input
                className={FIELD_CLASS}
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                autoComplete="tel"
                inputMode="tel"
                placeholder="10-digit mobile number"
                maxLength={20}
                required
              />
            </label>
            <label className="grid gap-2 text-sm font-medium text-ink">
              Special requests <span className="font-normal text-slate-500">(optional)</span>
              <textarea
                className="min-h-20 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-brand-blue focus:ring-4 focus:ring-brand-cyan/25"
                value={specialRequests}
                onChange={(event) => setSpecialRequests(event.target.value)}
                maxLength={1000}
              />
            </label>

            {(validation || error) && (
              <p role="alert" className="rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
                {validation ?? error}
              </p>
            )}

            <div className="mt-auto flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
              <Button variant="secondary" onClick={onClose} disabled={submitting} className="w-full sm:w-auto">
                Back
              </Button>
              <Button type="submit" size="lg" loading={submitting} className="w-full sm:w-auto">
                Confirm booking
              </Button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
