DROP DATABASE IF EXISTS Tickets;
CREATE database Tickets;
USE Tickets;
CREATE TABLE open_tickets  (
	id INT AUTO_INCREMENT PRIMARY KEY,
    user_id bigint NOT NULL,
    channel_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);