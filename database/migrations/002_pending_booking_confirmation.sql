-- Run only if you want to migrate manually. The app also performs this migration at startup.
USE nova_booking;
ALTER TABLE hotel_bookings
  MODIFY status ENUM('pending_confirmation','confirmed','cancelled') NOT NULL DEFAULT 'confirmed';
