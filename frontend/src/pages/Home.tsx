import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, CalendarCheck, CircleCheck, Mic, Sparkles, ShieldCheck, MessageSquareText } from "lucide-react";
import StaySearchForm, { type StaySearch } from "@/components/booking/StaySearchForm";
import RoomCard from "@/components/rooms/RoomCard";
import { Button } from "@/components/ui/Button";
import { fetchAvailableRooms } from "@/services/bookingService";
import { isAbortError, errorMessage } from "@/services/apiClient";
import type { Room } from "@/types/api";
import { addDays, nightsBetween, todayISO } from "@/utils/format";

const HERO_IMAGE = "https://images.pexels.com/photos/7821349/pexels-photo-7821349.jpeg?auto=compress&cs=tinysrgb&h=650&w=940";
const LOBBY_IMAGE = "https://images.pexels.com/photos/14036253/pexels-photo-14036253.jpeg?auto=compress&cs=tinysrgb&h=650&w=940";

const BENEFITS = [
  { icon: CalendarCheck, title: "Live availability", text: "Rooms and prices come straight from the hotel system, so what you see is what you can book." },
  { icon: ShieldCheck, title: "Confirmed before it counts", text: "Nova reads back every detail and nothing is booked until you say yes." },
  { icon: MessageSquareText, title: "Speak or type", text: "Book by voice in your language or type your request, whichever feels easier." },
];

const PROCESS = [
  { step: "01", title: "Choose your dates", text: "Pick check-in, check-out and the number of guests." },
  { step: "02", title: "Pick a room", text: "Compare live rooms, capacity and nightly rates." },
  { step: "03", title: "Confirm with Nova", text: "Review your summary and receive a booking reference." },
];

function defaultSearch(): StaySearch {
  const checkIn = addDays(todayISO(), 1);
  return { checkIn, checkOut: addDays(checkIn, 2), guests: 2 };
}

export default function Home() {
  const navigate = useNavigate();
  const search = useMemo(defaultSearch, []);
  const nights = nightsBetween(search.checkIn, search.checkOut);
  const [featured, setFeatured] = useState<{ status: "loading" } | { status: "error"; message: string } | { status: "ready"; rooms: Room[] }>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchAvailableRooms({ checkIn: search.checkIn, checkOut: search.checkOut, guests: search.guests }, controller.signal)
      .then((result) => setFeatured({ status: "ready", rooms: result.rooms.slice(0, 4) }))
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        setFeatured({ status: "error", message: errorMessage(error, "Featured rooms are unavailable right now.") });
      });
    return () => controller.abort();
  }, [search]);

  const handleSearch = (next: StaySearch) => {
    navigate(`/booking?check_in=${next.checkIn}&check_out=${next.checkOut}&guests=${next.guests}`);
  };

  return (
    <>
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <img src={HERO_IMAGE} alt="" aria-hidden="true" className="h-full w-full object-cover" fetchPriority="high" />
          <div className="absolute inset-0 bg-gradient-to-r from-ink/85 via-ink/60 to-ink/20" />
        </div>
        <div className="container-page grid gap-12 py-16 sm:py-24 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:py-28">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: "easeOut" }}>
            <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-sm font-medium text-white ring-1 ring-white/20 backdrop-blur">
              <Sparkles className="h-4 w-4 text-brand-cyan" aria-hidden="true" /> AI-powered hotel booking
            </p>
            <h1 className="mt-6 text-4xl font-bold leading-tight text-white sm:text-5xl lg:text-6xl">
              Your Perfect Stay Starts With{" "}
              <span className="bg-gradient-to-r from-cyan-300 to-sky-300 bg-clip-text text-transparent">Nova.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-100">
              Discover comfortable rooms, effortless bookings and personalised AI assistance.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/booking"
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-brand-gradient px-7 text-base font-semibold text-white shadow-glow transition hover:brightness-110 active:scale-[0.98]"
              >
                Book Your Stay <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                to="/nova"
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-white/30 bg-white/10 px-7 text-base font-semibold text-white backdrop-blur transition hover:bg-white/20 active:scale-[0.98]"
              >
                <Mic className="h-4 w-4" aria-hidden="true" /> Talk to Nova
              </Link>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15, ease: "easeOut" }}
            className="rounded-3xl bg-white p-6 shadow-card sm:p-8"
          >
            <h2 className="text-xl font-bold text-ink">Check availability</h2>
            <p className="mb-6 mt-1 text-sm text-slate-600">Pick your dates and guests to see rooms.</p>
            <StaySearchForm initial={search} onSubmit={handleSearch} submitLabel="Search rooms" />
          </motion.div>
        </div>
      </section>

      <section className="container-page py-20" aria-labelledby="nova-heading">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-brand-blue">Meet Nova</p>
            <h2 id="nova-heading" className="mt-3 text-3xl font-bold text-ink sm:text-4xl">Your personal booking assistant</h2>
            <p className="mt-4 text-lg text-slate-600">
              Nova answers questions about rooms, collects your details, reads back the summary and only books once you confirm.
              You can talk or type, in English, Hindi or Hinglish.
            </p>
            <div className="mt-8">
              <Link to="/nova" className="inline-flex items-center gap-2 font-semibold text-brand-blue hover:gap-3 transition-all">
                Start a conversation <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
          <div className="relative">
            <img
              src={LOBBY_IMAGE}
              alt="Modern hotel lobby with a chandelier and warm lighting"
              loading="lazy"
              decoding="async"
              className="aspect-[4/3] w-full rounded-3xl object-cover shadow-card"
            />
            <div className="absolute -bottom-5 left-5 right-5 rounded-2xl bg-white p-4 shadow-card sm:left-auto sm:right-6 sm:w-72">
              <p className="text-sm font-semibold text-ink">Nova</p>
              <p className="mt-1 text-sm text-slate-600">Would you like Deluxe King for two nights? I can check it for you.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="container-page py-16" aria-labelledby="featured-heading">
        <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-brand-blue">Featured rooms</p>
            <h2 id="featured-heading" className="mt-3 text-3xl font-bold text-ink">Available for your next stay</h2>
            <p className="mt-2 text-slate-600">Live availability for {nights} nights, {search.guests} guests.</p>
          </div>
          <Link to="/booking" className="inline-flex items-center gap-2 font-semibold text-brand-blue">
            See all rooms <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>

        {featured.status === "loading" && (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4" aria-hidden="true">
            {[0, 1, 2, 3].map((item) => (
              <div key={item} className="overflow-hidden rounded-2xl bg-white shadow-card ring-1 ring-slate-100">
                <div className="aspect-[4/3] animate-pulse bg-slate-200" />
                <div className="space-y-3 p-5">
                  <div className="h-6 w-2/3 animate-pulse rounded bg-slate-200" />
                  <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
                </div>
              </div>
            ))}
          </div>
        )}

        {featured.status === "error" && (
          <p role="alert" className="rounded-2xl bg-rose-50 p-6 text-sm font-medium text-rose-700">{featured.message}</p>
        )}

        {featured.status === "ready" && featured.rooms.length === 0 && (
          <p className="rounded-2xl bg-white p-6 text-center text-slate-600 shadow-card ring-1 ring-slate-100">
            No rooms are free for these dates. Try other dates on the booking page.
          </p>
        )}

        {featured.status === "ready" && featured.rooms.length > 0 && (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {featured.rooms.map((room, index) => (
              <RoomCard
                key={room.id}
                room={room}
                nights={nights}
                index={index}
                action={
                  <Link
                    to={`/booking?check_in=${search.checkIn}&check_out=${search.checkOut}&guests=${search.guests}`}
                    className="inline-flex min-h-11 items-center rounded-xl bg-brand-gradient px-4 text-sm font-semibold text-white shadow-glow transition hover:brightness-110 active:scale-[0.98]"
                  >
                    Book
                  </Link>
                }
              />
            ))}
          </div>
        )}
      </section>

      <section className="bg-white py-20" aria-labelledby="benefits-heading">
        <div className="container-page">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-sm font-semibold uppercase tracking-wider text-brand-blue">Why choose Nova</p>
            <h2 id="benefits-heading" className="mt-3 text-3xl font-bold text-ink">Simple, honest and quick</h2>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {BENEFITS.map(({ icon: Icon, title, text }) => (
              <motion.div
                key={title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="rounded-2xl bg-canvas p-7 ring-1 ring-slate-100 transition hover:-translate-y-1 hover:shadow-card"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-gradient text-white">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 text-lg font-bold text-ink">{title}</h3>
                <p className="mt-2 text-slate-600">{text}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="container-page py-20" aria-labelledby="process-heading">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-blue">How it works</p>
          <h2 id="process-heading" className="mt-3 text-3xl font-bold text-ink">Booking in three steps</h2>
        </div>
        <ol className="mt-12 grid gap-6 md:grid-cols-3">
          {PROCESS.map((item) => (
            <li key={item.step} className="flex gap-4 rounded-2xl bg-white p-6 shadow-card ring-1 ring-slate-100">
              <span className="text-2xl font-bold text-brand-blue">{item.step}</span>
              <div>
                <h3 className="font-bold text-ink">{item.title}</h3>
                <p className="mt-1 text-sm text-slate-600">{item.text}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="mt-12 flex flex-col items-center gap-4 rounded-3xl bg-brand-gradient p-10 text-center text-white shadow-glow">
          <CircleCheck className="h-8 w-8" aria-hidden="true" />
          <p className="max-w-xl text-xl font-semibold">Ready when you are. Nova will help you find the right room.</p>
          <Button variant="secondary" size="lg" onClick={() => navigate("/booking")} className="border-0 text-brand-blue">
            Book Your Stay
          </Button>
        </div>
      </section>
    </>
  );
}
