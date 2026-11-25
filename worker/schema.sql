CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'admin',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enquiries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  locale TEXT NOT NULL DEFAULT '',
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  company TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT NOT NULL,
  country TEXT NOT NULL,
  services TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

INSERT INTO users (email, name, password_hash, role, active, created_at, updated_at)
SELECT 'admin@northgo.com', 'Northgo 管理員',
  'pbkdf2$100000$a1c3e5b79d2f4a608c0e1b3d5f709182$48dbd914215ca252988f5a5960651a1df5ab0704fc5ca4f8443db176116cab1d',
  'admin', 1, datetime('now'), datetime('now')
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@northgo.com');
