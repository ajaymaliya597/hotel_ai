from pathlib import Path


def test_room_lock_select_result_is_consumed_before_next_query():
    source = (Path(__file__).resolve().parents[1] / "booking.py").read_text(encoding="utf-8")
    lock_query = 'cur.execute("SELECT id FROM hotel_rooms WHERE id=%s FOR UPDATE", (row["room_id"],))'
    next_query = 'cur.execute("""SELECT id FROM hotel_bookings WHERE room_id=%s'
    lock_pos = source.index(lock_query)
    fetch_pos = source.index("locked_room = cur.fetchone()", lock_pos)
    next_pos = source.index(next_query, lock_pos)
    assert lock_pos < fetch_pos < next_pos
