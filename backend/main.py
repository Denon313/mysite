
# -*- coding: utf-8 -*-

import os
import time
import uuid
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory
)
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR.parent / "uploads"
DB_PATH = BASE_DIR / "database.db"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))

# رمز مدیریت را در Termux با متغیر محیطی تنظیم کن:
# export ADMIN_PASSWORD='رمز شما'
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

ADMIN_TOKENS = set()

FIXED_MEMBERS = [
    "مهدی",
    "راستین",
    "امیرعلی",
    "مهنا",
    "فاطمه"
]

MAIN_ROOM_ID = "MOVIE4"
MAX_ROOM_MEMBERS = 5

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".mkv",
    ".mov",
    ".m4v",
    ".avi"
}

FRONTEND_ORIGINS = [
    item.strip()
    for item in os.environ.get(
        "FRONTEND_ORIGINS",
        "https://denon313.github.io,http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if item.strip()
]


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 * 1024

CORS(
    app,
    resources={r"/api/*": {"origins": FRONTEND_ORIGINS}},
    supports_credentials=False
)

socketio = SocketIO(
    app,
    cors_allowed_origins=FRONTEND_ORIGINS,
    async_mode="threading"
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            year TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            poster TEXT DEFAULT '',
            video TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def add_log(action):
    try:
        conn = get_db()

        conn.execute(
            "INSERT INTO logs (action) VALUES (?)",
            (action,)
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print("LOG ERROR:", e)


init_db()


# =========================================================
# HELPERS
# =========================================================

def serialize_movie(row):
    if row is None:
        return None

    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "year": row["year"],
        "genre": row["genre"],
        "poster": row["poster"],
        "video": row["video"],
        "created_at": row["created_at"]
    }


def get_movie(movie_id):
    conn = get_db()

    row = conn.execute(
        "SELECT * FROM movies WHERE id = ?",
        (movie_id,)
    ).fetchone()

    conn.close()

    return row


def allowed_video(filename):
    if not filename:
        return False

    extension = Path(filename).suffix.lower()

    return extension in ALLOWED_VIDEO_EXTENSIONS


def create_admin_token():
    token = uuid.uuid4().hex + uuid.uuid4().hex

    ADMIN_TOKENS.add(token)

    return token


def is_admin():
    token = request.headers.get("X-Admin-Token", "")

    return bool(token and token in ADMIN_TOKENS)


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if not is_admin():
            return jsonify({
                "success": False,
                "error": "دسترسی مدیر لازم است"
            }), 401

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# ROOMS
# =========================================================

rooms = {}

sid_info = {}


def create_room_if_needed(room_id):
    if room_id not in rooms:

        rooms[room_id] = {
            "connections": {},
            "movie": None,
            "playing": False,
            "current_time": 0.0,
            "updated_at": time.time()
        }

    return rooms[room_id]


def get_room_current_time(room):
    current_time = float(room.get("current_time", 0))

    if room.get("playing"):
        updated_at = float(
            room.get("updated_at", time.time())
        )

        current_time += time.time() - updated_at

    return max(0.0, current_time)


def get_public_members(room):
    result = {}

    for name in FIXED_MEMBERS:
        result[name] = "offline"

    for info in room["connections"].values():

        name = info["name"]

        status = info.get("status", "online")

        if name in result:
            result[name] = status

    return result


def emit_members(room_id):
    room = create_room_if_needed(room_id)

    socketio.emit(
        "member_update",
        {
            "members": get_public_members(room)
        },
        room=room_id
    )


def get_room_state(room_id):
    room = create_room_if_needed(room_id)

    return {
        "room_id": room_id,
        "movie": room["movie"],
        "playing": room["playing"],
        "current_time": get_room_current_time(room),
        "members": get_public_members(room)
    }


# =========================================================
# BASIC ROUTES
# =========================================================

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "message": "Movie Night backend is running",
        "room": MAIN_ROOM_ID
    })


@app.route("/api/health")
def health():

    return jsonify({
        "success": True,
        "status": "online",
        "room": MAIN_ROOM_ID
    })


# =========================================================
# MOVIES - PUBLIC
# =========================================================

@app.route("/api/movies", methods=["GET"])
def get_movies():

    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM movies ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "movies": [
            serialize_movie(row)
            for row in rows
        ]
    })


@app.route("/api/movies/<int:movie_id>", methods=["GET"])
def get_single_movie(movie_id):

    row = get_movie(movie_id)

    if not row:
        return jsonify({
            "success": False,
            "error": "فیلم پیدا نشد"
        }), 404

    return jsonify({
        "success": True,
        "movie": serialize_movie(row)
    })


# =========================================================
# MOVIE FILES
# =========================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_DIR,
        filename,
        conditional=True
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/api/admin/login", methods=["POST"])
def admin_login():

    data = request.get_json(silent=True) or {}

    password = str(
        data.get("password", "")
    )

    if not ADMIN_PASSWORD:
        return jsonify({
            "success": False,
            "error": "ADMIN_PASSWORD در محیط سرور تنظیم نشده است"
        }), 500

    if password != ADMIN_PASSWORD:

        add_log("Admin login failed")

        return jsonify({
            "success": False,
            "error": "رمز عبور اشتباه است"
        }), 401

    token = create_admin_token()

    add_log("Admin logged in")

    return jsonify({
        "success": True,
        "token": token
    })


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():

    token = request.headers.get(
        "X-Admin-Token",
        ""
    )

    if token in ADMIN_TOKENS:
        ADMIN_TOKENS.remove(token)

    return jsonify({
        "success": True
    })


@app.route("/api/admin/status")
def admin_status():

    return jsonify({
        "success": True,
        "logged_in": is_admin()
    })


# =========================================================
# ADMIN MOVIES
# =========================================================

@app.route("/api/admin/movies", methods=["POST"])
@admin_required
def admin_add_movie():

    title = (
        request.form.get("title")
        or request.form.get("name")
        or ""
    ).strip()

    video_file = request.files.get("file")

    if not title:
        return jsonify({
            "success": False,
            "error": "نام فیلم را وارد کنید"
        }), 400

    if not video_file:
        return jsonify({
            "success": False,
            "error": "فایل فیلم انتخاب نشده است"
        }), 400

    if not allowed_video(video_file.filename):

        return jsonify({
            "success": False,
            "error": "فرمت فایل ویدیو پشتیبانی نمی‌شود"
        }), 400

    original_name = Path(
        video_file.filename
    ).name

    extension = Path(
        original_name
    ).suffix.lower()

    safe_name = (
        f"{int(time.time())}_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file_path = UPLOAD_DIR / safe_name

    try:

        video_file.save(file_path)

    except Exception as e:

        print("UPLOAD ERROR:", e)

        return jsonify({
            "success": False,
            "error": "ذخیره فایل انجام نشد"
        }), 500

    relative_video = f"/uploads/{safe_name}"

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO movies
        (title, description, year, genre, poster, video)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            "",
            "",
            "",
            "",
            relative_video
        )
    )

    movie_id = cursor.lastrowid

    conn.commit()

    row = conn.execute(
        "SELECT * FROM movies WHERE id = ?",
        (movie_id,)
    ).fetchone()

    conn.close()

    add_log(
        f"Movie added: {title}"
    )

    return jsonify({
        "success": True,
        "movie": serialize_movie(row)
    })


@app.route("/api/admin/movies/<int:movie_id>", methods=["DELETE"])
@admin_required
def admin_delete_movie(movie_id):

    row = get_movie(movie_id)

    if not row:

        return jsonify({
            "success": False,
            "error": "فیلم پیدا نشد"
        }), 404

    video_path = row["video"]

    conn = get_db()

    conn.execute(
        "DELETE FROM movies WHERE id = ?",
        (movie_id,)
    )

    conn.commit()
    conn.close()

    if video_path.startswith("/uploads/"):

        filename = video_path.replace(
            "/uploads/",
            "",
            1
        )

        file_path = UPLOAD_DIR / filename

        try:

            if file_path.exists():
                file_path.unlink()

        except Exception as e:
            print("DELETE FILE ERROR:", e)

    add_log(
        f"Movie deleted: {row['title']}"
    )

    return jsonify({
        "success": True
    })


# =========================================================
# ADMIN UPLOAD - OPTIONAL
# =========================================================

@app.route("/api/admin/upload", methods=["POST"])
@admin_required
def admin_upload():

    uploaded = request.files.get("file")

    if not uploaded:

        return jsonify({
            "success": False,
            "error": "فایلی ارسال نشده است"
        }), 400

    if not allowed_video(uploaded.filename):

        return jsonify({
            "success": False,
            "error": "فرمت فایل ویدیو پشتیبانی نمی‌شود"
        }), 400

    original_name = Path(
        uploaded.filename
    ).name

    extension = Path(
        original_name
    ).suffix.lower()

    safe_name = (
        f"{int(time.time())}_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file_path = UPLOAD_DIR / safe_name

    uploaded.save(file_path)

    return jsonify({
        "success": True,
        "url": f"/uploads/{safe_name}"
    })


# =========================================================
# ADMIN STATS
# =========================================================

@app.route("/api/admin/stats")
@admin_required
def admin_stats():

    conn = get_db()

    movie_count = conn.execute(
        "SELECT COUNT(*) AS count FROM movies"
    ).fetchone()["count"]

    log_count = conn.execute(
        "SELECT COUNT(*) AS count FROM logs"
    ).fetchone()["count"]

    conn.close()

    room = create_room_if_needed(
        MAIN_ROOM_ID
    )

    online_count = len(
        room["connections"]
    )

    return jsonify({
        "success": True,
        "movies": movie_count,
        "logs": log_count,
        "online": online_count,
        "room": MAIN_ROOM_ID
    })


@app.route("/api/admin/logs")
@admin_required
def admin_logs():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM logs
        ORDER BY id DESC
        LIMIT 200
        """
    ).fetchall()

    conn.close()

    logs = []

    for row in rows:

        logs.append({
            "id": row["id"],
            "action": row["action"],
            "created_at": row["created_at"]
        })

    return jsonify({
        "success": True,
        "logs": logs
    })


# =========================================================
# ADMIN - DIRECT CONNECT MOVIE TO ROOM
# =========================================================

@app.route(
    "/api/admin/rooms/<room_id>/movie",
    methods=["POST"]
)
@admin_required
def admin_connect_movie(room_id):

    data = request.get_json(silent=True) or {}

    movie_id = data.get("movie_id")

    if not movie_id:

        return jsonify({
            "success": False,
            "error": "شناسه فیلم ارسال نشده است"
        }), 400

    try:
        movie_id = int(movie_id)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "error": "شناسه فیلم نامعتبر است"
        }), 400

    row = get_movie(movie_id)

    if not row:

        return jsonify({
            "success": False,
            "error": "فیلم پیدا نشد"
        }), 404

    movie = serialize_movie(row)

    room = create_room_if_needed(
        room_id
    )

    room["movie"] = movie
    room["playing"] = False
    room["current_time"] = 0.0
    room["updated_at"] = time.time()

    socketio.emit(
        "movie_changed",
        {
            "movie": movie,
            "current_time": 0,
            "playing": False
        },
        room=room_id
    )

    add_log(
        f"Movie connected to room {room_id}: {movie['title']}"
    )

    return jsonify({
        "success": True,
        "room": room_id,
        "movie": movie
    })


# =========================================================
# SOCKET.IO - JOIN ROOM
# =========================================================

@socketio.on("join_room")
def handle_join_room(data):

    data = data or {}

    room_id = str(
        data.get("room_id")
        or MAIN_ROOM_ID
    ).strip()

    name = str(
        data.get("name")
        or ""
    ).strip()

    if name not in FIXED_MEMBERS:

        emit(
            "join_error",
            {
                "error": "این نام در لیست اعضای اتاق نیست"
            }
        )

        return

    room = create_room_if_needed(
        room_id
    )

    # جلوگیری از ورود دوباره با یک نام
    for existing_sid, info in room["connections"].items():

        if info["name"] == name:

            emit(
                "join_error",
                {
                    "error": "این نام در حال حاضر داخل اتاق است"
                }
            )

            return

    if len(room["connections"]) >= MAX_ROOM_MEMBERS:

        emit(
            "join_error",
            {
                "error": "ظرفیت اتاق تکمیل است"
            }
        )

        return

    join_room(room_id)

    room["connections"][request.sid] = {
        "name": name,
        "status": "online",
        "last_seen": time.time()
    }

    sid_info[request.sid] = {
        "room_id": room_id,
        "name": name
    }

    emit(
        "joined",
        {
            "success": True,
            "room_id": room_id,
            "name": name
        }
    )

    emit(
        "room_state",
        get_room_state(room_id)
    )

    emit_members(room_id)

    socketio.emit(
        "system_message",
        {
            "text": f"{name} وارد اتاق شد"
        },
        room=room_id
    )

    add_log(
        f"{name} joined room {room_id}"
    )


# =========================================================
# SOCKET.IO - LEAVE ROOM
# =========================================================

@socketio.on("leave_room")
def handle_leave_room():

    info = sid_info.get(
        request.sid
    )

    if not info:
        return

    room_id = info["room_id"]
    name = info["name"]

    room = rooms.get(room_id)

    if room:

        room["connections"].pop(
            request.sid,
            None
        )

        leave_room(room_id)

        emit_members(room_id)

        socketio.emit(
            "system_message",
            {
                "text": f"{name} از اتاق خارج شد"
            },
            room=room_id
        )

    sid_info.pop(
        request.sid,
        None
    )


# =========================================================
# SOCKET.IO - DISCONNECT
# =========================================================

@socketio.on("disconnect")
def handle_disconnect():

    info = sid_info.pop(
        request.sid,
        None
    )

    if not info:
        return

    room_id = info["room_id"]
    name = info["name"]

    room = rooms.get(room_id)

    if not room:
        return

    room["connections"].pop(
        request.sid,
        None
    )

    emit_members(room_id)

    socketio.emit(
        "system_message",
        {
            "text": f"{name} از اتاق خارج شد"
        },
        room=room_id
    )

    add_log(
        f"{name} disconnected from room {room_id}"
    )


# =========================================================
# SOCKET.IO - HEARTBEAT / INTERNET STATUS
# =========================================================

@socketio.on("heartbeat")
def handle_heartbeat(data):

    info = sid_info.get(
        request.sid
    )

    if not info:
        return {
            "status": "offline"
        }

    room_id = info["room_id"]

    room = rooms.get(room_id)

    if not room:
        return {
            "status": "offline"
        }

    member = room["connections"].get(
        request.sid
    )

    if not member:
        return {
            "status": "offline"
        }

    latency = 0

    try:
        latency = float(
            (data or {}).get(
                "latency_ms",
                0
            )
        )

    except (TypeError, ValueError):
        latency = 0

    if latency >= 700:
        status = "weak"

    else:
        status = "online"

    member["status"] = status
    member["last_seen"] = time.time()

    emit_members(room_id)

    return {
        "status": status,
        "latency_ms": latency
    }


# =========================================================
# SOCKET.IO - PLAY
# =========================================================

@socketio.on("video_play")
def handle_video_play(data):

    info = sid_info.get(
        request.sid
    )

    if not info:
        return

    room_id = info["room_id"]

    room = rooms.get(room_id)

    if not room:
        return

    current_time = float(
        (data or {}).get(
            "current_time",
            0
        )
    )

    room["current_time"] = max(
        0.0,
        current_time
    )

    room["playing"] = True
    room["updated_at"] = time.time()

    emit(
        "video_play",
        {
            "current_time": room["current_time"],
            "by": info["name"]
        },
        room=room_id,
        include_self=False
    )


# =========================================================
# SOCKET.IO - PAUSE
# =========================================================

@socketio.on("video_pause")
def handle_video_pause(data):

    info = sid_info.get(
        request.sid
    )

    if not info:
        return

    room_id = info["room_id"]

    room = rooms.get(room_id)

    if not room:
        return

    current_time = float(
        (data or {}).get(
            "current_time",
            0
        )
    )

    room["current_time"] = max(
        0.0,
        current_time
    )

    room["playing"] = False
    room["updated_at"] = time.time()

    emit(
        "video_pause",
        {
            "current_time": room["current_time"],
            "by": info["name"]
        },
        room=room_id,
        include_self=False
    )

    socketio.emit(
        "system_message",
        {
            "text": f"{info['name']} ویدیو رو متوقف کرد"
        },
        room=room_id
    )


# =========================================================
# SOCKET.IO - SEEK
# =========================================================

@socketio.on("video_seek")
def handle_video_seek(data):

    info = sid_info.get(
        request.sid
    )

    if not info:
        return

    room_id = info["room_id"]

    room = rooms.get(room_id)

    if not room:
        return

    current_time = float(
        (data or {}).get(
            "current_time",
            0
        )
    )

    room["current_time"] = max(
        0.0,
        current_time
    )

    room["updated_at"] = time.time()

    emit(
        "video_seek",
        {
            "current_time": room["current_time"],
            "by": info["name"]
        },
        room=room_id,
        include_self=False
    )


# =========================================================
# SOCKET.IO - CHAT
# =========================================================

@socketio.on("chat_message")
def handle_chat_message(data):

    info = sid_info.get(
        request.sid
    )

    if not info:
        return

    room_id = info["room_id"]

    text = str(
        (data or {}).get(
            "text",
            ""
        )
    ).strip()

    if not text:
        return

    if len(text) > 1000:
        text = text[:1000]

    socketio.emit(
        "new_message",
        {
            "name": info["name"],
            "text": text,
            "created_at": time.time()
        },
        room=room_id
    )


# =========================================================
# SOCKET.IO - ROOM MOVIE STATE
# =========================================================

@socketio.on("request_room_state")
def handle_request_room_state():

    info = sid_info.get(
        request.sid
    )

    if not info:
        return

    room_id = info["room_id"]

    emit(
        "room_state",
        get_room_state(room_id)
    )


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "success": False,
        "error": "حجم فایل بیش از حد مجاز است"
    }), 413


@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "error": "مسیر موردنظر پیدا نشد"
    }), 404


@app.errorhandler(500)
def server_error(error):

    return jsonify({
        "success": False,
        "error": "خطای داخلی سرور"
    }), 500


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    if not ADMIN_PASSWORD:
        print("")
        print("=" * 60)
        print("هشدار: ADMIN_PASSWORD تنظیم نشده است.")
        print("قبل از اجرا در Termux این دستور را بزن:")
        print("export ADMIN_PASSWORD='رمز مدیریت'")
        print("=" * 60)
        print("")

    print("")
    print("=" * 60)
    print("Movie Night Backend")
    print(f"Room: {MAIN_ROOM_ID}")
    print(f"Port: {PORT}")
    print("=" * 60)
    print("")

    socketio.run(
        app,
        host=HOST,
        port=PORT,
        debug=False,
        allow_unsafe_werkzeug=True
    )
