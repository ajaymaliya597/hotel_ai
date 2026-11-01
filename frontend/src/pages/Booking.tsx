import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, BedDouble } from "lucide-react";
import StaySearchForm, { type StaySearch } from "@/components/booking/StaySearchForm";
import BookingStepper from "@/components/booking/BookingStepper";
import BookRoomDialog, { type GuestDetails } from "@/components/booking/BookRoomDialog";
import BookingConfirmation from "@/components/booking/BookingConfirmation";
import RoomCard from "@/components/rooms/RoomCard";
import { Button } from "@/components/ui/Button";
import { ApiError, errorMessage, isAbortError } from "@/services/apiClient";
import { createBooking, fetchAvailableRooms } from "@/services/bookingService";
import type { Booking, Room } from "@/types/api";
import { addDays, isValidISODate, nightsBetween, todayISO } from "@/utils/format";

type RoomsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; rooms: Room[] };

function defaultSearch(): StaySearch {
  const checkIn = addDays(todayISO(), 1);
  return { checkIn, checkOut: addDays(checkIn, 1), guests: 2 };
}

function searchFromParams(params: URLSearchParams, fallback: StaySearch): StaySearch {
  const checkIn = params.get("check_in");
  const checkOut = params.get("check_out");
  const guests = Number(params.get("guests") ?? fallback.guests);
  const valid =
    isValidISODate(checkIn) &&
    isValidISODate(checkOut) &&
    checkIn >= todayISO() &&
    checkOut > checkIn &&
    Number.isInteger(guests) &&
    guests >= 1 &&
    guests <= 10;
  return valid ? { checkIn, checkOut, guests } : fallback;
}

export default function Booking() {
  const [params, setParams] = useSearchParams();
  const fallback = useMemo(defaultSearch, []);
  const search = useMemo(() => searchFromParams(params, fallback), [params, fallback]);

  const [roomsState, setRoomsState] = useState<RoomsState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState<Booking | null>(null);

  const nights = nightsBetween(search.checkIn, search.checkOut);

  useEffect(() => {
    const controller = new AbortController();
    setRoomsState({ status: "loading" });
    fetchAvailableRooms({ checkIn: search.checkIn, checkOut: search.checkOut, guests: search.guests }, controller.signal)
      .then((result) => setRoomsState({ status: "ready", rooms: result.rooms }))
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        setRoomsState({ status: "error", message: errorMessage(error, "We could not load rooms right now.") });
      });
    return () => controller.abort();
  }, [search.checkIn, search.checkOut, search.guests, attempt]);

  const handleSearch = useCallback(
    (next: StaySearch) => {
      setSelectedRoom(null);
      setSubmitError(null);
      setConfirmed(null);
      setParams({ check_in: next.checkIn, check_out: next.checkOut, guests: String(next.guests) });
      setAttempt((value) => value + 1);
    },
    [setParams],
  );

  const handleBookAnother = useCallback(() => {
    setConfirmed(null);
    setSelectedRoom(null);
    setSubmitError(null);
  }, []);

  const handleCloseDialog = useCallback(() => {
    setSelectedRoom(null);
    setSubmitError(null);
  }, []);

  const handleBook = async (details: GuestDetails) => {
    if (!selectedRoom) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await createBooking({
        guest_name: details.guestName,
        phone: details.phone,
        room_id: selectedRoom.id,
        check_in: search.checkIn,
        check_out: search.checkOut,
        guests: search.guests,
        special_requests: details.specialRequests,
      });
      setConfirmed(result.booking);
      setSelectedRoom(null);
    } catch (error) {
      setSubmitError(errorMessage(error, "We could not complete the booking. Please try again."));
      if (error instanceof ApiError && error.status === 409) {
        setAttempt((value) => value + 1);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const stepIndex = confirmed ? 3 : selectedRoom ? 2 : 1;

  return (
    <div className="container-page py-10 sm:py-14">
      <header className="mb-8 max-w-2xl">
        <p className="text-sm font-semibold uppercase tracking-wider text-brand-blue">Book a stay</p>
        <h1 className="mt-2 text-3xl font-bold text-ink sm:text-4xl">Find your room</h1>
        <p className="mt-3 text-slate-600">Choose your dates and guests. Rooms and prices are checked live against the hotel's system.</p>
      </header>

      <div className="mb-10 rounded-2xl bg-white p-5 shadow-card ring-1 ring-slate-100 sm:p-6">
        <BookingStepper current={stepIndex} />
      </div>

      {confirmed ? (
        <BookingConfirmation booking={confirmed} onBookAnother={handleBookAnother} />
      ) : (
        <div className="grid gap-8 lg:grid-cols-[320px_1fr] lg:items-start">
          <aside className="rounded-2xl bg-white p-5 shadow-card ring-1 ring-slate-100 sm:p-6 lg:sticky lg:top-24">
            <h2 className="mb-5 text-lg font-bold text-ink">Dates and guests</h2>
            <StaySearchForm
              key={`${search.checkIn}-${search.checkOut}-${search.guests}`}
              initial={search}
              onSubmit={handleSearch}
              loading={roomsState.status === "loading"}
            />
          </aside>

          <section aria-live="polite" aria-label="Available rooms" className="min-w-0">
            {roomsState.status === "loading" && <RoomsSkeleton />}

            {roomsState.status === "error" && (
              <div role="alert" className="flex flex-col items-start gap-4 rounded-2xl bg-rose-50 p-6 ring-1 ring-rose-100">
                <AlertTriangle className="h-6 w-6 text-rose-600" aria-hidden="true" />
                <div>
                  <p className="font-semibold text-ink">Rooms are unavailable right now</p>
                  <p className="mt-1 text-sm text-slate-700">{roomsState.message}</p>
                </div>
                <Button variant="secondary" onClick={() => setAttempt((value) => value + 1)}>Try again</Button>
              </div>
            )}

            {roomsState.status === "ready" && roomsState.rooms.length === 0 && (
              <div className="flex flex-col items-center gap-3 rounded-2xl bg-white p-10 text-center shadow-card ring-1 ring-slate-100">
                <BedDouble className="h-10 w-10 text-brand-blue" aria-hidden="true" />
                <p className="text-lg font-semibold text-ink">No rooms are free for these dates</p>
                <p className="max-w-sm text-sm text-slate-600">Try different dates or a smaller group. Nova can also help you find an alternative.</p>
              </div>
            )}

            {roomsState.status === "ready" && roomsState.rooms.length > 0 && (
              <>
                <p className="mb-5 text-sm text-slate-600">
                  <span className="font-semibold text-ink">{roomsState.rooms.length}</span>{" "}
                  {roomsState.rooms.length === 1 ? "room" : "rooms"} available for {nights} {nights === 1 ? "night" : "nights"}
                </p>
                <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-2">
                  {roomsState.rooms.map((room, index) => (
                    <RoomCard
                      key={room.id}
                      room={room}
                      nights={nights}
                      index={index}
                      action={
                        <Button size="md" onClick={() => { setSubmitError(null); setSelectedRoom(room); }}>
                          Book now
                        </Button>
                      }
                    />
                  ))}
                </div>
              </>
            )}
          </section>
        </div>
      )}

      {selectedRoom && !confirmed && (
        <BookRoomDialog
          room={selectedRoom}
          checkIn={search.checkIn}
          checkOut={search.checkOut}
          guests={search.guests}
          nights={nights}
          submitting={submitting}
          error={submitError}
          onClose={handleCloseDialog}
          onSubmit={handleBook}
        />
      )}
    </div>
  );
}

function RoomsSkeleton() {
  return (
    <div className="grid gap-6 md:grid-cols-2" aria-hidden="true">
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="overflow-hidden rounded-2xl bg-white p-0 shadow-card ring-1 ring-slate-100">
          <div className="aspect-[4/3] animate-pulse bg-slate-200" />
          <div className="space-y-3 p-5">
            <div className="h-4 w-1/3 animate-pulse rounded bg-slate-200" />
            <div className="h-6 w-2/3 animate-pulse rounded bg-slate-200" />
            <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  );
}
