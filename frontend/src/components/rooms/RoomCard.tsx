import { motion } from "framer-motion";
import { BedDouble, CalendarDays, Users } from "lucide-react";
import type { ReactNode } from "react";
import type { Room } from "@/types/api";
import { formatINR } from "@/utils/format";
import { roomImageFor } from "@/utils/roomImages";

interface RoomCardProps {
  room: Room;
  nights: number;
  index?: number;
  action?: ReactNode;
}

export default function RoomCard({ room, nights, index = 0, action }: RoomCardProps) {
  const pricePerNight = Number(room.price_per_night);
  const showTotal = nights > 0 && Number.isFinite(pricePerNight);

  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 6) * 0.06, duration: 0.35, ease: "easeOut" }}
      className="group flex flex-col overflow-hidden rounded-2xl bg-white shadow-card ring-1 ring-slate-100 transition duration-300 hover:-translate-y-1 hover:shadow-glow"
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-brand-light">
        <img
          src={roomImageFor(room.room_type)}
          alt={`${room.room_type} room`}
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
        />
        <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs font-semibold text-emerald-700 shadow-card">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
          Available
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-brand-blue">Room {room.room_number}</p>
          <h3 className="mt-1 text-xl font-bold text-ink">{room.room_type}</h3>
        </div>
        <p className="text-sm text-slate-600">{room.description}</p>
        <ul className="flex flex-wrap gap-2 text-xs font-medium text-slate-700">
          <li className="flex items-center gap-1.5 rounded-full bg-brand-light px-3 py-1.5">
            <Users className="h-3.5 w-3.5 text-brand-blue" aria-hidden="true" /> Up to {room.capacity} guests
          </li>
          {nights > 0 && (
            <li className="flex items-center gap-1.5 rounded-full bg-brand-light px-3 py-1.5">
              <CalendarDays className="h-3.5 w-3.5 text-brand-blue" aria-hidden="true" /> {nights} {nights === 1 ? "night" : "nights"}
            </li>
          )}
          <li className="flex items-center gap-1.5 rounded-full bg-brand-light px-3 py-1.5">
            <BedDouble className="h-3.5 w-3.5 text-brand-blue" aria-hidden="true" /> Live rate
          </li>
        </ul>

        <div className="mt-auto flex items-end justify-between gap-3 border-t border-slate-100 pt-4">
          <div>
            <p className="text-2xl font-bold text-ink">
              {formatINR(room.price_per_night)}
              <span className="text-sm font-medium text-slate-500"> / night</span>
            </p>
            {showTotal && (
              <p className="text-xs text-slate-500">{formatINR(pricePerNight * nights)} total for {nights} {nights === 1 ? "night" : "nights"}</p>
            )}
          </div>
          {action}
        </div>
      </div>
    </motion.article>
  );
}
