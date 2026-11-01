export type BookingStatus = "pending_confirmation" | "confirmed" | "cancelled";

export interface Room {
  id: number;
  room_number: string;
  room_type: string;
  description: string;
  price_per_night: number | string;
  capacity: number;
}

export interface RoomSearchResponse {
  rooms: Room[];
  count: number;
  check_in: string;
  check_out: string;
}

export interface Booking {
  id: number;
  booking_code: string;
  guest_name: string;
  phone: string;
  room_id: number;
  room_number: string;
  room_type: string;
  check_in: string;
  check_out: string;
  guests: number;
  special_requests: string;
  status: BookingStatus;
  total_price: number | string;
  created_at: string;
  updated_at: string;
}

export interface BookingCreatePayload {
  guest_name: string;
  phone: string;
  room_id: number;
  check_in: string;
  check_out: string;
  guests: number;
  special_requests: string;
}

export interface BookingCreateResponse {
  message: string;
  booking: Booking;
}

export interface BookingListResponse {
  bookings: Booking[];
  count: number;
}

export interface BookingCancelResponse {
  message: string;
  booking_code: string;
  status: string;
}

export type NovaMode = "booking" | "cancel";
export type NovaLanguage = "auto" | "hinglish" | "en" | "hi" | "ta" | "te";

export interface NovaHistoryItem {
  role: "user" | "assistant";
  content: string;
}

export interface NovaToolTrace {
  tool: string;
  ok: boolean;
}

export interface NovaTurnResponse {
  transcript: string;
  reply: string;
  spoken_reply: string;
  provider: string;
  language: string;
  mode: NovaMode;
  input_mode: "text" | "voice";
  tools_called: NovaToolTrace[];
  elapsed_ms: number;
}
