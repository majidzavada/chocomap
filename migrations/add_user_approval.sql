-- Add approval_status column if it doesn't exist
ALTER TABLE users
ADD COLUMN IF NOT EXISTS approval_status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending';

-- Add preferred_lang column if it doesn't exist
ALTER TABLE users
ADD COLUMN IF NOT EXISTS preferred_lang VARCHAR(2) NOT NULL DEFAULT 'en';

-- Update existing users to be approved
UPDATE users SET approval_status = 'approved' WHERE approval_status = 'pending';

-- Create admin user if it doesn't exist
INSERT INTO users (name, email, password, role, approval_status)
SELECT 'Admin', 'admin@chocomap.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYpR1IOBYVxGzHy', 'admin', 'approved'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@chocomap.com'); 