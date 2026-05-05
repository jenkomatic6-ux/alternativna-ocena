from flask import Flask, render_template, request, redirect, session,jsonify
import sqlite3
import requests
from datetime import datetime, timedelta


app = Flask(__name__, template_folder="templates2", static_folder="static2")
app.secret_key = "secret123"

DATABASE = "app.db"


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            created_at TEXT,
            edit_until TEXT
        )
    """)
    db.commit()
    db.close()


init_db()



def get_time():
    try:
        r = requests.get("https://timeapi.io/api/time/current/zone?timeZone=Europe/Ljubljana")
        d = r.json()
        return datetime(d["year"], d["month"], d["day"], d["hour"], d["minute"], d["seconds"])
    except:
        return datetime.now()



@app.route("/")
def home():
    return redirect("/login")


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if user:
            return "Uporabnik že obstaja!"

        db.execute("INSERT INTO users (username,password) VALUES (?,?)", (username,password))
        db.commit()
        db.close()

        return redirect("/login")

    return render_template("register.html")


# 🔹 LOGIN
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        db.close()

        if user and user["password"] == password:
            session["user"] = user["username"]
            session["user_id"] = user["id"]
            return redirect("/dashboard")

        return "Napačen login"

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")




@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    db = get_db()

    posts = db.execute("""
        SELECT posts.*, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """).fetchall()

    now = get_time()

    posts_fixed = []
    for p in posts:
        p = dict(p)
        if p["edit_until"]:
            p["edit_until"] = datetime.fromisoformat(p["edit_until"])
        posts_fixed.append(p)

    return render_template(
        "dashboard.html",
        user=session["user"],
        posts=posts_fixed,
        now=now
    )



@app.route("/create_post", methods=["POST"])
def create_post():
    if "user_id" not in session:
        return jsonify({"success":False})

    content = request.form["content"]

    now= get_time()
    edit_until = now + timedelta(hours=24)

    db = get_db()
    db.execute(
        "INSERT INTO posts (user_id, content, created_at, edit_until) VALUES (?, ?, ?, ?)",
        (session["user_id"], content, now.isoformat(), edit_until.isoformat())
    )
    db.commit()
    db.close()

    return jsonify({"success":True})




@app.route("/edit_post/<int:post_id>", methods=["GET","POST"])
def edit_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()

    if not post:
        return "Post ne obstaja"

    if post["user_id"] != session["user_id"]:
        return "Ni tvoj post"

    now = get_time()

    if now > datetime.fromisoformat(post["edit_until"]):
        return "Prepozno za urejanje (24h mimo)"

    if request.method == "POST":
        new_content = request.form["content"]

        db.execute("UPDATE posts SET content=? WHERE id=?", (new_content, post_id))
        db.commit()
        db.close()

        return redirect("/dashboard")

    return render_template("edit.html", post=post)


if __name__ == "__main__":
    app.run(debug=True)