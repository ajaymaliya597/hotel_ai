import { apiFetch } from "./apiClient";
import type {
  BookingCancelResponse,
  BookingCreatePayload,
  BookingCreateResponse,
  BookingListResponse,
  RoomSearchResponse,
} from "@/types/api";

const HOTELS = "/api/hotels";
const JSON_HEADERS = { "Content-Type": "application/json" };

export function fetchAvailableRooms(
  params: { checkIn: string; checkOut: string; guests: number },
  signal?: AbortSignal,
): Promise<RoomSearchResponse> {
  const query = new URLSearchParams({
    check_in: params.checkIn,
    check_out: params.checkOut,
    guests: String(params.guests),
  });
  return apiFetch<RoomSearchResponse>(`${HOTELS}/rooms?${query.toString()}`, { signal });
}

export function createBooking(payload: BookingCreatePayload): Promise<BookingCreateResponse> {
  return apiFetch<BookingCreateResponse>(`${HOTELS}/bookings`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
}

export function lookupBookings(params: {
  guestName: string;
  phone: string;
  bookingCode?: string;
}): Promise<BookingListResponse> {
  const query = new URLSearchParams({ guest_name: params.guestName, phone: params.phone });
  if (params.bookingCode) query.set("booking_code", params.bookingCode);
  return apiFetch<BookingListResponse>(`${HOTELS}/bookings?${query.toString()}`);
}

export function cancelBooking(
  bookingCode: string,
  identity: { guestName: string; phone: string },
): Promise<BookingCancelResponse> {
  const query = new URLSearchParams({ phone: identity.phone, guest_name: identity.guestName });
  return apiFetch<BookingCancelResponse>(
    `${HOTELS}/bookings/${encodeURIComponent(bookingCode)}/cancel?${query.toString()}`,
    { method: "PATCH" },
  );
}
