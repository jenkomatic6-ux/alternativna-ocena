from flask import Flask, render_template, request, redirect, session, jsonify
from tinydb import TinyDB, Query

app = Flask(__name__, template_folder="templates2", static_folder="static2")
app.secret_key = "skrivnost123"

db = TinyDB("db.json")
users = db.table("users")

User = Query()

# homepage
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

        users.insert({"username" : username, "password" : password, "note" : ""})
        return redirect("/login")      

        #print(username,password)
    return render_template("register.html")


@app.route("/login", methods = ["GET","POST"])
def login():

    if request.method == "POST":
        username=request.form["username"]
        password=request.form["password"]
        
        user = users.get(User.username == username)
        #print(user)

        if user and user["password"] == password:
            session["user"] = username
            return redirect("/dashboard")

        return "Napačen login"

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return render_template("dashboard.html", user = session["user"])

app.run(debug=1)

