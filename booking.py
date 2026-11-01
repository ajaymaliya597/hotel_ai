"""MySQL-backed hotel room booking API for Nova."""
from __future__ import annotations

import logging
import os
import secrets
from datetime import date
from decimal import Decimal
from typing import Optional

import mysql.connector
from mysql.connector import Error
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator

log = logging.getLogger("nova.booking")
router = APIRouter(prefix="/api/hotels", tags=["Hotel bookings"])


def _normalize_phone(value: object) -> str:
    """Store mobile numbers consistently, regardless of spaces, dashes or +91 prefix."""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits


def _db_config() -> dict:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "nova_booking"),
        "connection_timeout": 4,
    }


def get_connection():
    try:
        return mysql.connector.connect(**_db_config())
    except Error as exc:
        log.exception("MySQL connection failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hotel booking database is unavailable. Check MySQL service and MYSQL_* settings in .env.",
        ) from exc


def initialize_booking_database() -> bool:
    """Create booking tables and demo rooms; report whether storage is ready."""
    conn = None
    try:
        conn = mysql.connector.connect(**_db_config())
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hotel_rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                room_number VARCHAR(20) NOT NULL UNIQUE,
                room_type VARCHAR(80) NOT NULL,
                description VARCHAR(500) NOT NULL DEFAULT '',
                price_per_night DECIMAL(10,2) NOT NULL,
                capacity TINYINT UNSIGNED NOT NULL DEFAULT 2,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (price_per_night >= 0), CHECK (capacity >= 1)
            ) ENGINE=InnoDB
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hotel_bookings (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                booking_code VARCHAR(24) NOT NULL UNIQUE,
                guest_name VARCHAR(120) NOT NULL,
                phone VARCHAR(30) NOT NULL,
                room_id INT NOT NULL,
                check_in DATE NOT NULL,
                check_out DATE NOT NULL,
                guests TINYINT UNSIGNED NOT NULL,
                special_requests VARCHAR(1000) NOT NULL DEFAULT '',
                status ENUM('pending_confirmation','confirmed','cancelled') NOT NULL DEFAULT 'confirmed',
                total_price DECIMAL(12,2) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT fk_hotel_booking_room FOREIGN KEY (room_id) REFERENCES hotel_rooms(id),
                INDEX idx_booking_dates (room_id, check_in, check_out, status),
                CHECK (check_out > check_in), CHECK (guests >= 1)
            ) ENGINE=InnoDB
        """)
        # Upgrade existing databases to support a real pending -> confirmed lifecycle.
        cur.execute("""SELECT COLUMN_TYPE FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME='hotel_bookings' AND COLUMN_NAME='status'""",
            (_db_config()["database"],))
        status_column = cur.fetchone()
        if status_column and "pending_confirmation" not in str(status_column[0]):
            cur.execute("ALTER TABLE hotel_bookings MODIFY status ENUM('pending_confirmation','confirmed','cancelled') NOT NULL DEFAULT 'confirmed'")
            log.info("Migrated hotel_bookings.status to include pending_confirmation")
        # Remove the old email column from existing databases too; the new flow uses name + mobile.
        cur.execute("""SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME='hotel_bookings' AND COLUMN_NAME='email'""",
            (_db_config()["database"],))
        if cur.fetchone()[0]:
            cur.execute("ALTER TABLE hotel_bookings DROP COLUMN email")
            log.info("Removed legacy email column from hotel_bookings")
        cur.execute("SELECT COUNT(*) FROM hotel_rooms")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO hotel_rooms (room_number, room_type, description, price_per_night, capacity) VALUES (%s,%s,%s,%s,%s)",
                [
                    ("101", "Standard Queen", "Comfortable room with queen bed, Wi-Fi and private bathroom.", 2499.00, 2),
                    ("201", "Deluxe King", "Spacious room with king bed and city view.", 3999.00, 2),
                    ("301", "Family Suite", "Large suite with extra sleeping space for families.", 5999.00, 4),
                    ("401", "Premium Suite", "Premium suite with lounge area and breakfast option.", 7999.00, 3),
                ],
            )
        conn.commit()
        cur.close()
        log.info("Hotel booking tables ready in MySQL database '%s'", os.getenv("MYSQL_DATABASE", "nova_booking"))
        return True
    except (Error, ValueError, TypeError):
        if conn:
            try:
                conn.rollback()
            except Exception:
                log.exception("Could not roll back failed schema initialization")
        log.exception("Could not initialize hotel booking tables; booking operations are unavailable")
        return False
    finally:
        if conn:
            try:
                if conn.is_connected():
                    conn.close()
            except Exception:
                log.exception("Could not close MySQL connection after schema initialization")


class BookingCreate(BaseModel):
    guest_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    room_id: int = Field(gt=0)
    check_in: date
    check_out: date
    guests: int = Field(ge=1, le=10)
    special_requests: str = Field(default="", max_length=1000)

    @field_validator("guest_name")
    @classmethod
    def strip_guest_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Guest name cannot be blank")
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_required_phone(cls, value: object) -> str:
        phone = _normalize_phone(value)
        if not 10 <= len(phone) <= 15:
            raise ValueError("Enter a valid mobile number with 10 to 15 digits")
        return phone

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_in < date.today():
            raise ValueError("Check-in date cannot be in the past")
        if self.check_out <= self.check_in:
            raise ValueError("Check-out must be after check-in")
        return self


class BookingUpdate(BaseModel):
    guest_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, min_length=10, max_length=15)
    room_id: Optional[int] = Field(default=None, gt=0)
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    guests: Optional[int] = Field(default=None, ge=1, le=10)
    special_requests: Optional[str] = Field(default=None, max_length=1000)


def _as_dict(row: dict) -> dict:
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, date):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
        elif key in ("created_at", "updated_at") and value is not None:
            result[key] = value.isoformat(sep=" ")
    return result


def _booking_select(where: str = "", suffix: str = "") -> str:
    return """SELECT b.id, b.booking_code, b.guest_name, b.phone,
        b.room_id, r.room_number, r.room_type, b.check_in, b.check_out,
        b.guests, b.special_requests, b.status, b.total_price,
        b.created_at, b.updated_at
        FROM hotel_bookings b JOIN hotel_rooms r ON r.id=b.room_id """ + where + " " + suffix


@router.get("/rooms")
def list_rooms(check_in: date = Query(...), check_out: date = Query(...), guests: int = Query(1, ge=1, le=10)):
    if check_in < date.today() or check_out <= check_in:
        raise HTTPException(422, "Choose valid check-in and check-out dates.")
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT r.id, r.room_number, r.room_type, r.description,
                   r.price_per_night, r.capacity
            FROM hotel_rooms r
            WHERE r.active=TRUE AND r.capacity >= %s
              AND NOT EXISTS (
                SELECT 1 FROM hotel_bookings b
                WHERE b.room_id=r.id AND b.status='confirmed'
                  AND b.check_in < %s AND b.check_out > %s
              )
            ORDER BY r.price_per_night, r.room_number
        """, (guests, check_out, check_in))
        rows = [_as_dict(row) for row in cur.fetchall()]
        cur.close()
        return {"rooms": rows, "count": len(rows), "check_in": check_in.isoformat(), "check_out": check_out.isoformat()}
    except Error as exc:
        log.exception("Failed to search hotel room availability")
        raise HTTPException(503, "Could not read room availability from MySQL.") from exc
    finally:
        conn.close()


@router.post("/bookings", status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, *, initial_status: str = "confirmed"):
    nights = (payload.check_out - payload.check_in).days
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)
        # Lock the room row to serialize simultaneous reservations for this room.
        cur.execute("SELECT id, room_number, room_type, price_per_night, capacity, active FROM hotel_rooms WHERE id=%s FOR UPDATE", (payload.room_id,))
        room = cur.fetchone()
        if not room or not room["active"]:
            raise HTTPException(404, "Selected room was not found or is unavailable.")
        if payload.guests > room["capacity"]:
            raise HTTPException(422, f"This room allows up to {room['capacity']} guests.")
        cur.execute("""
            SELECT id FROM hotel_bookings
            WHERE room_id=%s AND status='confirmed'
              AND check_in < %s AND check_out > %s
            LIMIT 1 FOR UPDATE
        """, (payload.room_id, payload.check_out, payload.check_in))
        if cur.fetchone():
            raise HTTPException(409, "This room has already been booked for the selected dates. Please choose another room or dates.")
        total = Decimal(str(room["price_per_night"])) * nights
        code = "NOVA-" + secrets.token_hex(4).upper()
        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO hotel_bookings
            (booking_code, guest_name, phone, room_id, check_in, check_out, guests, special_requests, status, total_price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (code, payload.guest_name, payload.phone, payload.room_id,
              payload.check_in, payload.check_out, payload.guests, payload.special_requests.strip(), initial_status, total))
        booking_id = cur2.lastrowid
        cur2.close()
        # Build the success response before committing. If fetching the inserted row fails,
        # the transaction can still roll back instead of creating a booking while reporting failure.
        cur.execute(_booking_select("WHERE b.id=%s"), (booking_id,))
        inserted_row = cur.fetchone()
        if not inserted_row:
            raise HTTPException(500, "Could not build booking confirmation details; no booking was committed.")
        row = _as_dict(inserted_row)
        conn.commit()
        cur.close()
        log.info("Hotel booking saved code=%s status=%s room=%s nights=%s total=%s", code, initial_status, room["room_number"], nights, total)
        return {"message": "Hotel room booked successfully.", "booking": row}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        log.exception("Failed to create hotel booking")
        raise HTTPException(500, "Could not save booking to MySQL.") from exc
    finally:
        conn.close()


def confirm_pending_booking(booking_code: str, guest_name: str, phone: str) -> dict:
    """Atomically transition a matching pending reservation to confirmed in MySQL."""
    code = booking_code.strip().upper()
    name = guest_name.strip()
    phone = _normalize_phone(phone)
    if not code or not name or len(phone) < 10:
        raise HTTPException(422, "Booking code, full name and mobile number are required.")
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)
        cur.execute(_booking_select("WHERE b.booking_code=%s AND b.phone=%s AND LOWER(b.guest_name)=LOWER(%s) FOR UPDATE"), (code, phone, name))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Matching pending booking was not found. Please restart booking if needed.")
        if row["status"] == "confirmed":
            conn.commit()
            return {"message": "Booking is already confirmed.", "booking": _as_dict(row), "already_confirmed": True}
        if row["status"] != "pending_confirmation":
            raise HTTPException(409, f"Booking cannot be confirmed because its status is {row['status']}.")
        # Recheck room/date conflicts while holding the transaction lock.
        cur.execute("SELECT id FROM hotel_rooms WHERE id=%s FOR UPDATE", (row["room_id"],))
        # IMPORTANT: consume the locking SELECT result before executing another query.
        # mysql-connector raises InternalError("Unread result found") otherwise.
        locked_room = cur.fetchone()
        if not locked_room:
            raise HTTPException(409, "The selected room no longer exists. Please choose another room.")
        cur.execute("""SELECT id FROM hotel_bookings WHERE room_id=%s AND id<>%s AND status='confirmed'
            AND check_in < %s AND check_out > %s LIMIT 1 FOR UPDATE""",
            (row["room_id"], row["id"], row["check_out"], row["check_in"]))
        if cur.fetchone():
            raise HTTPException(409, "This room was booked by someone else before confirmation. Please choose another room.")
        cur.execute("UPDATE hotel_bookings SET status='confirmed' WHERE id=%s AND status='pending_confirmation'", (row["id"],))
        if cur.rowcount != 1:
            raise HTTPException(409, "Booking status changed before confirmation. Please check the booking again.")
        cur.execute(_booking_select("WHERE b.id=%s"), (row["id"],))
        confirmed = cur.fetchone()
        if not confirmed:
            raise HTTPException(500, "Could not read the confirmed booking from MySQL.")
        conn.commit()
        result = _as_dict(confirmed)
        log.info("Hotel booking confirmed by UPDATE code=%s status=%s", code, result["status"])
        return {"message": "Hotel booking confirmed successfully.", "booking": result}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        log.exception("Failed to confirm pending hotel booking")
        raise HTTPException(503, "Could not confirm booking in MySQL.") from exc
    finally:
        conn.close()


@router.get("/bookings")
def list_bookings(phone: str, guest_name: str, booking_code: Optional[str] = None):
    phone = _normalize_phone(phone)
    guest_name = guest_name.strip()
    if len(phone) < 10 or not guest_name:
        raise HTTPException(422, "Provide the booking mobile number and guest name.")
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        if booking_code:
            cur.execute(_booking_select("WHERE b.booking_code=%s AND b.phone=%s AND LOWER(b.guest_name)=LOWER(%s)", "ORDER BY b.created_at DESC"), (booking_code.strip().upper(), phone, guest_name))
        else:
            cur.execute(_booking_select("WHERE b.phone=%s AND LOWER(b.guest_name)=LOWER(%s)", "ORDER BY b.created_at DESC"), (phone, guest_name))
        rows = [_as_dict(row) for row in cur.fetchall()]
        cur.close()
        return {"bookings": rows, "count": len(rows)}
    except Error as exc:
        log.exception("Failed to look up hotel bookings")
        raise HTTPException(503, "Could not look up bookings in MySQL.") from exc
    finally:
        conn.close()


@router.patch("/bookings/{booking_code}/cancel")
def cancel_booking(booking_code: str, phone: str, guest_name: str):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        conn.start_transaction()
        cur.execute("SELECT id, status FROM hotel_bookings WHERE booking_code=%s AND phone=%s AND LOWER(guest_name)=LOWER(%s) FOR UPDATE", (booking_code.strip().upper(), _normalize_phone(phone), guest_name.strip()))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Booking not found for this booking code, mobile number and name.")
        if row["status"] == "cancelled":
            raise HTTPException(409, "This booking is already cancelled.")
        cur.execute("UPDATE hotel_bookings SET status='cancelled' WHERE id=%s", (row["id"],))
        conn.commit()
        cur.close()
        log.info("Hotel booking cancelled code=%s", booking_code.upper())
        return {"message": "Booking cancelled successfully.", "booking_code": booking_code.upper(), "status": "cancelled"}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        log.exception("Failed to cancel hotel booking")
        raise HTTPException(500, "Could not cancel booking in MySQL.") from exc
    finally:
        conn.close()

@router.patch("/bookings/{booking_code}")
def update_booking(booking_code: str, phone: str, guest_name: str, payload: BookingUpdate):
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(422, "Provide at least one field to update.")
    if "guest_name" in changes:
        changes["guest_name"] = changes["guest_name"].strip()
    if "phone" in changes:
        changes["phone"] = _normalize_phone(changes["phone"])
        if not 10 <= len(changes["phone"]) <= 15:
            raise HTTPException(422, "Enter a valid mobile number with 10 to 15 digits.")
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM hotel_bookings WHERE booking_code=%s AND phone=%s AND LOWER(guest_name)=LOWER(%s) FOR UPDATE", (booking_code.strip().upper(), _normalize_phone(phone), guest_name.strip()))
        current = cur.fetchone()
        if not current:
            raise HTTPException(404, "Booking not found for this booking code, mobile number and name.")
        if current["status"] != "confirmed":
            raise HTTPException(409, "Cancelled bookings cannot be edited.")
        merged = {k: current[k] for k in ("room_id", "check_in", "check_out", "guests")}
        merged.update({k: changes[k] for k in changes if k in merged})
        if merged["check_in"] < date.today() or merged["check_out"] <= merged["check_in"]:
            raise HTTPException(422, "Choose valid check-in and check-out dates.")
        cur.execute("SELECT id, room_number, room_type, price_per_night, capacity, active FROM hotel_rooms WHERE id=%s FOR UPDATE", (merged["room_id"],))
        room = cur.fetchone()
        if not room or not room["active"] or merged["guests"] > room["capacity"]:
            raise HTTPException(422, "Selected room is unavailable or cannot fit this number of guests.")
        cur.execute("""SELECT id FROM hotel_bookings WHERE room_id=%s AND status='confirmed' AND id<>%s
            AND check_in < %s AND check_out > %s LIMIT 1 FOR UPDATE""",
            (merged["room_id"], current["id"], merged["check_out"], merged["check_in"]))
        if cur.fetchone():
            raise HTTPException(409, "Room is already booked for the selected dates.")
        allowed = {"guest_name", "phone", "room_id", "check_in", "check_out", "guests", "special_requests"}
        set_sql = ", ".join(f"{key}=%s" for key in changes if key in allowed)
        values = [changes[key] for key in changes if key in allowed]
        nights = (merged["check_out"] - merged["check_in"]).days
        values.append(Decimal(str(room["price_per_night"])) * nights)
        values.append(current["id"])
        cur2 = conn.cursor()
        cur2.execute(f"UPDATE hotel_bookings SET {set_sql}, total_price=%s WHERE id=%s", tuple(values))
        conn.commit()
        cur2.close()
        cur.execute(_booking_select("WHERE b.id=%s"), (current["id"],))
        updated = _as_dict(cur.fetchone())
        cur.close()
        log.info("Hotel booking updated code=%s", booking_code.upper())
        return {"message": "Booking updated successfully.", "booking": updated}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        log.exception("Failed to update hotel booking")
        raise HTTPException(500, "Could not update booking in MySQL.") from exc
    finally:
        conn.close()
