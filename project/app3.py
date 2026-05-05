from flask import Flask, render_template, request, redirect, session, jsonify
from tinydb import TinyDB, Query
import random


app = Flask(__name__, template_folder="templates3", static_folder="static3")
app.secret_key = "skrivnost123"

db = TinyDB("db3/db.json")
users = db.table("users")
documents = db.table("documents")

User = Query()
Document = Query()


def generate_password(length,words,numbers,signs):
    luft=""

    if words:
        luft+="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if numbers:
        luft+="0123456789"
    if signs:
        luft+="!@#$%^&*()_+-=[]|;:,.<>?"
    if luft == "":
        luft = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]|;:,.<>?"
    
    
    password =""
    for _ in range(length):
        password += random.choice(luft)
    return password

def check_strength(password):
    if len(password) < 8:
        return "WEAK"
    if len(password) < 12:
        return "MEDIUM"
    else:
        return "STRONG"



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
    strength = None
    user_docs = documents.search(Document.owner == session["user"])

    if request.method == "POST":
        try:
            length = int(request.form["length"])
        except:
            length = 8
        

        words= request.form.get("obcija1")
        numbers= request.form.get("obcija2")
        signs= request.form.get("obcija3")

        password= generate_password(length,words,numbers,signs)
        strength= check_strength(password)

    return render_template(
        "dashboard.html",
        user=session["user"],
        password=password,
        strength=strength,
        documents= user_docs
    )


@app.route("/save_password",methods=["POST"])
def save_password():
    if "user" not in session:
        return redirect("/login")
    
    name=request.form["name"]
    password=request.form["password"]

    documents.insert({
        "owner":session["user"],
        "name":name,
        "password": password
    })

    return redirect("/dashboard")

app.run(debug=1)