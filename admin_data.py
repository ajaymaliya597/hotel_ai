"""Protected admin data API reusing Nova hotel_rooms and hotel_bookings tables."""
from __future__ import annotations

import logging
import os
import secrets
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal, Optional

import mysql.connector
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from mysql.connector import Error
from pydantic import BaseModel, Field, field_validator, model_validator

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
from admin_auth import require_admin, require_csrf

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("nova.admin")

router = APIRouter(prefix="/admin/api/admin", dependencies=[Depends(require_admin)])

VALID_STATUSES = {"pending_confirmation", "confirmed", "cancelled"}


def get_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "nova_booking"),
            connection_timeout=5,
        )
    except (Error, ValueError) as exc:
        log.exception("Admin database connection failed")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to the Nova MySQL database. Check MYSQL_* values and make sure MySQL is running.",
        ) from exc


def _normalize_phone(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits


def _serialize(row: Optional[dict]) -> Optional[dict]:
    if row is None:
        return None
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
    return result


BOOKING_SELECT = """SELECT b.id, b.booking_code, b.guest_name, b.phone,
    b.room_id, r.room_number, r.room_type, b.check_in, b.check_out,
    b.guests, b.special_requests, b.status, b.total_price,
    b.created_at, b.updated_at
    FROM hotel_bookings b JOIN hotel_rooms r ON r.id=b.room_id"""


class ReservationPayload(BaseModel):
    guest_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    room_id: int = Field(gt=0)
    check_in: date
    check_out: date
    guests: int = Field(ge=1, le=10)
    special_requests: str = Field(default="", max_length=1000)
    status: Literal["pending_confirmation", "confirmed", "cancelled"] = "confirmed"

    @field_validator("guest_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Guest name cannot be blank")
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, value: object) -> str:
        phone = _normalize_phone(value)
        if not 10 <= len(phone) <= 15:
            raise ValueError("Enter a valid phone number with 10 to 15 digits")
        return phone

    @field_validator("special_requests")
    @classmethod
    def clean_requests(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("Check-out must be after check-in")
        return self


def _load_room(cur, room_id: int, guests: int, *, allow_inactive: bool = False) -> dict:
    cur.execute(
        "SELECT id, room_number, room_type, price_per_night, capacity, active FROM hotel_rooms WHERE id=%s FOR UPDATE",
        (room_id,),
    )
    room = cur.fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="Selected room does not exist.")
    if not allow_inactive and not room["active"]:
        raise HTTPException(status_code=422, detail="Selected room is currently inactive.")
    if guests > int(room["capacity"]):
        raise HTTPException(status_code=422, detail=f"This room allows up to {room['capacity']} guests.")
    return room


def _check_conflict(cur, room_id: int, check_in: date, check_out: date, exclude_id: Optional[int] = None):
    sql = """SELECT id FROM hotel_bookings
        WHERE room_id=%s AND status='confirmed'
          AND check_in < %s AND check_out > %s"""
    params: list = [room_id, check_out, check_in]
    if exclude_id is not None:
        sql += " AND id<>%s"
        params.append(exclude_id)
    sql += " LIMIT 1 FOR UPDATE"
    cur.execute(sql, tuple(params))
    if cur.fetchone():
        raise HTTPException(status_code=409, detail="This room is already booked for the selected dates.")


@router.get("/summary")
def summary():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT COUNT(*) AS total,
            SUM(status='confirmed') AS confirmed,
            SUM(status='pending_confirmation') AS pending,
            SUM(status='cancelled') AS cancelled,
            COALESCE(SUM(CASE WHEN status='confirmed' THEN total_price ELSE 0 END),0) AS revenue
            FROM hotel_bookings""")
        row = cur.fetchone() or {}
        cur.close()
        return {
            "total": int(row.get("total") or 0),
            "confirmed": int(row.get("confirmed") or 0),
            "pending": int(row.get("pending") or 0),
            "cancelled": int(row.get("cancelled") or 0),
            "revenue": float(row.get("revenue") or 0),
        }
    except Error as exc:
        log.exception("Could not load admin summary")
        raise HTTPException(status_code=503, detail="Could not load dashboard summary.") from exc
    finally:
        conn.close()


@router.get("/rooms")
def rooms():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, room_number, room_type, price_per_night, capacity, active FROM hotel_rooms ORDER BY room_number")
        rows = [_serialize(row) for row in cur.fetchall()]
        cur.close()
        return {"rooms": rows}
    except Error as exc:
        log.exception("Could not list admin rooms")
        raise HTTPException(status_code=503, detail="Could not load rooms.") from exc
    finally:
        conn.close()


@router.get("/bookings")
def list_admin_bookings(
    search: str = "",
    status_filter: str = "all",
    page: int = 1,
    limit: int = 20,
):
    if status_filter not in {"all", *VALID_STATUSES}:
        raise HTTPException(status_code=422, detail="Invalid booking status filter.")
    page = max(1, page)
    limit = min(max(1, limit), 100)
    offset = (page - 1) * limit
    where_parts, params = [], []
    if status_filter != "all":
        where_parts.append("b.status=%s")
        params.append(status_filter)
    clean_search = search.strip()[:100]
    if clean_search:
        like = f"%{clean_search}%"
        where_parts.append("(b.booking_code LIKE %s OR b.guest_name LIKE %s OR b.phone LIKE %s OR r.room_number LIKE %s)")
        params.extend([like, like, like, like])
    where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS total FROM hotel_bookings b JOIN hotel_rooms r ON r.id=b.room_id" + where_sql, tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(BOOKING_SELECT + where_sql + " ORDER BY b.created_at DESC, b.id DESC LIMIT %s OFFSET %s", tuple(params + [limit, offset]))
        rows = [_serialize(row) for row in cur.fetchall()]
        cur.close()
        return {"bookings": rows, "page": page, "limit": limit, "total": total, "pages": max(1, (total + limit - 1) // limit)}
    except Error as exc:
        log.exception("Could not list admin bookings")
        raise HTTPException(status_code=503, detail="Could not load reservations.") from exc
    finally:
        conn.close()


@router.get("/bookings/{booking_code}")
def get_admin_booking(booking_code: str):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(BOOKING_SELECT + " WHERE b.booking_code=%s", (booking_code.strip().upper(),))
        row = _serialize(cur.fetchone())
        cur.close()
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found.")
        return {"booking": row}
    except Error as exc:
        log.exception("Could not read admin booking %s", booking_code)
        raise HTTPException(status_code=503, detail="Could not read reservation.") from exc
    finally:
        conn.close()


@router.post("/bookings", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create_admin_booking(payload: ReservationPayload):
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)
        room = _load_room(cur, payload.room_id, payload.guests)
        if payload.status == "confirmed":
            _check_conflict(cur, payload.room_id, payload.check_in, payload.check_out)
        nights = (payload.check_out - payload.check_in).days
        total = Decimal(str(room["price_per_night"])) * nights
        code = "NOVA-" + secrets.token_hex(4).upper()
        cur.execute("""INSERT INTO hotel_bookings
            (booking_code, guest_name, phone, room_id, check_in, check_out, guests, special_requests, status, total_price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (code, payload.guest_name, payload.phone, payload.room_id, payload.check_in, payload.check_out,
             payload.guests, payload.special_requests, payload.status, total))
        booking_id = cur.lastrowid
        cur.execute(BOOKING_SELECT + " WHERE b.id=%s", (booking_id,))
        row = _serialize(cur.fetchone())
        conn.commit()
        cur.close()
        log.info("Admin created reservation %s", code)
        return {"message": "Reservation created.", "booking": row}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        log.exception("Admin could not create reservation")
        raise HTTPException(status_code=503, detail="Could not create reservation in MySQL.") from exc
    finally:
        conn.close()


@router.put("/bookings/{booking_code}", dependencies=[Depends(require_csrf)])
def update_admin_booking(booking_code: str, payload: ReservationPayload):
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM hotel_bookings WHERE booking_code=%s FOR UPDATE", (booking_code.strip().upper(),))
        current = cur.fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Reservation not found.")
        cur.execute("SELECT id, room_number, room_type, price_per_night, capacity, active FROM hotel_rooms WHERE id=%s FOR UPDATE", (payload.room_id,))
        room = cur.fetchone()
        if not room:
            raise HTTPException(status_code=404, detail="Selected room does not exist.")
        # Allow editing an existing reservation on an inactive room, but never creating a new one there.
        cur.execute("SELECT room_id FROM hotel_bookings WHERE id=%s", (current["id"],))
        existing_room_id = cur.fetchone()["room_id"]
        if not room["active"] and int(existing_room_id) != payload.room_id:
            raise HTTPException(status_code=422, detail="You cannot move a reservation into an inactive room.")
        if payload.guests > int(room["capacity"]):
            raise HTTPException(status_code=422, detail=f"This room allows up to {room['capacity']} guests.")
        if payload.status == "confirmed":
            _check_conflict(cur, payload.room_id, payload.check_in, payload.check_out, exclude_id=int(current["id"]))
        nights = (payload.check_out - payload.check_in).days
        total = Decimal(str(room["price_per_night"])) * nights
        cur.execute("""UPDATE hotel_bookings SET guest_name=%s, phone=%s, room_id=%s,
            check_in=%s, check_out=%s, guests=%s, special_requests=%s, status=%s, total_price=%s
            WHERE id=%s""",
            (payload.guest_name, payload.phone, payload.room_id, payload.check_in, payload.check_out,
             payload.guests, payload.special_requests, payload.status, total, current["id"]))
        cur.execute(BOOKING_SELECT + " WHERE b.id=%s", (current["id"],))
        row = _serialize(cur.fetchone())
        conn.commit()
        cur.close()
        log.info("Admin updated reservation %s", booking_code.upper())
        return {"message": "Reservation updated.", "booking": row}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        log.exception("Admin could not update reservation %s", booking_code)
        raise HTTPException(status_code=503, detail="Could not update reservation in MySQL.") from exc
    finally:
        conn.close()


@router.delete("/bookings/{booking_code}", dependencies=[Depends(require_csrf)])
def delete_admin_booking(booking_code: str):
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor()
        cur.execute("DELETE FROM hotel_bookings WHERE booking_code=%s", (booking_code.strip().upper(),))
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        if not deleted:
            raise HTTPException(status_code=404, detail="Reservation not found.")
        log.warning("Admin permanently deleted reservation %s", booking_code.upper())
        return {"message": "Reservation permanently deleted."}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        log.exception("Admin could not delete reservation %s", booking_code)
        raise HTTPException(status_code=503, detail="Could not delete reservation from MySQL.") from exc
    finally:
        conn.close()

