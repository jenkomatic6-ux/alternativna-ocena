from flask import Flask, render_template, request, redirect, session, jsonify
from tinydb import TinyDB, Query
from werkzeug.utils import secure_filename
import os
import time

app = Flask(__name__, template_folder="templates3", static_folder="static3")
app.secret_key = "skrivnost123"

db = TinyDB("db3.json")
users = db.table("users")
products = db.table("products")

User = Query()
Product = Query()

UPLOAD_FOLDER = os.path.join("static3", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return redirect("/dashboard")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            return "Izpolni vsa polja."

        if users.search(User.username == username):
            return "Uporabnik že obstaja."

        users.insert({
            "username": username,
            "password": password
        })

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        user = users.get((User.username == username) & (User.password == password))

        if user:
            session["user"] = username
            return redirect("/dashboard")

        return "Napačen login."

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/dashboard")


@app.route("/dashboard")
def dashboard():
    all_products = products.all()
    all_products.reverse()
    return render_template("dashboard.html", products=all_products)


@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        brand = request.form["brand"].strip()
        power_type = request.form["power_type"].strip()
        chain_length = request.form["chain_length"].strip()
        price = request.form["price"].strip()

        image_name = ""

        file = request.files.get("image")
        if file and file.filename != "":
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                image_name = str(int(time.time())) + "_" + filename
                file.save(os.path.join(UPLOAD_FOLDER, image_name))
            else:
                return "Dovoljene so samo slike."

        products.insert({
            "username": session["user"],
            "title": title,
            "description": description,
            "brand": brand,
            "power_type": power_type,
            "chain_length": chain_length,
            "price": price,
            "image": image_name
        })

        return redirect("/dashboard")

    return render_template("post.html")


@app.route("/delete_product/<int:doc_id>", methods=["POST"])
def delete_product(doc_id):
    if "user" not in session:
        return redirect("/login")

    product = products.get(doc_id=doc_id)

    if not product:
        return "Izdelek ne obstaja."

    if product["username"] != session["user"]:
        return "To ni tvoj izdelek."

    if product["image"]:
        image_path = os.path.join(UPLOAD_FOLDER, product["image"])
        if os.path.exists(image_path):
            os.remove(image_path)

    products.remove(doc_ids=[doc_id])
    return redirect("/dashboard")


@app.route("/search")
def search():
    term = request.args.get("q", "").strip().lower()

    if term == "":
        result = products.all()
    else:
        result = []
        for product in products.all():
            if term in product["title"].lower():
                result.append(product)

    result.reverse()

    data = []
    for product in result:
        item = dict(product)
        item["doc_id"] = product.doc_id
        item["can_delete"] = "user" in session and product["username"] == session["user"]
        data.append(item)

    return jsonify(data)

app.run(debug=True)