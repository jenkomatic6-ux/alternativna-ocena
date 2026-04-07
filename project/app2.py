from flask import Flask, render_template, request, redirect, session, jsonify, g
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from datetime import datetime, timedelta

app = Flask(__name__, template_folder="templates2", static_folder="static2")
app.secret_key = "skrivnost123"

DATABASE = "app2.db"


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


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            bio TEXT DEFAULT ''
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    db.commit()


@app.before_request
def setup():
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
            (username,)
        ).fetchone()

        if existing_user:
            return "Uporabnik že obstaja."

        hashed_password = generate_password_hash(password)

        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)
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
            (username,)
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
            (username,)
        ).fetchone()

        if not user:
            return "Uporabnik ne obstaja."

        hashed = generate_password_hash(new_password)

        db.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed, username)
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
    posts = db.execute("""
        SELECT posts.id, posts.content, posts.created_at, users.username, users.id as author_id
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """).fetchall()

    return render_template("dashboard.html", user=session["username"], posts=posts)


# -------------------------
# CREATE POST (AJAX)
# -------------------------
@app.route("/create_post", methods=["POST"])
def create_post():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Nisi prijavljen."}), 401

    content = request.form["content"].strip()

    if not content:
        return jsonify({"success": False, "message": "Objava ne sme biti prazna."})

    db = get_db()
    db.execute(
        "INSERT INTO posts (user_id, content) VALUES (?, ?)",
        (session["user_id"], content)
    )
    db.commit()

    new_post = db.execute("""
        SELECT posts.id, posts.content, posts.created_at, users.username, users.id as author_id
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE posts.id = last_insert_rowid()
    """).fetchone()

    return jsonify({
        "success": True,
        "post": {
            "id": new_post["id"],
            "content": new_post["content"],
            "created_at": new_post["created_at"],
            "username": new_post["username"],
            "author_id": new_post["author_id"]
        }
    })


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
        (post_id,)
    ).fetchone()

    if not post:
        return jsonify({"success": False, "message": "Objava ne obstaja."})

    if post["user_id"] != session["user_id"]:
        return jsonify({"success": False, "message": "To ni tvoja objava."}), 403

    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()

    return jsonify({"success": True})


# -------------------------
# POST
# -------------------------
@app.route("/create_post", methods=["GET"])
def create_post_page():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("post_form.html")



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
        (username,)
    ).fetchone()

    if not profile_user:
        return "Uporabnik ne obstaja."

    user_posts = db.execute("""
        SELECT posts.id, posts.content, posts.created_at
        FROM posts
        WHERE posts.user_id = ?
        ORDER BY posts.id DESC
    """, (profile_user["id"],)).fetchall()

    is_own_profile = session["user_id"] == profile_user["id"]

    return render_template(
        "profile.html",
        profile_user=profile_user,
        posts=user_posts,
        is_own_profile=is_own_profile
    )


# -------------------------
# EDIT PROFILE
# -------------------------
@app.route("/edit_profile", methods=["POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect("/login")

    bio = request.form["bio"].strip()

    db = get_db()
    db.execute(
        "UPDATE users SET bio = ? WHERE id = ?",
        (bio, session["user_id"])
    )
    db.commit()

    return redirect(f"/profile/{session['username']}")

app.run(debug=True)