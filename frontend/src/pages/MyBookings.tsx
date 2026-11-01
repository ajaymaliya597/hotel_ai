import { useState, type FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CalendarDays, Search, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cancelBooking, lookupBookings } from "@/services/bookingService";
import { errorMessage } from "@/services/apiClient";
import type { Booking } from "@/types/api";
import { formatINR, formatStayDate, todayISO } from "@/utils/format";

const FIELD_CLASS =
  "h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-ink outline-none transition " +
  "placeholder:text-slate-400 focus:border-brand-blue focus:ring-4 focus:ring-brand-cyan/25";

const STATUS_STYLES: Record<Booking["status"], { label: string; className: string }> = {
  confirmed: { label: "Confirmed", className: "bg-emerald-50 text-emerald-700 ring-emerald-100" },
  pending_confirmation: { label: "Awaiting confirmation", className: "bg-amber-50 text-amber-800 ring-amber-100" },
  cancelled: { label: "Cancelled", className: "bg-slate-100 text-slate-600 ring-slate-200" },
};

interface Identity {
  guestName: string;
  phone: string;
}

export default function MyBookings() {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [form, setForm] = useState<Identity>({ guestName: "", phone: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pendingCancel, setPendingCancel] = useState<Booking | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = async (who: Identity) => {
    setLoading(true);
    setLoadError(null);
    try {
      const result = await lookupBookings({ guestName: who.guestName, phone: who.phone });
      setBookings(result.bookings);
    } catch (error) {
      setBookings([]);
      setLoadError(errorMessage(error, "We could not load your bookings. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  const handleLookup = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const guestName = form.guestName.trim();
    const phone = form.phone.trim();
    if (guestName.length < 2) {
      setFormError("Enter the name used for the booking.");
      return;
    }
    if (phone.replace(/\D/g, "").length < 10) {
      setFormError("Enter the mobile number used for the booking.");
      return;
    }
    setFormError(null);
    setNotice(null);
    const who = { guestName, phone };
    setIdentity(who);
    void load(who);
  };

  const handleCancel = async () => {
    if (!pendingCancel || !identity) return;
    setCancelling(true);
    setCancelError(null);
    try {
      const result = await cancelBooking(pendingCancel.booking_code, identity);
      setNotice(`Booking ${result.booking_code} has been cancelled.`);
      setPendingCancel(null);
      await load(identity);
    } catch (error) {
      setCancelError(errorMessage(error, "We could not cancel this booking. Please try again."));
    } finally {
      setCancelling(false);
    }
  };

  const canCancel = (booking: Booking) => booking.status === "confirmed" && booking.check_in >= todayISO();

  return (
    <div className="container-page py-10 sm:py-14">
      <header className="mb-8 max-w-2xl">
        <p className="text-sm font-semibold uppercase tracking-wider text-brand-blue">My bookings</p>
        <h1 className="mt-2 text-3xl font-bold text-ink sm:text-4xl">Find your reservations</h1>
        <p className="mt-3 text-slate-600">Enter the name and mobile number used when you booked. We show only bookings that match both.</p>
      </header>

      <form onSubmit={handleLookup} noValidate className="grid gap-4 rounded-2xl bg-white p-5 shadow-card ring-1 ring-slate-100 sm:grid-cols-[1fr_1fr_auto] sm:items-end sm:p-6">
        <label className="grid gap-2 text-sm font-medium text-ink">
          Full name
          <input className={FIELD_CLASS} value={form.guestName} onChange={(e) => setForm({ ...form, guestName: e.target.value })} autoComplete="name" maxLength={120} />
        </label>
        <label className="grid gap-2 text-sm font-medium text-ink">
          Mobile number
          <input className={FIELD_CLASS} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} inputMode="tel" autoComplete="tel" maxLength={20} />
        </label>
        <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
          <Search className="h-4 w-4" aria-hidden="true" /> Find bookings
        </Button>
        {formError && <p role="alert" className="text-sm font-medium text-rose-700 sm:col-span-3">{formError}</p>}
      </form>

      {notice && (
        <p role="status" className="mt-6 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">{notice}</p>
      )}

      <section aria-live="polite" className="mt-8">
        {loadError && (
          <div role="alert" className="flex flex-col gap-3 rounded-2xl bg-rose-50 p-6 ring-1 ring-rose-100 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-medium text-rose-800">{loadError}</p>
            <Button variant="secondary" onClick={() => identity && load(identity)}>Try again</Button>
          </div>
        )}

        {identity && !loading && !loadError && bookings.length === 0 && (
          <div className="rounded-2xl bg-white p-10 text-center shadow-card ring-1 ring-slate-100">
            <p className="text-lg font-semibold text-ink">No bookings found</p>
            <p className="mt-2 text-sm text-slate-600">Check the name and mobile number, or make a new booking.</p>
          </div>
        )}

        <div className="grid gap-5">
          {bookings.map((booking, index) => (
            <motion.article
              key={booking.booking_code}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05, duration: 0.3 }}
              className="grid gap-5 rounded-2xl bg-white p-5 shadow-card ring-1 ring-slate-100 sm:p-6 md:grid-cols-[1fr_auto]"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-mono text-sm font-bold tracking-wider text-ink">{booking.booking_code}</span>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${STATUS_STYLES[booking.status].className}`}>
                    {STATUS_STYLES[booking.status].label}
                  </span>
                </div>
                <h2 className="mt-3 text-lg font-bold text-ink">{booking.room_type} <span className="font-medium text-slate-500">· Room {booking.room_number}</span></h2>
                <p className="mt-2 flex items-center gap-2 text-sm text-slate-600">
                  <CalendarDays className="h-4 w-4 text-brand-blue" aria-hidden="true" />
                  {formatStayDate(booking.check_in)} to {formatStayDate(booking.check_out)}
                </p>
                <p className="mt-1 text-sm text-slate-600">{booking.guests} {booking.guests === 1 ? "guest" : "guests"} · {booking.guest_name}</p>
              </div>
              <div className="flex flex-col items-start gap-3 md:items-end md:justify-between">
                <p className="text-xl font-bold text-ink">{formatINR(booking.total_price)}</p>
                {canCancel(booking) && (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setCancelError(null);
                      setPendingCancel(booking);
                    }}
                  >
                    Cancel booking
                  </Button>
                )}
              </div>
            </motion.article>
          ))}
        </div>
      </section>

      <AnimatePresence>
        {pendingCancel && (
          <motion.div
            className="fixed inset-0 z-50 flex items-end justify-center bg-ink/60 backdrop-blur-sm sm:items-center sm:p-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => !cancelling && setPendingCancel(null)}
          >
            <motion.div
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="cancel-title"
              onClick={(event) => event.stopPropagation()}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 24 }}
              className="w-full max-w-md rounded-t-3xl bg-white p-6 shadow-card sm:rounded-3xl"
            >
              <div className="flex items-start justify-between gap-4">
                <h2 id="cancel-title" className="text-xl font-bold text-ink">Cancel this booking?</h2>
                <button type="button" aria-label="Close" onClick={() => setPendingCancel(null)} disabled={cancelling} className="rounded-lg p-1 text-slate-500 hover:bg-slate-100">
                  <X className="h-5 w-5" aria-hidden="true" />
                </button>
              </div>
              <p className="mt-3 text-sm text-slate-600">
                Booking <span className="font-mono font-semibold text-ink">{pendingCancel.booking_code}</span> for {pendingCancel.room_type}, {formatStayDate(pendingCancel.check_in)} to {formatStayDate(pendingCancel.check_out)}, will be cancelled. This cannot be undone from this page.
              </p>
              {cancelError && <p role="alert" className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{cancelError}</p>}
              <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <Button variant="secondary" onClick={() => setPendingCancel(null)} disabled={cancelling}>Keep booking</Button>
                <Button onClick={handleCancel} loading={cancelling}>Yes, cancel booking</Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
