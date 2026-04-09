from flask import Flask, render_template, request, redirect, session, jsonify, g, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
from datetime import datetime, timedelta
import os
import uuid

app = Flask(__name__, template_folder="templates2", static_folder="static2")
app.secret_key = "skrivnost123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "app2.db")
PROFILE_UPLOAD_FOLDER = os.path.join(BASE_DIR, "static2", "uploads", "profile_pics")
POST_UPLOAD_FOLDER = os.path.join(BASE_DIR, "static2", "uploads", "post_images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


# -------------------------
# FILES
# -------------------------
def ensure_folders():
    os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(POST_UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, folder):
    if not file or file.filename == "":
        return None

    if not allowed_file(file.filename):
        return None

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    full_path = os.path.join(folder, new_filename)
    file.save(full_path)

    if folder == PROFILE_UPLOAD_FOLDER:
        return f"uploads/profile_pics/{new_filename}"
    return f"uploads/post_images/{new_filename}"


# -------------------------
# TIME API
# -------------------------
def get_current_time():
    try:
        response = requests.get(
            "https://timeapi.io/api/time/current/zone?timeZone=Europe/Ljubljana",
            timeout=5,
        )
        data = response.json()
        return datetime(
            data["year"],
            data["month"],
            data["day"],
            data["hour"],
            data["minute"],
            data["seconds"],
        )
    except Exception:
        return datetime.now()


def can_manage_post(edit_until):
    if not edit_until:
        return False
    return get_current_time() <= datetime.fromisoformat(edit_until)


# -------------------------
# DATABASE
# -------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def column_exists(table_name, column_name):
    db = get_db()
    columns = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column[1] == column_name for column in columns)


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            bio TEXT DEFAULT '',
            profile_image TEXT DEFAULT ''
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            image_path TEXT DEFAULT '',
            created_at TEXT,
            edit_until TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # simple migration for older db files
    if not column_exists("users", "bio"):
        db.execute("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''")
    if not column_exists("users", "profile_image"):
        db.execute("ALTER TABLE users ADD COLUMN profile_image TEXT DEFAULT ''")
    if not column_exists("posts", "image_path"):
        db.execute("ALTER TABLE posts ADD COLUMN image_path TEXT DEFAULT ''")
    if not column_exists("posts", "created_at"):
        db.execute("ALTER TABLE posts ADD COLUMN created_at TEXT")
    if not column_exists("posts", "edit_until"):
        db.execute("ALTER TABLE posts ADD COLUMN edit_until TEXT")

    db.commit()


@app.before_request
def setup():
    ensure_folders()
    init_db()


# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")


# -------------------------
# REGISTER
# -------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            return "Izpolni vsa polja."

        db = get_db()
        existing_user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if existing_user:
            return "Uporabnik že obstaja."

        hashed_password = generate_password_hash(password)

        db.execute(
            "INSERT INTO users (username, password, bio, profile_image) VALUES (?, ?, '', '')",
            (username, hashed_password),
        )
        db.commit()

        return redirect("/login")

    return render_template("register.html")


# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")

        return "Napačen username ali password."

    return render_template("login.html")


# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -------------------------
# RESET PASSWORD
# -------------------------
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        username = request.form["username"].strip()
        new_password = request.form["new_password"].strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not user:
            return "Uporabnik ne obstaja."

        hashed = generate_password_hash(new_password)

        db.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed, username),
        )
        db.commit()

        return redirect("/login")

    return render_template("password_form.html")


# -------------------------
# DASHBOARD
# -------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    rows = db.execute("""
        SELECT posts.id, posts.content, posts.image_path, posts.created_at, posts.edit_until,
               users.username, users.id as author_id, users.profile_image
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """).fetchall()

    posts = []
    for row in rows:
        post = dict(row)
        post["can_manage"] = row["author_id"] == session["user_id"] and can_manage_post(row["edit_until"])
        posts.append(post)

    return render_template("dashboard.html", user=session["username"], posts=posts)


# -------------------------
# CREATE POST (AJAX)
# -------------------------
@app.route("/create_post", methods=["POST"])
def create_post():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Nisi prijavljen."}), 401

    content = request.form.get("content", "").strip()
    image = request.files.get("image")

    if not content and (not image or image.filename == ""):
        return jsonify({"success": False, "message": "Dodaj besedilo ali sliko."})

    image_path = save_image(image, POST_UPLOAD_FOLDER)
    if image and image.filename and not image_path:
        return jsonify({"success": False, "message": "Dovoljene slike: png, jpg, jpeg, gif, webp."})

    created_at = get_current_time()
    edit_until = created_at + timedelta(hours=24)

    db = get_db()
    db.execute(
        "INSERT INTO posts (user_id, content, image_path, created_at, edit_until) VALUES (?, ?, ?, ?, ?)",
        (
            session["user_id"],
            content,
            image_path or "",
            created_at.isoformat(timespec="seconds"),
            edit_until.isoformat(timespec="seconds"),
        ),
    )
    db.commit()

    new_post = db.execute("""
        SELECT posts.id, posts.content, posts.image_path, posts.created_at, posts.edit_until,
               users.username, users.id as author_id, users.profile_image
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE posts.id = last_insert_rowid()
    """).fetchone()

    return jsonify({
        "success": True,
        "post": {
            "id": new_post["id"],
            "content": new_post["content"],
            "image_path": new_post["image_path"],
            "image_url": url_for("static", filename=new_post["image_path"]) if new_post["image_path"] else "",
            "created_at": new_post["created_at"],
            "username": new_post["username"],
            "author_id": new_post["author_id"],
            "profile_image": new_post["profile_image"],
            "profile_image_url": url_for("static", filename=new_post["profile_image"]) if new_post["profile_image"] else "",
        },
    })


# -------------------------
# EDIT POST
# -------------------------
@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()

    if not post:
        return "Objava ne obstaja."
    if post["user_id"] != session["user_id"]:
        return "To ni tvoja objava."
    if not can_manage_post(post["edit_until"]):
        return "Objavo lahko urejaš samo 24 ur po objavi."

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        image = request.files.get("image")
        current_image_path = post["image_path"] or ""

        if not content and current_image_path == "" and (not image or image.filename == ""):
            return "Objava ne sme biti prazna."

        new_image_path = current_image_path
        if image and image.filename:
            saved = save_image(image, POST_UPLOAD_FOLDER)
            if not saved:
                return "Dovoljene slike: png, jpg, jpeg, gif, webp."
            new_image_path = saved

        db.execute(
            "UPDATE posts SET content = ?, image_path = ? WHERE id = ?",
            (content, new_image_path, post_id),
        )
        db.commit()
        return redirect("/dashboard")

    return render_template("post_form.html", post=post, edit_mode=True)


# -------------------------
# DELETE POST (AJAX)
# -------------------------
@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Nisi prijavljen."}), 401

    db = get_db()
    post = db.execute(
        "SELECT * FROM posts WHERE id = ?",
        (post_id,),
    ).fetchone()

    if not post:
        return jsonify({"success": False, "message": "Objava ne obstaja."})

    if post["user_id"] != session["user_id"]:
        return jsonify({"success": False, "message": "To ni tvoja objava."}), 403

    if not can_manage_post(post["edit_until"]):
        return jsonify({"success": False, "message": "Objavo lahko izbrišeš samo 24 ur po objavi."}), 403

    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()

    return jsonify({"success": True})


# -------------------------
# PROFILE
# -------------------------
@app.route("/profile/<username>")
def profile(username):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    profile_user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if not profile_user:
        return "Uporabnik ne obstaja."

    user_posts = db.execute("""
        SELECT posts.id, posts.content, posts.image_path, posts.created_at
        FROM posts
        WHERE posts.user_id = ?
        ORDER BY posts.id DESC
    """, (profile_user["id"],)).fetchall()

    is_own_profile = session["user_id"] == profile_user["id"]

    return render_template(
        "profile.html",
        profile_user=profile_user,
        posts=user_posts,
        is_own_profile=is_own_profile,
    )


# -------------------------
# EDIT PROFILE
# -------------------------
@app.route("/edit_profile", methods=["POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect("/login")

    bio = request.form.get("bio", "").strip()
    image = request.files.get("profile_image")

    db = get_db()
    current_user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    profile_image = current_user["profile_image"] or ""

    if image and image.filename:
        saved = save_image(image, PROFILE_UPLOAD_FOLDER)
        if saved:
            profile_image = saved

    db.execute(
        "UPDATE users SET bio = ?, profile_image = ? WHERE id = ?",
        (bio, profile_image, session["user_id"]),
    )
    db.commit()

    return redirect(f"/profile/{session['username']}")


app.run(debug=True)