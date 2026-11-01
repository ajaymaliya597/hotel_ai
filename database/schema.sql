CREATE DATABASE IF NOT EXISTS nova_booking CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE nova_booking;

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
) ENGINE=InnoDB;

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
) ENGINE=InnoDB;

INSERT IGNORE INTO hotel_rooms (room_number, room_type, description, price_per_night, capacity) VALUES
('101','Standard Queen','Comfortable room with queen bed, Wi-Fi and private bathroom.',2499.00,2),
('201','Deluxe King','Spacious room with king bed and city view.',3999.00,2),
('301','Family Suite','Large suite with extra sleeping space for families.',5999.00,4),
('401','Premium Suite','Premium suite with lounge area and breakfast option.',7999.00,3);
