
import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"


def get_collection():
    """Connect to MongoDB Atlas and return the submissions collection."""
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME", "flask_assignment")

    if not mongo_uri:
        raise RuntimeError("MONGO_URI is missing. Configure your .env file.")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[db_name]["submissions"]


@app.route("/")
def home():
    return render_template("index.html", error=None, form_data={})


@app.route("/api", methods=["GET"])
def api():
    """Read JSON data from a backend file and return it as JSON."""
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return jsonify(data), 200

    except (OSError, json.JSONDecodeError) as error:
        app.logger.exception("Could not read the JSON data file")
        return jsonify({"error": "Unable to load API data."}), 500


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    form_data = {
        "name": name,
        "email": email,
        "message": message
    }

    # Validate before attempting database insertion.
    if not name or not email or not message:
        return render_template(
            "index.html",
            error="Please fill in all fields.",
            form_data=form_data
        ), 400

    try:
        collection = get_collection()

        collection.insert_one({
            "name": name,
            "email": email,
            "message": message
        })

        return redirect(url_for("success"))

    except (PyMongoError, RuntimeError, ValueError):
        app.logger.exception("Form submission failed")

        return render_template(
            "index.html",
            error="Could not save your data. Check the database connection and try again.",
            form_data=form_data
        ), 500


@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
