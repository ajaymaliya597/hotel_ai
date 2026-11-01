import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/Button";
import type { Booking } from "@/types/api";
import { formatINR, formatStayDate } from "@/utils/format";

interface BookingConfirmationProps {
  booking: Booking;
  onBookAnother: () => void;
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl bg-slate-50 px-4 py-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-sm font-semibold text-ink">{value}</dd>
    </div>
  );
}

export default function BookingConfirmation({ booking, onBookAnother }: BookingConfirmationProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      aria-labelledby="confirmation-title"
      className="mx-auto w-full max-w-2xl rounded-3xl bg-white p-6 text-center shadow-card ring-1 ring-slate-100 sm:p-10"
    >
      <div className="relative mx-auto flex h-20 w-20 items-center justify-center">
        <motion.span
          className="absolute inset-0 rounded-full bg-brand-cyan/30"
          initial={{ scale: 0.6, opacity: 0.8 }}
          animate={{ scale: 1.6, opacity: 0 }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
        <motion.span
          className="relative flex h-16 w-16 items-center justify-center rounded-full bg-brand-gradient text-white shadow-glow"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 16 }}
        >
          <Check className="h-8 w-8" aria-hidden="true" />
        </motion.span>
      </div>

      <h2 id="confirmation-title" className="mt-6 text-2xl font-bold text-ink sm:text-3xl">Your stay is confirmed!</h2>
      <p className="mt-2 text-slate-600">A summary of your reservation is below. Keep your booking reference handy for any changes.</p>

      <div className="mt-6 rounded-2xl bg-brand-light px-4 py-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-brand-blue">Booking reference</p>
        <p className="mt-1 font-mono text-2xl font-bold tracking-wider text-ink">{booking.booking_code}</p>
      </div>

      <dl className="mt-6 grid gap-3 text-left sm:grid-cols-2">
        <Detail label="Guest" value={booking.guest_name} />
        <Detail label="Room" value={`${booking.room_type} (Room ${booking.room_number})`} />
        <Detail label="Check-in" value={formatStayDate(booking.check_in)} />
        <Detail label="Check-out" value={formatStayDate(booking.check_out)} />
        <Detail label="Guests" value={String(booking.guests)} />
        <Detail label="Total amount" value={formatINR(booking.total_price)} />
      </dl>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Link
          to="/my-bookings"
          className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand-gradient px-6 text-sm font-semibold text-white shadow-glow transition hover:brightness-110 active:scale-[0.98]"
        >
          View my bookings
        </Link>
        <Button variant="secondary" onClick={onBookAnother}>Book another stay</Button>
      </div>
    </motion.section>
  );
}
