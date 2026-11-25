const VERSION_FALLBACK = "0.1.6";
const STATUSES = ["new", "in_progress", "closed"];
const ROLES = {
  admin: { name: "管理員", views: ["enquiries", "content", "media", "pages", "users", "menus", "permissions"] },
  sales: { name: "業務", views: ["enquiries"] },
  support: { name: "客服", views: ["enquiries"] },
  docs: { name: "文件部", views: ["content", "media", "pages"] }
};
const VIEW_KEYS = ["", "enquiries", "content", "media", "pages", "users", "menus", "permissions"];
let schemaReady = null;

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors(request) });
    }
    try {
      const response = await route(request, env);
      return withCors(response, request);
    } catch (error) {
      return json({ error: "server" }, 500, request);
    }
  }
};

async function route(request, env) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/$/, "") || "/";
  const db = env.DB;
  if (!db) return json({ error: "database" }, 500, request);
  await ensureSchema(env);

  if (request.method === "GET" && path === "/api/version") {
    return json({ version: env.APP_VERSION || VERSION_FALLBACK }, 200, request);
  }
  if (request.method === "POST" && path === "/api/login") return login(request, env);
  if (request.method === "GET" && path === "/api/me") return me(request, env);
  if (request.method === "POST" && (path === "/api/enquiry" || path === "/api/enquiries/public")) {
    return createPublicEnquiry(request, env);
  }

  const enquiryId = matchId(path, "/api/enquiries");
  const userId = matchId(path, "/api/users");
  const menuId = matchId(path, "/api/menus");
  const user = await requireUser(request, env);
  if (!user) return json({ error: "unauthorized" }, 401, request);
  if (!user.active) return json({ error: "inactive" }, 403, request);
  if (request.method === "PUT" && path === "/api/me") return updateAccount(request, env, user);

  if (request.method === "GET" && path === "/api/assignees") {
    if (!allows(user, "enquiries")) return json({ error: "forbidden" }, 403, request);
    return listAssignees(env);
  }

  if (path === "/api/enquiries" || enquiryId) {
    if (!allows(user, "enquiries")) return json({ error: "forbidden" }, 403, request);
    if (request.method === "GET" && path === "/api/enquiries") return listEnquiries(url, env, user);
    if (request.method === "POST" && path === "/api/enquiries") return createEnquiry(request, env, false, null, user);
    if (request.method === "GET" && enquiryId) return getEnquiry(enquiryId, env, user);
    if (request.method === "PUT" && enquiryId) return updateEnquiry(enquiryId, request, env, user);
    if (request.method === "DELETE" && enquiryId) return deleteEnquiry(enquiryId, env, user);
  }

  if (path === "/api/users" || userId) {
    if (!allows(user, "users")) return json({ error: "forbidden" }, 403, request);
    if (request.method === "GET" && path === "/api/users") return listUsers(url, env);
    if (request.method === "POST" && path === "/api/users") return createUser(request, env);
    if (request.method === "PUT" && userId) return updateUser(userId, request, env, user);
    if (request.method === "DELETE" && userId) return deleteUser(userId, env, user);
  }

  if (path === "/api/menus" || menuId) {
    if (request.method === "GET" && path === "/api/menus" && url.searchParams.get("scope") !== "manage") {
      return listMenus(env, user, false);
    }
    if (!allows(user, "menus")) return json({ error: "forbidden" }, 403, request);
    if (request.method === "GET" && path === "/api/menus") return listMenus(env, user, true);
    if (request.method === "POST" && path === "/api/menus") return saveMenu(request, env, 0);
    if (request.method === "PUT" && menuId) return saveMenu(request, env, menuId);
    if (request.method === "DELETE" && menuId) return deleteMenu(menuId, env);
  }

  return json({ error: "not_found" }, 404, request);
}

function allows(user, viewKey) {
  const role = ROLES[user.role] || { views: [] };
  return role.views.includes(viewKey);
}

async function ensureSchema(env) {
  if (!schemaReady) {
    schemaReady = (async () => {
      const statements = [
        "ALTER TABLE users ADD COLUMN username TEXT",
        "ALTER TABLE users ADD COLUMN last_login_at TEXT",
        "ALTER TABLE enquiries ADD COLUMN assignee_id INTEGER",
        `CREATE TABLE IF NOT EXISTS menus (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          parent_id INTEGER,
          label TEXT NOT NULL,
          view_key TEXT NOT NULL DEFAULT '',
          sort_order INTEGER NOT NULL DEFAULT 0,
          roles TEXT NOT NULL DEFAULT 'admin',
          active INTEGER NOT NULL DEFAULT 1
        )`
      ];
      for (const sql of statements) {
        try { await env.DB.prepare(sql).run(); } catch (error) { /* column already exists */ }
      }
      await env.DB.prepare(
        "UPDATE users SET username = lower(substr(email, 1, instr(email, '@') - 1)) WHERE username IS NULL OR username = ''"
      ).run();
      await env.DB.prepare("UPDATE users SET role = 'sales' WHERE role = 'editor'").run();
      try {
        await env.DB.prepare("CREATE UNIQUE INDEX IF NOT EXISTS users_username ON users(username)").run();
      } catch (error) { /* existing duplicate usernames */ }
      const seeds = [
        [1, null, "內容管理", "", 10, "admin"],
        [2, 1, "客戶詢問", "enquiries", 10, "admin,sales,support"],
        [3, 1, "網站內容", "content", 20, "admin,docs"],
        [4, 1, "媒體", "media", 30, "admin,docs"],
        [5, 1, "動態頁面", "pages", 40, "admin,docs"],
        [6, null, "系統設定", "", 20, "admin"],
        [7, 6, "使用者", "users", 10, "admin"],
        [8, 6, "選單管理", "menus", 20, "admin"],
        [9, 6, "角色權限", "permissions", 30, "admin"]
      ];
      for (const [id, parentId, label, viewKey, sortOrder, roles] of seeds) {
        await env.DB.prepare(
          "INSERT INTO menus (id, parent_id, label, view_key, sort_order, roles, active) SELECT ?, ?, ?, ?, ?, ?, 1 WHERE NOT EXISTS (SELECT 1 FROM menus WHERE id = ?)"
        ).bind(id, parentId, label, viewKey, sortOrder, roles, id).run();
      }
      const roleUpdates = [[1, "admin"], [2, "admin,sales,support"], [3, "admin,docs"], [4, "admin,docs"], [5, "admin,docs"]];
      for (const [id, roles] of roleUpdates) {
        await env.DB.prepare("UPDATE menus SET roles = ? WHERE id = ?").bind(roles, id).run();
      }
    })().catch((error) => {
      schemaReady = null;
      throw error;
    });
  }
  return schemaReady;
}

function matchId(path, prefix) {
  const match = path.match(new RegExp("^" + prefix + "/(\\d+)$"));
  return match ? Number(match[1]) : 0;
}

async function login(request, env) {
  const body = await readBody(request);
  const email = String(body.email || "").trim().toLowerCase();
  const password = String(body.password || "");
  const row = await env.DB.prepare("SELECT * FROM users WHERE email = ? OR username = ?").bind(email, email).first();
  if (!row || !row.active || !(await verifyPassword(password, row.password_hash))) {
    return json({ error: "invalid" }, 401, request);
  }
  const now = new Date().toISOString();
  await env.DB.prepare("UPDATE users SET last_login_at = ? WHERE id = ?").bind(now, row.id).run();
  row.last_login_at = now;
  const token = await signToken({ sub: row.id, email: row.email, exp: Date.now() + 12 * 60 * 60 * 1000 }, env);
  return json({ token, user: publicUser(row), version: env.APP_VERSION || VERSION_FALLBACK }, 200, request);
}

async function me(request, env) {
  const user = await requireUser(request, env);
  if (!user) return json({ error: "unauthorized" }, 401, request);
  return json({ user: publicUser(user), version: env.APP_VERSION || VERSION_FALLBACK }, 200, request);
}

async function createPublicEnquiry(request, env) {
  const body = await readBody(request);
  if (String(body.website || "").trim()) return json({ ok: true, id: 0 }, 200, request);
  if (String(body.acceptTerms || "") !== "yes") return json({ error: "terms" }, 400, request);
  return createEnquiry(request, env, true, body);
}

async function createEnquiry(request, env, isPublic, parsed, actor) {
  const body = parsed || await readBody(request);
  const record = normalizeEnquiry(body);
  const missing = requiredMissing(record);
  if (missing) return json({ error: "required", field: missing }, 400, request);
  const assignee = await enquiryAssignee(env, body, actor, isPublic);
  if (assignee === false) return json({ error: "assignee" }, 400, request);
  const now = new Date().toISOString();
  const result = await env.DB.prepare(
    `INSERT INTO enquiries (locale, first_name, last_name, company, email, phone, country, services, message, status, notes, assignee_id, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(record.locale, record.firstName, record.lastName, record.company, record.email, record.phone, record.country, record.services, record.message, record.status, record.notes, assignee, now, now).run();
  const id = result.meta && result.meta.last_row_id;
  const row = await env.DB.prepare("SELECT * FROM enquiries WHERE id = ?").bind(id).first();
  return json(isPublic ? { ok: true, id } : publicEnquiry(row), 201, request);
}

async function listEnquiries(url, env, user) {
  const q = (url.searchParams.get("q") || "").trim();
  let status = (url.searchParams.get("status") || "").trim();
  if (status === "all") status = "";
  if (status && !STATUSES.includes(status)) return json({ error: "status" }, 400);
  const like = "%" + q + "%";
  const flag = q ? "1" : "";
  const mine = user.role === "support" ? user.id : 0;
  const rows = await env.DB.prepare(
    `SELECT * FROM enquiries
     WHERE (? = '' OR first_name LIKE ? OR last_name LIKE ? OR company LIKE ? OR email LIKE ? OR phone LIKE ? OR message LIKE ? OR country LIKE ?)
       AND (? = '' OR status = ?)
       AND (? = 0 OR assignee_id = ?)
     ORDER BY id DESC`
  ).bind(flag, like, like, like, like, like, like, like, status, status, mine, mine).all();
  return json({ items: (rows.results || []).map(publicEnquiry) }, 200);
}

async function getEnquiry(id, env, user) {
  const row = await env.DB.prepare("SELECT * FROM enquiries WHERE id = ?").bind(id).first();
  if (!row || !canSeeEnquiry(user, row)) return json({ error: "not_found" }, 404);
  return json(publicEnquiry(row), 200);
}

async function updateEnquiry(id, request, env, user) {
  const current = await env.DB.prepare("SELECT * FROM enquiries WHERE id = ?").bind(id).first();
  if (!current || !canSeeEnquiry(user, current)) return json({ error: "not_found" }, 404);
  const body = await readBody(request);
  const next = enquiryPatch(current, body, user);
  if (next.error) return json({ error: next.error }, 400);
  const missing = requiredMissing(next);
  if (missing) return json({ error: "required", field: missing }, 400);
  const assignee = user.role === "support" ? current.assignee_id : await enquiryAssignee(env, body, user, false, current.assignee_id);
  if (assignee === false) return json({ error: "assignee" }, 400);
  const now = new Date().toISOString();
  await env.DB.prepare(
    `UPDATE enquiries SET locale=?, first_name=?, last_name=?, company=?, email=?, phone=?, country=?, services=?, message=?, status=?, notes=?, assignee_id=?, updated_at=? WHERE id=?`
  ).bind(next.locale, next.firstName, next.lastName, next.company, next.email, next.phone, next.country, next.services, next.message, next.status, next.notes, assignee, now, id).run();
  const row = await env.DB.prepare("SELECT * FROM enquiries WHERE id = ?").bind(id).first();
  return json(publicEnquiry(row), 200);
}

async function deleteEnquiry(id, env, user) {
  if (user.role !== "admin") return json({ error: "forbidden" }, 403);
  const result = await env.DB.prepare("DELETE FROM enquiries WHERE id = ?").bind(id).run();
  if (!result.meta || result.meta.changes === 0) return json({ error: "not_found" }, 404);
  return json({ ok: true }, 200);
}

async function listAssignees(env) {
  const rows = await env.DB.prepare("SELECT id, name, username, role FROM users WHERE active = 1 ORDER BY name, id").all();
  const items = (rows.results || []).filter((row) => allows(row, "enquiries")).map((row) => ({ id: row.id, name: row.name, username: row.username || "", role: row.role }));
  return json({ items }, 200);
}

function canSeeEnquiry(user, row) {
  return user.role !== "support" || Number(row.assignee_id) === Number(user.id);
}

function enquiryPatch(current, body, user) {
  const base = publicEnquiry(current);
  if (user.role === "admin") return normalizeEnquiry({ ...base, ...body });
  if (user.role === "sales") {
    return normalizeEnquiry({ ...base, status: body.status === undefined ? base.status : body.status, notes: body.notes === undefined ? base.notes : body.notes });
  }
  if (body.status !== undefined && body.status !== "in_progress") return { error: "status" };
  return normalizeEnquiry({ ...base, notes: body.notes === undefined ? base.notes : body.notes, status: body.status === "in_progress" ? "in_progress" : base.status });
}

async function enquiryAssignee(env, body, actor, isPublic, current) {
  if (isPublic || !actor) return null;
  if (actor.role === "support") return actor.id;
  if (body.assigneeId === undefined) return current === undefined ? null : current;
  if (body.assigneeId === null || body.assigneeId === "") return null;
  const id = Number(body.assigneeId);
  if (!id) return null;
  const row = await env.DB.prepare("SELECT id, role FROM users WHERE id = ? AND active = 1").bind(id).first();
  return row && allows(row, "enquiries") ? id : false;
}

async function listUsers(url, env) {
  const rows = await env.DB.prepare("SELECT * FROM users").all();
  let items = (rows.results || []).map(publicUser);
  const q = (url.searchParams.get("q") || "").trim().toLowerCase();
  const role = (url.searchParams.get("role") || "").trim();
  if (q) {
    items = items.filter((item) => [item.username, item.name, item.email, item.role, item.roleName].join(" ").toLowerCase().includes(q));
  }
  if (role && role !== "all") items = items.filter((item) => item.role === role);
  if (url.searchParams.get("includeInactive") !== "1") items = items.filter((item) => item.active);
  const sort = url.searchParams.get("sort") || "lastLoginAt";
  const dir = url.searchParams.get("dir") === "asc" ? 1 : -1;
  items.sort((a, b) => String(a[sort] || "").localeCompare(String(b[sort] || "")) * dir);
  const pageSize = Math.min(100, Math.max(5, Number(url.searchParams.get("pageSize")) || 20));
  const page = Math.max(1, Number(url.searchParams.get("page")) || 1);
  const start = (page - 1) * pageSize;
  return json({ items: items.slice(start, start + pageSize), total: items.length, page, pageSize }, 200);
}

async function createUser(request, env) {
  const body = await readBody(request);
  const fields = userFields(body);
  if (fields.error) return json({ error: fields.error }, 400);
  if (String(body.password || "").length < 8) return json({ error: "password" }, 400);
  const hash = await hashPassword(String(body.password));
  const now = new Date().toISOString();
  try {
    await env.DB.prepare(
      "INSERT INTO users (email, username, name, password_hash, role, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(fields.email, fields.username, fields.name, hash, fields.role, fields.active, now, now).run();
  } catch (error) {
    return json({ error: "duplicate" }, 409);
  }
  const row = await env.DB.prepare("SELECT * FROM users WHERE email = ?").bind(fields.email).first();
  return json(publicUser(row), 201);
}

async function updateUser(id, request, env, actor, preset) {
  const current = await env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(id).first();
  if (!current) return json({ error: "not_found" }, 404);
  const body = preset || await readBody(request);
  const fields = userFields({ ...publicUser(current), ...body, active: body.active === undefined ? current.active : body.active });
  if (fields.error) return json({ error: fields.error }, 400);
  if (current.role === "admin" && current.active && (fields.role !== "admin" || !fields.active) && await isLastAdmin(env, id)) {
    return json({ error: "last_admin" }, 400);
  }
  let hash = current.password_hash;
  if (body.password) {
    if (String(body.password).length < 8) return json({ error: "password" }, 400);
    hash = await hashPassword(body.password);
  }
  const now = new Date().toISOString();
  try {
    await env.DB.prepare(
      "UPDATE users SET email=?, username=?, name=?, password_hash=?, role=?, active=?, updated_at=? WHERE id=?"
    ).bind(fields.email, fields.username, fields.name, hash, fields.role, fields.active, now, id).run();
  } catch (error) {
    return json({ error: "duplicate" }, 409);
  }
  const row = await env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(id).first();
  return json(publicUser(row), 200);
}

async function deleteUser(id, env, actor) {
  if (actor.id === id) return json({ error: "self" }, 400);
  const current = await env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(id).first();
  if (!current) return json({ error: "not_found" }, 404);
  if (current.role === "admin" && current.active && await isLastAdmin(env, id)) return json({ error: "last_admin" }, 400);
  await env.DB.prepare("DELETE FROM users WHERE id = ?").bind(id).run();
  return json({ ok: true }, 200);
}

async function isLastAdmin(env, exceptId) {
  const row = await env.DB.prepare("SELECT COUNT(*) AS n FROM users WHERE active = 1 AND role = 'admin' AND id != ?").bind(exceptId).first();
  return !row || Number(row.n) === 0;
}

function userFields(body) {
  const email = String(body.email || "").trim().toLowerCase();
  const name = String(body.name || "").trim();
  const username = String(body.username || "").trim().toLowerCase();
  if (!ROLES[body.role]) return { error: "role" };
  const role = body.role;
  const active = body.active === undefined || body.active ? 1 : 0;
  if (!email.includes("@") || !name || !/^[a-z0-9._-]{2,32}$/.test(username)) return { error: "required" };
  return { email, name, username, role, active };
}

async function updateAccount(request, env, actor) {
  const body = await readBody(request);
  body.role = actor.role;
  body.active = !!actor.active;
  return updateUser(actor.id, request, env, actor, body);
}

async function listMenus(env, user, manage) {
  const rows = await env.DB.prepare("SELECT * FROM menus ORDER BY sort_order, id").all();
  const items = (rows.results || []).map(publicMenu);
  if (manage) return json({ items }, 200);
  const role = user.role;
  const visible = items.filter((item) => item.active && item.roles.includes(role));
  const ids = new Set(visible.map((item) => item.id));
  visible.forEach((item) => { if (item.parentId) ids.add(item.parentId); });
  return json({ items: items.filter((item) => item.active && ids.has(item.id)) }, 200);
}

async function saveMenu(request, env, id) {
  const body = await readBody(request);
  const label = String(body.label || "").trim();
  const viewKey = String(body.viewKey || "");
  const parentId = body.parentId ? Number(body.parentId) : null;
  const sortOrder = Number(body.sortOrder) || 0;
  const roles = (Array.isArray(body.roles) ? body.roles : String(body.roles || "").split(","))
    .map((item) => String(item).trim()).filter((item) => ROLES[item]);
  const active = body.active === undefined || body.active ? 1 : 0;
  if (!label || !VIEW_KEYS.includes(viewKey) || !roles.length) return json({ error: "required" }, 400);
  if (parentId && parentId === id) return json({ error: "parent" }, 400);
  const roleText = roles.join(",");
  if (id) {
    const current = await env.DB.prepare("SELECT id FROM menus WHERE id = ?").bind(id).first();
    if (!current) return json({ error: "not_found" }, 404);
    await env.DB.prepare(
      "UPDATE menus SET parent_id=?, label=?, view_key=?, sort_order=?, roles=?, active=? WHERE id=?"
    ).bind(parentId, label, viewKey, sortOrder, roleText, active, id).run();
  } else {
    await env.DB.prepare(
      "INSERT INTO menus (parent_id, label, view_key, sort_order, roles, active) VALUES (?, ?, ?, ?, ?, ?)"
    ).bind(parentId, label, viewKey, sortOrder, roleText, active).run();
  }
  const rows = await env.DB.prepare("SELECT * FROM menus ORDER BY sort_order, id").all();
  return json({ items: (rows.results || []).map(publicMenu) }, id ? 200 : 201);
}

async function deleteMenu(id, env) {
  const current = await env.DB.prepare("SELECT id FROM menus WHERE id = ?").bind(id).first();
  if (!current) return json({ error: "not_found" }, 404);
  const child = await env.DB.prepare("SELECT id FROM menus WHERE parent_id = ?").bind(id).first();
  if (child) return json({ error: "children" }, 400);
  await env.DB.prepare("DELETE FROM menus WHERE id = ?").bind(id).run();
  return json({ ok: true }, 200);
}

function publicMenu(row) {
  return {
    id: row.id,
    parentId: row.parent_id,
    label: row.label,
    viewKey: row.view_key,
    sortOrder: row.sort_order,
    roles: String(row.roles || "").split(",").filter(Boolean),
    active: !!row.active
  };
}

function normalizeEnquiry(body) {
  const services = Array.isArray(body.services) ? body.services.join(",") : String(body.services || "");
  let status = String(body.status || "new");
  if (!STATUSES.includes(status)) status = "new";
  return {
    locale: String(body.locale || "").slice(0, 12),
    firstName: String(body.firstName || "").trim(),
    lastName: String(body.lastName || "").trim(),
    company: String(body.company || "").trim(),
    email: String(body.email || "").trim(),
    phone: String(body.phone || "").trim(),
    country: String(body.country || "").trim(),
    services: services.split(",").map((item) => item.trim()).filter(Boolean).join(","),
    message: String(body.message || "").trim(),
    status,
    notes: String(body.notes || "")
  };
}

function requiredMissing(record) {
  for (const key of ["firstName", "lastName", "company", "email", "phone", "country", "message"]) {
    if (!record[key]) return key;
  }
  if (!record.email.includes("@")) return "email";
  return "";
}

function publicEnquiry(row) {
  return {
    id: row.id,
    locale: row.locale,
    firstName: row.first_name,
    lastName: row.last_name,
    company: row.company,
    email: row.email,
    phone: row.phone,
    country: row.country,
    services: row.services ? row.services.split(",") : [],
    message: row.message,
    status: row.status,
    notes: row.notes,
    assigneeId: row.assignee_id || null,
    createdAt: row.created_at,
    updatedAt: row.updated_at
  };
}

function publicUser(row) {
  const role = row.role;
  const known = ROLES[role];
  return {
    id: row.id,
    email: row.email,
    username: row.username || "",
    name: row.name,
    role,
    roleName: known ? known.name : role,
    permissions: known ? known.views : [],
    active: !!row.active,
    lastLoginAt: row.last_login_at || "",
    createdAt: row.created_at
  };
}

async function requireUser(request, env) {
  const header = request.headers.get("Authorization") || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!token) return null;
  const payload = await verifyToken(token, env);
  if (!payload) return null;
  return env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(payload.sub).first();
}

async function hashPassword(password) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iterations = 100000;
  const digest = await pbkdf2(password, salt, iterations);
  return "pbkdf2$" + iterations + "$" + bytesToHex(salt) + "$" + bytesToHex(digest);
}

async function verifyPassword(password, stored) {
  const parts = String(stored || "").split("$");
  if (parts.length !== 4 || parts[0] !== "pbkdf2") return false;
  const iterations = Number(parts[1]);
  const salt = hexToBytes(parts[2]);
  const digest = await pbkdf2(password, salt, iterations);
  return bytesToHex(digest) === parts[3];
}

async function pbkdf2(password, salt, iterations) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations }, key, 256);
  return new Uint8Array(bits);
}

async function signToken(payload, env) {
  const secret = env.SESSION_SECRET || "northgo-dev-session-secret";
  const body = b64url(JSON.stringify(payload));
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  return body + "." + bytesToHex(new Uint8Array(sig));
}

async function verifyToken(token, env) {
  const secret = env.SESSION_SECRET || "northgo-dev-session-secret";
  const parts = token.split(".");
  if (parts.length !== 2) return null;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("HMAC", key, hexToBytes(parts[1]), new TextEncoder().encode(parts[0]));
  if (!ok) return null;
  try {
    const payload = JSON.parse(atob(parts[0].replace(/-/g, "+").replace(/_/g, "/")));
    if (!payload.exp || payload.exp < Date.now()) return null;
    return payload;
  } catch (error) {
    return null;
  }
}

async function readBody(request) {
  const type = request.headers.get("Content-Type") || "";
  if (type.includes("application/json")) return request.json();
  const form = await request.formData();
  const body = {};
  for (const [key, value] of form.entries()) {
    if (key === "services") {
      body.services = body.services || [];
      body.services.push(String(value));
    } else {
      body[key] = String(value);
    }
  }
  return body;
}

function json(data, status, request) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...cors(request || { headers: { get: () => "" } }) }
  });
}

function withCors(response, request) {
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(cors(request))) headers.set(key, value);
  return new Response(response.body, { status: response.status, headers });
}

function cors(request) {
  const origin = (request.headers && request.headers.get && request.headers.get("Origin")) || "*";
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    Vary: "Origin"
  };
}

function bytesToHex(bytes) {
  return [...bytes].map((value) => value.toString(16).padStart(2, "0")).join("");
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let index = 0; index < bytes.length; index += 1) bytes[index] = parseInt(hex.substr(index * 2, 2), 16);
  return bytes;
}

function b64url(value) {
  return btoa(value).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}
