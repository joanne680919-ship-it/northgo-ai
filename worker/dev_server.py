"""Local stand-in for the Cloudflare Worker while D1 is not deployed."""
import hashlib
import hmac
import json
import re
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "dev.db"
SECRET = "northgo-dev-session-secret"
VERSION = "0.1.5"
STATUSES = {"new", "in_progress", "closed"}
ROLES = {
    "admin": {"name": "管理員", "views": ["enquiries", "content", "media", "pages", "users", "menus"]},
    "sales": {"name": "業務", "views": ["enquiries"]},
    "support": {"name": "客服", "views": ["enquiries"]},
    "docs": {"name": "文件部", "views": ["content", "media", "pages"]},
}
VIEW_KEYS = {"", "enquiries", "content", "media", "pages", "users", "menus"}


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
    if "username" not in columns:
        con.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "last_login_at" not in columns:
        con.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")
    con.execute(
        "UPDATE users SET username = lower(substr(email, 1, instr(email, '@') - 1)) WHERE username IS NULL OR username = ''"
    )
    try:
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_username ON users(username)")
    except sqlite3.IntegrityError:
        pass
    enquiry_columns = {row[1] for row in con.execute("PRAGMA table_info(enquiries)")}
    if "assignee_id" not in enquiry_columns:
        con.execute("ALTER TABLE enquiries ADD COLUMN assignee_id INTEGER")
    con.execute("UPDATE users SET role = 'sales' WHERE role = 'editor'")
    con.execute("UPDATE menus SET roles = 'admin' WHERE id = 1")
    con.execute("UPDATE menus SET roles = 'admin,docs' WHERE id IN (3, 4, 5)")
    con.execute("UPDATE menus SET roles = 'admin,sales,support' WHERE id = 2")
    con.commit()
    return con


def allows(user, view_key):
    return view_key in ROLES.get(user["role"], {}).get("views", [])


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def b64url(raw):
    import base64
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def sign_token(payload):
    body = b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + "." + sig


def verify_token(token):
    import base64
    parts = token.split(".")
    if len(parts) != 2:
        return None
    expected = hmac.new(SECRET.encode(), parts[0].encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, parts[1]):
        return None
    padded = parts[0] + "=" * (-len(parts[0]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (json.JSONDecodeError, ValueError):
        return None
    if payload.get("exp", 0) < time.time() * 1000:
        return None
    return payload


def hash_password(password):
    salt = hashlib.sha256(f"{password}{time.time()}".encode()).digest()[:16]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return "pbkdf2$100000$" + salt.hex() + "$" + digest.hex()


def verify_password(password, stored):
    parts = (stored or "").split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(parts[2]), int(parts[1]))
    return hmac.compare_digest(digest.hex(), parts[3])


def public_user(row):
    role = row["role"]
    known = ROLES.get(role)
    return {
        "id": row["id"], "email": row["email"], "username": row["username"] or "", "name": row["name"],
        "role": role, "roleName": known["name"] if known else role, "permissions": known["views"] if known else [],
        "active": bool(row["active"]), "lastLoginAt": row["last_login_at"] or "", "createdAt": row["created_at"],
    }


def public_menu(row):
    return {
        "id": row["id"], "parentId": row["parent_id"], "label": row["label"], "viewKey": row["view_key"],
        "sortOrder": row["sort_order"], "roles": [item for item in (row["roles"] or "").split(",") if item],
        "active": bool(row["active"]),
    }


def user_fields(body):
    email = str(body.get("email") or "").strip().lower()
    name = str(body.get("name") or "").strip()
    username = str(body.get("username") or "").strip().lower()
    role = body.get("role")
    if role not in ROLES:
        return None
    active = 1 if body.get("active", True) else 0
    if "@" not in email or not name or not re.fullmatch(r"[a-z0-9._-]{2,32}", username):
        return None
    return email, username, name, role, active


def public_enquiry(row):
    return {
        "id": row["id"], "locale": row["locale"], "firstName": row["first_name"], "lastName": row["last_name"],
        "company": row["company"], "email": row["email"], "phone": row["phone"], "country": row["country"],
        "services": [item for item in (row["services"] or "").split(",") if item],
        "message": row["message"], "status": row["status"], "notes": row["notes"],
        "assigneeId": row["assignee_id"],
        "createdAt": row["created_at"], "updatedAt": row["updated_at"],
    }


def normalize(body):
    services = body.get("services") or []
    if isinstance(services, str):
        services = [item.strip() for item in services.split(",") if item.strip()]
    status = body.get("status") or "new"
    if status not in STATUSES:
        status = "new"
    return {
        "locale": str(body.get("locale") or "")[:12],
        "firstName": str(body.get("firstName") or "").strip(),
        "lastName": str(body.get("lastName") or "").strip(),
        "company": str(body.get("company") or "").strip(),
        "email": str(body.get("email") or "").strip(),
        "phone": str(body.get("phone") or "").strip(),
        "country": str(body.get("country") or "").strip(),
        "services": ",".join(services),
        "message": str(body.get("message") or "").strip(),
        "status": status,
        "notes": str(body.get("notes") or ""),
    }


def missing(record):
    for key in ("firstName", "lastName", "company", "email", "phone", "country", "message"):
        if not record[key]:
            return key
    if "@" not in record["email"]:
        return "email"
    return ""


def can_see_enquiry(actor, row):
    return actor["role"] != "support" or row["assignee_id"] == actor["id"]


def enquiry_patch(current, body, actor):
    base = public_enquiry(current)
    if actor["role"] == "admin":
        merged = dict(base)
        merged.update(body)
        return normalize(merged)
    if actor["role"] == "sales":
        merged = dict(base)
        if "status" in body:
            merged["status"] = body.get("status")
        if "notes" in body:
            merged["notes"] = body.get("notes")
        return normalize(merged)
    if "status" in body and body.get("status") != "in_progress":
        return {"error": "status"}
    merged = dict(base)
    if "notes" in body:
        merged["notes"] = body.get("notes")
    if body.get("status") == "in_progress":
        merged["status"] = "in_progress"
    return normalize(merged)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("api", self.address_string(), fmt % args)

    def end_json(self, code, payload):
        raw = json.dumps(payload).encode()
        origin = self.headers.get("Origin") or "*"
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.end_json(204, {})

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        ctype = self.headers.get("Content-Type") or ""
        if "application/json" in ctype:
            return json.loads(raw.decode() or "{}")
        parsed = parse_qs(raw.decode(), keep_blank_values=True)
        body = {key: values[0] for key, values in parsed.items()}
        if "services" in parsed:
            body["services"] = parsed["services"]
        return body

    def user(self):
        header = self.headers.get("Authorization") or ""
        token = header[7:] if header.startswith("Bearer ") else ""
        payload = verify_token(token) if token else None
        if not payload:
            return None
        con = connect()
        row = con.execute("SELECT * FROM users WHERE id = ?", (payload["sub"],)).fetchone()
        con.close()
        return row

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        if path == "/api/version":
            return self.end_json(200, {"version": VERSION})
        if path == "/api/me":
            row = self.user()
            if not row:
                return self.end_json(401, {"error": "unauthorized"})
            return self.end_json(200, {"user": public_user(row), "version": VERSION})
        row = self.user()
        if not row:
            return self.end_json(401, {"error": "unauthorized"})
        if not row["active"]:
            return self.end_json(403, {"error": "inactive"})
        if path == "/api/assignees":
            if not allows(row, "enquiries"):
                return self.end_json(403, {"error": "forbidden"})
            return self.list_assignees()
        if path == "/api/enquiries" or path.startswith("/api/enquiries/"):
            if not allows(row, "enquiries"):
                return self.end_json(403, {"error": "forbidden"})
            if path == "/api/enquiries":
                return self.list_enquiries(parse_qs(url.query), row)
            return self.get_enquiry(int(path.rsplit("/", 1)[1]), row)
        if path == "/api/users":
            if not allows(row, "users"):
                return self.end_json(403, {"error": "forbidden"})
            return self.list_users(parse_qs(url.query))
        if path == "/api/menus":
            manage = parse_qs(url.query).get("scope", [""])[0] == "manage"
            if manage and not allows(row, "menus"):
                return self.end_json(403, {"error": "forbidden"})
            return self.list_menus(row, manage)
        return self.end_json(404, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        body = self.read_body()
        if path == "/api/login":
            return self.login(body)
        if path in ("/api/enquiry", "/api/enquiries/public"):
            return self.create_public(body)
        row = self.user()
        if not row:
            return self.end_json(401, {"error": "unauthorized"})
        if not row["active"]:
            return self.end_json(403, {"error": "inactive"})
        if path == "/api/enquiries":
            if not allows(row, "enquiries"):
                return self.end_json(403, {"error": "forbidden"})
            return self.save_enquiry(body, False, row)
        if path == "/api/users":
            if not allows(row, "users"):
                return self.end_json(403, {"error": "forbidden"})
            return self.create_user(body)
        if path == "/api/menus":
            if not allows(row, "menus"):
                return self.end_json(403, {"error": "forbidden"})
            return self.save_menu(0, body)
        return self.end_json(404, {"error": "not_found"})

    def do_PUT(self):
        path = urlparse(self.path).path.rstrip("/")
        row = self.user()
        if not row:
            return self.end_json(401, {"error": "unauthorized"})
        if not row["active"]:
            return self.end_json(403, {"error": "inactive"})
        body = self.read_body()
        if path == "/api/me":
            body["role"] = row["role"]
            body["active"] = bool(row["active"])
            return self.update_user(row["id"], body, row)
        if path.startswith("/api/enquiries/"):
            if not allows(row, "enquiries"):
                return self.end_json(403, {"error": "forbidden"})
            return self.update_enquiry(int(path.rsplit("/", 1)[1]), body, row)
        if path.startswith("/api/users/"):
            if not allows(row, "users"):
                return self.end_json(403, {"error": "forbidden"})
            return self.update_user(int(path.rsplit("/", 1)[1]), body, row)
        if path.startswith("/api/menus/"):
            if not allows(row, "menus"):
                return self.end_json(403, {"error": "forbidden"})
            return self.save_menu(int(path.rsplit("/", 1)[1]), body)
        return self.end_json(404, {"error": "not_found"})

    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        row = self.user()
        if not row:
            return self.end_json(401, {"error": "unauthorized"})
        if not row["active"]:
            return self.end_json(403, {"error": "inactive"})
        if path.startswith("/api/enquiries/"):
            if not allows(row, "enquiries"):
                return self.end_json(403, {"error": "forbidden"})
            if row["role"] != "admin":
                return self.end_json(403, {"error": "forbidden"})
            return self.delete_enquiry(int(path.rsplit("/", 1)[1]))
        if path.startswith("/api/users/"):
            if not allows(row, "users"):
                return self.end_json(403, {"error": "forbidden"})
            return self.delete_user(int(path.rsplit("/", 1)[1]), row)
        if path.startswith("/api/menus/"):
            if not allows(row, "menus"):
                return self.end_json(403, {"error": "forbidden"})
            return self.delete_menu(int(path.rsplit("/", 1)[1]))
        return self.end_json(404, {"error": "not_found"})

    def login(self, body):
        email = str(body.get("email") or "").strip().lower()
        con = connect()
        row = con.execute("SELECT * FROM users WHERE email = ? OR username = ?", (email, email)).fetchone()
        if not row or not row["active"] or not verify_password(str(body.get("password") or ""), row["password_hash"]):
            con.close()
            return self.end_json(401, {"error": "invalid"})
        con.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now(), row["id"]))
        con.commit()
        row = con.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
        con.close()
        token = sign_token({"sub": row["id"], "email": row["email"], "exp": int(time.time() * 1000) + 12 * 60 * 60 * 1000})
        return self.end_json(200, {"token": token, "user": public_user(row), "version": VERSION})

    def create_public(self, body):
        if str(body.get("website") or "").strip():
            return self.end_json(200, {"ok": True, "id": 0})
        if str(body.get("acceptTerms") or "") != "yes":
            return self.end_json(400, {"error": "terms"})
        return self.save_enquiry(body, public=True)

    def save_enquiry(self, body, public=False, actor=None):
        record = normalize(body)
        field = missing(record)
        if field:
            return self.end_json(400, {"error": "required", "field": field})
        con = connect()
        assignee = self.enquiry_assignee(con, body, actor, public)
        if assignee is False:
            con.close()
            return self.end_json(400, {"error": "assignee"})
        stamp = now()
        cur = con.execute(
            """INSERT INTO enquiries (locale, first_name, last_name, company, email, phone, country, services, message, status, notes, assignee_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record["locale"], record["firstName"], record["lastName"], record["company"], record["email"], record["phone"], record["country"], record["services"], record["message"], record["status"], record["notes"], assignee, stamp, stamp),
        )
        con.commit()
        row = con.execute("SELECT * FROM enquiries WHERE id = ?", (cur.lastrowid,)).fetchone()
        con.close()
        if public:
            return self.end_json(201, {"ok": True, "id": row["id"]})
        return self.end_json(201, public_enquiry(row))

    def list_enquiries(self, query, actor):
        q = (query.get("q") or [""])[0].strip()
        status = (query.get("status") or [""])[0].strip()
        if status == "all":
            status = ""
        if status and status not in STATUSES:
            return self.end_json(400, {"error": "status"})
        like = "%" + q + "%"
        flag = "1" if q else ""
        mine = actor["id"] if actor["role"] == "support" else 0
        con = connect()
        rows = con.execute(
            """SELECT * FROM enquiries
               WHERE (? = '' OR first_name LIKE ? OR last_name LIKE ? OR company LIKE ? OR email LIKE ? OR phone LIKE ? OR message LIKE ? OR country LIKE ?)
                 AND (? = '' OR status = ?)
                 AND (? = 0 OR assignee_id = ?)
               ORDER BY id DESC""",
            (flag, like, like, like, like, like, like, like, status, status, mine, mine),
        ).fetchall()
        con.close()
        return self.end_json(200, {"items": [public_enquiry(row) for row in rows]})

    def get_enquiry(self, item_id, actor):
        con = connect()
        row = con.execute("SELECT * FROM enquiries WHERE id = ?", (item_id,)).fetchone()
        con.close()
        if not row or not can_see_enquiry(actor, row):
            return self.end_json(404, {"error": "not_found"})
        return self.end_json(200, public_enquiry(row))

    def update_enquiry(self, item_id, body, actor):
        con = connect()
        current = con.execute("SELECT * FROM enquiries WHERE id = ?", (item_id,)).fetchone()
        if not current or not can_see_enquiry(actor, current):
            con.close()
            return self.end_json(404, {"error": "not_found"})
        record = enquiry_patch(current, body, actor)
        if record.get("error"):
            con.close()
            return self.end_json(400, {"error": record["error"]})
        field = missing(record)
        if field:
            con.close()
            return self.end_json(400, {"error": "required", "field": field})
        if actor["role"] == "support":
            assignee = current["assignee_id"]
        else:
            assignee = self.enquiry_assignee(con, body, actor, False, current["assignee_id"])
            if assignee is False:
                con.close()
                return self.end_json(400, {"error": "assignee"})
        con.execute(
            """UPDATE enquiries SET locale=?, first_name=?, last_name=?, company=?, email=?, phone=?, country=?, services=?, message=?, status=?, notes=?, assignee_id=?, updated_at=? WHERE id=?""",
            (record["locale"], record["firstName"], record["lastName"], record["company"], record["email"], record["phone"], record["country"], record["services"], record["message"], record["status"], record["notes"], assignee, now(), item_id),
        )
        con.commit()
        row = con.execute("SELECT * FROM enquiries WHERE id = ?", (item_id,)).fetchone()
        con.close()
        return self.end_json(200, public_enquiry(row))

    def list_assignees(self):
        con = connect()
        rows = con.execute("SELECT id, name, username, role FROM users WHERE active = 1 ORDER BY name, id").fetchall()
        con.close()
        return self.end_json(200, {"items": [{"id": row["id"], "name": row["name"], "username": row["username"] or "", "role": row["role"]} for row in rows if allows(row, "enquiries")]})

    def enquiry_assignee(self, con, body, actor, public, current=None):
        if public or not actor:
            return None
        if actor["role"] == "support":
            return actor["id"]
        if "assigneeId" not in body:
            return None if current is None else current
        if body.get("assigneeId") in (None, ""):
            return None
        try:
            assignee = int(body.get("assigneeId"))
        except (TypeError, ValueError):
            return False
        if not assignee:
            return None
        row = con.execute("SELECT id, role FROM users WHERE id = ? AND active = 1", (assignee,)).fetchone()
        return assignee if row and allows(row, "enquiries") else False

    def delete_enquiry(self, item_id):
        con = connect()
        cur = con.execute("DELETE FROM enquiries WHERE id = ?", (item_id,))
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return self.end_json(404, {"error": "not_found"})
        return self.end_json(200, {"ok": True})

    def list_users(self, query):
        con = connect()
        rows = [public_user(row) for row in con.execute("SELECT * FROM users").fetchall()]
        con.close()
        q = (query.get("q", [""])[0] or "").strip().lower()
        role = (query.get("role", [""])[0] or "").strip()
        if q:
            rows = [item for item in rows if q in " ".join([item["username"], item["name"], item["email"], item["role"], item["roleName"]]).lower()]
        if role and role != "all":
            rows = [item for item in rows if item["role"] == role]
        if query.get("includeInactive", ["0"])[0] != "1":
            rows = [item for item in rows if item["active"]]
        sort = query.get("sort", ["lastLoginAt"])[0]
        direction = 1 if query.get("dir", ["desc"])[0] == "asc" else -1
        rows.sort(key=lambda item: str(item.get(sort) or ""), reverse=direction < 0)
        page_size = min(100, max(5, int(query.get("pageSize", ["20"])[0] or 20)))
        page = max(1, int(query.get("page", ["1"])[0] or 1))
        start = (page - 1) * page_size
        return self.end_json(200, {"items": rows[start:start + page_size], "total": len(rows), "page": page, "pageSize": page_size})

    def create_user(self, body):
        fields = user_fields(body)
        password = str(body.get("password") or "")
        if not fields or len(password) < 8:
            return self.end_json(400, {"error": "required"})
        email, username, name, role, active = fields
        stamp = now()
        con = connect()
        try:
            con.execute(
                "INSERT INTO users (email, username, name, password_hash, role, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (email, username, name, hash_password(password), role, active, stamp, stamp),
            )
            con.commit()
        except sqlite3.IntegrityError:
            con.close()
            return self.end_json(409, {"error": "duplicate"})
        row = con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        con.close()
        return self.end_json(201, public_user(row))

    def update_user(self, item_id, body, actor):
        con = connect()
        current = con.execute("SELECT * FROM users WHERE id = ?", (item_id,)).fetchone()
        if not current:
            con.close()
            return self.end_json(404, {"error": "not_found"})
        merged = public_user(current)
        merged.update(body)
        fields = user_fields(merged)
        if not fields:
            con.close()
            return self.end_json(400, {"error": "required"})
        email, username, name, role, active = fields
        if current["role"] == "admin" and current["active"] and (role != "admin" or not active):
            others = con.execute("SELECT COUNT(*) AS n FROM users WHERE active = 1 AND role = 'admin' AND id != ?", (item_id,)).fetchone()["n"]
            if others == 0:
                con.close()
                return self.end_json(400, {"error": "last_admin"})
        stored = current["password_hash"]
        if body.get("password"):
            if len(str(body["password"])) < 8:
                con.close()
                return self.end_json(400, {"error": "password"})
            stored = hash_password(str(body["password"]))
        try:
            con.execute(
                "UPDATE users SET email=?, username=?, name=?, password_hash=?, role=?, active=?, updated_at=? WHERE id=?",
                (email, username, name, stored, role, active, now(), item_id),
            )
            con.commit()
        except sqlite3.IntegrityError:
            con.close()
            return self.end_json(409, {"error": "duplicate"})
        row = con.execute("SELECT * FROM users WHERE id = ?", (item_id,)).fetchone()
        con.close()
        return self.end_json(200, public_user(row))

    def delete_user(self, item_id, actor):
        if actor["id"] == item_id:
            return self.end_json(400, {"error": "self"})
        con = connect()
        current = con.execute("SELECT * FROM users WHERE id = ?", (item_id,)).fetchone()
        if not current:
            con.close()
            return self.end_json(404, {"error": "not_found"})
        if current["role"] == "admin" and current["active"]:
            others = con.execute("SELECT COUNT(*) AS n FROM users WHERE active = 1 AND role = 'admin' AND id != ?", (item_id,)).fetchone()["n"]
            if others == 0:
                con.close()
                return self.end_json(400, {"error": "last_admin"})
        con.execute("DELETE FROM users WHERE id = ?", (item_id,))
        con.commit()
        con.close()
        return self.end_json(200, {"ok": True})

    def list_menus(self, user, manage):
        con = connect()
        items = [public_menu(row) for row in con.execute("SELECT * FROM menus ORDER BY sort_order, id").fetchall()]
        con.close()
        if manage:
            return self.end_json(200, {"items": items})
        visible = [item for item in items if item["active"] and user["role"] in item["roles"]]
        ids = {item["id"] for item in visible}
        ids.update(item["parentId"] for item in visible if item["parentId"])
        return self.end_json(200, {"items": [item for item in items if item["active"] and item["id"] in ids]})

    def save_menu(self, item_id, body):
        label = str(body.get("label") or "").strip()
        view_key = str(body.get("viewKey") or "")
        parent_id = int(body["parentId"]) if body.get("parentId") else None
        sort_order = int(body.get("sortOrder") or 0)
        raw_roles = body.get("roles") if isinstance(body.get("roles"), list) else str(body.get("roles") or "").split(",")
        roles = [item.strip() for item in raw_roles if item.strip() in ROLES]
        active = 1 if body.get("active", True) else 0
        if not label or view_key not in VIEW_KEYS or not roles or parent_id == item_id:
            return self.end_json(400, {"error": "required"})
        con = connect()
        if item_id:
            current = con.execute("SELECT id FROM menus WHERE id = ?", (item_id,)).fetchone()
            if not current:
                con.close()
                return self.end_json(404, {"error": "not_found"})
            con.execute(
                "UPDATE menus SET parent_id=?, label=?, view_key=?, sort_order=?, roles=?, active=? WHERE id=?",
                (parent_id, label, view_key, sort_order, ",".join(roles), active, item_id),
            )
        else:
            con.execute(
                "INSERT INTO menus (parent_id, label, view_key, sort_order, roles, active) VALUES (?, ?, ?, ?, ?, ?)",
                (parent_id, label, view_key, sort_order, ",".join(roles), active),
            )
        con.commit()
        items = [public_menu(row) for row in con.execute("SELECT * FROM menus ORDER BY sort_order, id").fetchall()]
        con.close()
        return self.end_json(200 if item_id else 201, {"items": items})

    def delete_menu(self, item_id):
        con = connect()
        current = con.execute("SELECT id FROM menus WHERE id = ?", (item_id,)).fetchone()
        if not current:
            con.close()
            return self.end_json(404, {"error": "not_found"})
        child = con.execute("SELECT id FROM menus WHERE parent_id = ?", (item_id,)).fetchone()
        if child:
            con.close()
            return self.end_json(400, {"error": "children"})
        con.execute("DELETE FROM menus WHERE id = ?", (item_id,))
        con.commit()
        con.close()
        return self.end_json(200, {"ok": True})


if __name__ == "__main__":
    connect().close()
    print("Northgo API on http://127.0.0.1:8787")
    ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()
