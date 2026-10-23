
import hashlib
import json
import os
import uuid
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"


def get_collection(collection_name="submissions"):
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME", "flask_assignment")

    if not mongo_uri:
        raise RuntimeError("MONGO_URI is missing. Configure your .env file.")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[db_name][collection_name]


@app.route("/")
def home():
    return render_template("index.html", error=None, form_data={})


@app.route("/api", methods=["GET"])
def api():
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return jsonify(data), 200

    except (OSError, json.JSONDecodeError):
        app.logger.exception("Could not read JSON data")
        return jsonify({"error": "Unable to load API data."}), 500


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    form_data = {"name": name, "email": email, "message": message}

    if not name or not email or not message:
        return render_template(
            "index.html",
            error="Please fill in all fields.",
            form_data=form_data
        ), 400

    try:
        collection = get_collection()
        collection.insert_one(form_data)
        return redirect(url_for("success"))

    except (PyMongoError, RuntimeError, ValueError):
        app.logger.exception("Contact form submission failed")
        return render_template(
            "index.html",
            error="Could not save your data. Check the database connection.",
            form_data=form_data
        ), 500


@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/todo", methods=["GET"])
def todo_form():
    return render_template("todo.html", item=None, error=None)


@app.route("/submittodoitem", methods=["POST"])
def submit_todo_item():
    item_name = request.form.get("itemName", "").strip()
    item_description = request.form.get("itemDescription", "").strip()

    if not item_name or not item_description:
        return render_template(
            "todo.html",
            item=None,
            error="Item Name and Item Description are required."
        ), 400

    item_id = str(ObjectId())
    item_uuid = str(uuid.uuid4())

    hash_input = f"{item_name}:{item_description}:{item_uuid}"
    item_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    item = {
        "itemId": item_id,
        "itemName": item_name,
        "itemDescription": item_description,
        "itemUUID": item_uuid,
        "itemHash": item_hash
    }

    try:
        collection = get_collection("todos")
        collection.insert_one({
            "_id": ObjectId(item_id),
            **item
        })

        return render_template(
            "todo.html",
            item=item,
            error=None,
            message="To-Do item saved successfully!"
        ), 201

    except (PyMongoError, RuntimeError, ValueError):
        app.logger.exception("To-Do submission failed")
        return render_template(
            "todo.html",
            item=None,
            error="Could not save the To-Do item. Check MongoDB configuration."
        ), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)