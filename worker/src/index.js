const VERSION_FALLBACK = "0.1.1";
const STATUSES = ["new", "in_progress", "closed"];

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
  const user = await requireUser(request, env);
  if (!user) return json({ error: "unauthorized" }, 401, request);
  if (!user.active) return json({ error: "inactive" }, 403, request);

  if (request.method === "GET" && path === "/api/enquiries") return listEnquiries(url, env);
  if (request.method === "POST" && path === "/api/enquiries") return createEnquiry(request, env, false);
  if (request.method === "GET" && enquiryId) return getEnquiry(enquiryId, env);
  if (request.method === "PUT" && enquiryId) return updateEnquiry(enquiryId, request, env);
  if (request.method === "DELETE" && enquiryId) return deleteEnquiry(enquiryId, env);

  if (request.method === "GET" && path === "/api/users") return listUsers(env);
  if (request.method === "POST" && path === "/api/users") return createUser(request, env);
  if (request.method === "PUT" && userId) return updateUser(userId, request, env, user);
  if (request.method === "DELETE" && userId) return deleteUser(userId, env, user);

  return json({ error: "not_found" }, 404, request);
}

function matchId(path, prefix) {
  const match = path.match(new RegExp("^" + prefix + "/(\\d+)$"));
  return match ? Number(match[1]) : 0;
}

async function login(request, env) {
  const body = await readBody(request);
  const email = String(body.email || "").trim().toLowerCase();
  const password = String(body.password || "");
  const row = await env.DB.prepare("SELECT * FROM users WHERE email = ?").bind(email).first();
  if (!row || !row.active || !(await verifyPassword(password, row.password_hash))) {
    return json({ error: "invalid" }, 401, request);
  }
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

async function createEnquiry(request, env, isPublic, parsed) {
  const body = parsed || await readBody(request);
  const record = normalizeEnquiry(body);
  const missing = requiredMissing(record);
  if (missing) return json({ error: "required", field: missing }, 400, request);
  const now = new Date().toISOString();
  const result = await env.DB.prepare(
    `INSERT INTO enquiries (locale, first_name, last_name, company, email, phone, country, services, message, status, notes, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(record.locale, record.firstName, record.lastName, record.company, record.email, record.phone, record.country, record.services, record.message, record.status, record.notes, now, now).run();
  const id = result.meta && result.meta.last_row_id;
  const row = await env.DB.prepare("SELECT * FROM enquiries WHERE id = ?").bind(id).first();
  return json(isPublic ? { ok: true, id } : publicEnquiry(row), isPublic ? 201 : 201, request);
}

async function listEnquiries(url, env) {
  const q = (url.searchParams.get("q") || "").trim();
  let status = (url.searchParams.get("status") || "").trim();
  if (status === "all") status = "";
  if (status && !STATUSES.includes(status)) return json({ error: "status" }, 400);
  const like = "%" + q + "%";
  const flag = q ? "1" : "";
  const rows = await env.DB.prepare(
    `SELECT * FROM enquiries
     WHERE (? = '' OR first_name LIKE ? OR last_name LIKE ? OR company LIKE ? OR email LIKE ? OR phone LIKE ? OR message LIKE ? OR country LIKE ?)
       AND (? = '' OR status = ?)
     ORDER BY id DESC`
  ).bind(flag, like, like, like, like, like, like, like, status, status).all();
  return json({ items: (rows.results || []).map(publicEnquiry) }, 200);
}

async function getEnquiry(id, env) {
  const row = await env.DB.prepare("SELECT * FROM enquiries WHERE id = ?").bind(id).first();
  if (!row) return json({ error: "not_found" }, 404);
  return json(publicEnquiry(row), 200);
}

async function updateEnquiry(id, request, env) {
  const current = await env.DB.prepare("SELECT * FROM enquiries WHERE id = ?").bind(id).first();
  if (!current) return json({ error: "not_found" }, 404);
  const body = await readBody(request);
  const next = normalizeEnquiry({ ...publicEnquiry(current), ...body });
  const missing = requiredMissing(next);
  if (missing) return json({ error: "required", field: missing }, 400);
  const now = new Date().toISOString();
  await env.DB.prepare(
    `UPDATE enquiries SET locale=?, first_name=?, last_name=?, company=?, email=?, phone=?, country=?, services=?, message=?, status=?, notes=?, updated_at=? WHERE id=?`
  ).bind(next.locale, next.firstName, next.lastName, next.company, next.email, next.phone, next.country, next.services, next.message, next.status, next.notes, now, id).run();
  const row = await env.DB.prepare("SELECT * FROM enquiries WHERE id = ?").bind(id).first();
  return json(publicEnquiry(row), 200);
}

async function deleteEnquiry(id, env) {
  const result = await env.DB.prepare("DELETE FROM enquiries WHERE id = ?").bind(id).run();
  if (!result.meta || result.meta.changes === 0) return json({ error: "not_found" }, 404);
  return json({ ok: true }, 200);
}

async function listUsers(env) {
  const rows = await env.DB.prepare("SELECT * FROM users ORDER BY id").all();
  return json({ items: (rows.results || []).map(publicUser) }, 200);
}

async function createUser(request, env) {
  const body = await readBody(request);
  const email = String(body.email || "").trim().toLowerCase();
  const name = String(body.name || "").trim();
  const password = String(body.password || "");
  if (!email.includes("@") || !name || password.length < 8) return json({ error: "required" }, 400);
  const hash = await hashPassword(password);
  const now = new Date().toISOString();
  try {
    await env.DB.prepare(
      "INSERT INTO users (email, name, password_hash, role, active, created_at, updated_at) VALUES (?, ?, ?, 'admin', 1, ?, ?)"
    ).bind(email, name, hash, now, now).run();
  } catch (error) {
    return json({ error: "duplicate" }, 409);
  }
  const row = await env.DB.prepare("SELECT * FROM users WHERE email = ?").bind(email).first();
  return json(publicUser(row), 201);
}

async function updateUser(id, request, env, actor) {
  const current = await env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(id).first();
  if (!current) return json({ error: "not_found" }, 404);
  const body = await readBody(request);
  const email = String(body.email || current.email).trim().toLowerCase();
  const name = String(body.name || current.name).trim();
  const active = body.active === undefined ? current.active : (body.active ? 1 : 0);
  if (!email.includes("@") || !name) return json({ error: "required" }, 400);
  if (!active && current.active && await isLastActive(env, id)) return json({ error: "last_admin" }, 400);
  let hash = current.password_hash;
  if (body.password) {
    if (String(body.password).length < 8) return json({ error: "password" }, 400);
    hash = await hashPassword(body.password);
  }
  const now = new Date().toISOString();
  try {
    await env.DB.prepare(
      "UPDATE users SET email=?, name=?, password_hash=?, active=?, updated_at=? WHERE id=?"
    ).bind(email, name, hash, active, now, id).run();
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
  if (current.active && await isLastActive(env, id)) return json({ error: "last_admin" }, 400);
  await env.DB.prepare("DELETE FROM users WHERE id = ?").bind(id).run();
  return json({ ok: true }, 200);
}

async function isLastActive(env, exceptId) {
  const row = await env.DB.prepare("SELECT COUNT(*) AS n FROM users WHERE active = 1 AND id != ?").bind(exceptId).first();
  return !row || Number(row.n) === 0;
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
    createdAt: row.created_at,
    updatedAt: row.updated_at
  };
}

function publicUser(row) {
  return { id: row.id, email: row.email, name: row.name, role: row.role, active: !!row.active, createdAt: row.created_at };
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
