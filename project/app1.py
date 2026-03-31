from flask import Flask, render_template, request, redirect, session, jsonify
from tinydb import TinyDB, Query



app = Flask(__name__, template_folder="templates1", static_folder="static1")
app.secret_key = "skrivnost123"

db = TinyDB("db/db.json")
users = db.table("users")
documents = db.table("documents")

User = Query()
Document = Query()

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


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    user_docs = documents.search(Document.owner == session["user"])
    return render_template("dashboard.html", user=session["user"], documents=user_docs)


@app.route("/new_document", methods=["POST"])
def new_document():
    if "user" not in session:
        return jsonify({"success": False})

    doc_id = len(documents) + 1

    documents.insert({
        "id": doc_id,
        "owner": session["user"],
        "title": f"Dokument {doc_id}",
        "content": ""
    })

    return jsonify({"success": True, "doc_id": doc_id})

@app.route("/editor/<int:doc_id>")
def editor(doc_id):
    if "user" not in session:
        return redirect("/login")

    doc = documents.get((Document.id == doc_id) & (Document.owner == session["user"]))
    if not doc:
        return "Dokument ne obstaja"

    return render_template("editor.html", doc=doc)


@app.route("/save_document/<int:doc_id>", methods=["POST"])
def save_document(doc_id):
    if "user" not in session:
        return jsonify({"success": False})

    title = request.form["title"]
    content = request.form["content"]

    documents.update(
        {"title": title, "content": content},
        (Document.id == doc_id) & (Document.owner == session["user"])
    )

    return jsonify({"success": True})


@app.route("/delete_document/<int:doc_id>", methods=["POST"])
def delete_document(doc_id):
    if "user" not in session:
        return jsonify({"success": False})

    documents.remove((Document.id == doc_id) & (Document.owner == session["user"]))
    return jsonify({"success": True})


@app.route("/search_documents")
def search_documents():
    if "user" not in session:
        return jsonify([])

    q = request.args.get("q", "").lower()
    user_docs = documents.search(Document.owner == session["user"])

    filtered = []
    for doc in user_docs:
        if q in doc["title"].lower() or q in doc["content"].lower():
            filtered.append(doc)

    return jsonify(filtered)

app.run(debug=1)