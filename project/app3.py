from flask import Flask, render_template, request, redirect, session, jsonify
from tinydb import TinyDB, Query
import random


app = Flask(__name__, template_folder="templates3", static_folder="static3")
app.secret_key = "skrivnost123"

db = TinyDB("db/db.json")
users = db.table("users")
documents = db.table("documents")

User = Query()
Document = Query()


def generate_password(length):
    password= ""
    for _ in range(length):
        password += chr(random.randint(32,126))
    return password


@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")


@app.route("/register", methods = ["GET","POST"])
def register():
    if request.method == "POST":
        username=request.form["username"]
        password=request.form["password"]
        
        if users.search(User.username == username):
            return "Uporabnik že obstaja!"

        users.insert({
            "username" : username,
            "password" : password,
            "note" : ""
            })

        return redirect("/login")      
    return render_template("register.html")


@app.route("/login", methods = ["GET","POST"])
def login():

    if request.method == "POST":
        username=request.form["username"]
        password=request.form["password"]
        
        user = users.get(User.username == username)

        if user and user["password"] == password:
            session["user"] = username
            return redirect("/dashboard")

        return "Napačen login"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")
    password = None

    if request.method == "POST":
        try:
            length = int(request.form["length"])
        except:
            length = 8
        
        password = generate_password(length)

    return render_template(
        "dashboard.html",
        user=session["user"],
        password=password
    )

app.run(debug=1)