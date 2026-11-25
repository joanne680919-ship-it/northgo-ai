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

CREATE TABLE IF NOT EXISTS menus (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_id INTEGER,
  label TEXT NOT NULL,
  view_key TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL DEFAULT 0,
  roles TEXT NOT NULL DEFAULT 'admin',
  active INTEGER NOT NULL DEFAULT 1
);

INSERT INTO menus (id, parent_id, label, view_key, sort_order, roles, active)
SELECT 1, NULL, '內容管理', '', 10, 'admin', 1 WHERE NOT EXISTS (SELECT 1 FROM menus WHERE id = 1);
INSERT INTO menus (id, parent_id, label, view_key, sort_order, roles, active)
SELECT 2, 1, '客戶詢問', 'enquiries', 10, 'admin,sales,support', 1 WHERE NOT EXISTS (SELECT 1 FROM menus WHERE id = 2);
INSERT INTO menus (id, parent_id, label, view_key, sort_order, roles, active)
SELECT 3, 1, '網站內容', 'content', 20, 'admin,docs', 1 WHERE NOT EXISTS (SELECT 1 FROM menus WHERE id = 3);
INSERT INTO menus (id, parent_id, label, view_key, sort_order, roles, active)
SELECT 4, 1, '媒體', 'media', 30, 'admin,docs', 1 WHERE NOT EXISTS (SELECT 1 FROM menus WHERE id = 4);
INSERT INTO menus (id, parent_id, label, view_key, sort_order, roles, active)
SELECT 5, 1, '動態頁面', 'pages', 40, 'admin,docs', 1 WHERE NOT EXISTS (SELECT 1 FROM menus WHERE id = 5);
UPDATE users SET role = 'sales' WHERE role = 'editor';
UPDATE menus SET roles = 'admin' WHERE id = 1;
UPDATE menus SET roles = 'admin,docs' WHERE id IN (3, 4, 5);
UPDATE menus SET roles = 'admin,sales,support' WHERE id = 2;
INSERT INTO menus (id, parent_id, label, view_key, sort_order, roles, active)
SELECT 6, NULL, '系統設定', '', 20, 'admin', 1 WHERE NOT EXISTS (SELECT 1 FROM menus WHERE id = 6);
INSERT INTO menus (id, parent_id, label, view_key, sort_order, roles, active)
SELECT 7, 6, '使用者', 'users', 10, 'admin', 1 WHERE NOT EXISTS (SELECT 1 FROM menus WHERE id = 7);
INSERT INTO menus (id, parent_id, label, view_key, sort_order, roles, active)
SELECT 8, 6, '選單管理', 'menus', 20, 'admin', 1 WHERE NOT EXISTS (SELECT 1 FROM menus WHERE id = 8);
