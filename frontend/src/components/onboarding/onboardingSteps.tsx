import { motion } from "framer-motion";
import { CalendarDays, Keyboard, Mic, MessageSquareText, Minus, Plus, Sparkles, Users, BedDouble } from "lucide-react";
import type { ReactNode } from "react";

export interface OnboardingStep {
  id: string;
  eyebrow?: string;
  title: string;
  body: string;
  bullets?: { icon: ReactNode; text: string }[];
  visual: ReactNode;
}

function NovaOrb() {
  return (
    <div className="relative mx-auto flex h-40 w-40 items-center justify-center" aria-hidden="true">
      {[0, 1].map((ring) => (
        <motion.span
          key={ring}
          className="absolute inset-0 rounded-full border-2 border-brand-cyan/40"
          animate={{ scale: [0.8, 1.25], opacity: [0.6, 0] }}
          transition={{ duration: 2.4, repeat: Infinity, delay: ring * 1.2, ease: "easeOut" }}
        />
      ))}
      <motion.span
        className="flex h-24 w-24 items-center justify-center rounded-full bg-brand-gradient text-white shadow-glow"
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      >
        <Sparkles className="h-10 w-10" />
      </motion.span>
    </div>
  );
}

function StayMock() {
  return (
    <div className="mx-auto grid w-full max-w-sm gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-card" aria-hidden="true">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-brand-light p-3">
          <p className="text-xs font-medium text-slate-500">Check-in</p>
          <p className="mt-1 flex items-center gap-2 text-sm font-semibold text-ink"><CalendarDays className="h-4 w-4 text-brand-blue" /> Nov 12</p>
        </div>
        <div className="rounded-xl bg-brand-light p-3">
          <p className="text-xs font-medium text-slate-500">Check-out</p>
          <p className="mt-1 flex items-center gap-2 text-sm font-semibold text-ink"><CalendarDays className="h-4 w-4 text-brand-blue" /> Nov 14</p>
        </div>
      </div>
      <div className="flex items-center justify-between rounded-xl border border-slate-200 p-3">
        <span className="flex items-center gap-2 text-sm font-medium text-ink"><Users className="h-4 w-4 text-brand-blue" /> Guests</span>
        <span className="flex items-center gap-3">
          <Minus className="h-4 w-4 text-slate-400" />
          <span className="w-4 text-center text-sm font-semibold">2</span>
          <Plus className="h-4 w-4 text-brand-blue" />
        </span>
      </div>
      <div className="flex items-center gap-2 rounded-xl border border-brand-blue/30 bg-white p-3 text-sm font-medium text-ink">
        <BedDouble className="h-4 w-4 text-brand-blue" /> Deluxe King, room 201
      </div>
    </div>
  );
}

function ConversationMock() {
  return (
    <div className="mx-auto flex w-full max-w-sm flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-card" aria-hidden="true">
      <div className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-brand-gradient px-4 py-2 text-sm text-white">
        Is a Deluxe King free for two nights?
      </div>
      <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-brand-light px-4 py-2 text-sm text-ink">
        Yes. Room 201 is available. The total is shown before you confirm.
      </div>
      <div className="flex items-center justify-center gap-2 pt-1 text-xs font-medium text-brand-blue">
        <Mic className="h-4 w-4" /> Speak or type, whichever you prefer
      </div>
    </div>
  );
}

export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: "welcome",
    title: "Welcome to Nova.",
    body: "Your AI-powered hotel booking assistant. Discover comfortable stays, explore rooms and book your perfect hotel experience with the help of Nova.",
    visual: <NovaOrb />,
  },
  {
    id: "meet-nova",
    eyebrow: "Step 1 of 3 - Meet Nova",
    title: "A booking assistant that listens.",
    body: "Nova helps you find rooms, make reservations, manage existing bookings and cancel when plans change.",
    bullets: [
      { icon: <Mic className="h-4 w-4" />, text: "Voice-based booking assistance" },
      { icon: <MessageSquareText className="h-4 w-4" />, text: "Text chat whenever you prefer typing" },
      { icon: <BedDouble className="h-4 w-4" />, text: "Room discovery with live availability" },
    ],
    visual: <NovaOrb />,
  },
  {
    id: "choose-stay",
    eyebrow: "Step 2 of 3 - Choose your stay",
    title: "Pick your dates, guests and room.",
    body: "Choose a check-in and check-out date, set the number of guests, then pick the room that suits you. Prices are shown per night with your total.",
    bullets: [
      { icon: <CalendarDays className="h-4 w-4" />, text: "Check-in and check-out dates" },
      { icon: <Users className="h-4 w-4" />, text: "Number of guests" },
      { icon: <Keyboard className="h-4 w-4" />, text: "Preferred room from live results" },
    ],
    visual: <StayMock />,
  },
  {
    id: "book-with-nova",
    eyebrow: "Step 3 of 3 - Book with Nova",
    title: "Talk or type. Nova confirms with you.",
    body: "Ask Nova about rooms, speak with the microphone or type a message. Nova reads back every detail, and nothing is booked until you confirm.",
    bullets: [
      { icon: <Mic className="h-4 w-4" />, text: "Speak to Nova using your microphone" },
      { icon: <Keyboard className="h-4 w-4" />, text: "Type messages if you prefer" },
      { icon: <MessageSquareText className="h-4 w-4" />, text: "Ask about rooms and confirm your booking" },
    ],
    visual: <ConversationMock />,
  },
  {
    id: "ready",
    title: "You're ready! Let's find your perfect stay.",
    body: "You can replay this introduction any time from the Help menu. Returning guests go straight to the website.",
    visual: <NovaOrb />,
  },
];
