from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from services.ai_generator import generate_course
import os
import traceback


load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "https://ai-course-frontend-olive.vercel.app"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response
# ---------------------------
# MongoDB Connection
# ---------------------------
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI not found in .env file")

client = MongoClient(MONGO_URI)
db = client["ai_course_builder"]

users_collection = db["users"]
courses_collection = db["courses"]


# ---------------------------
# Helpers
# ---------------------------
def serialize_course(course):
    return {
        "id": str(course["_id"]),
        "user_id": str(course["user_id"]),
        "title": course.get("title", ""),
        "topic": course.get("topic", ""),
        "modules": course.get("modules", []),
        "mcq": course.get("mcq", []),
        "assignment": course.get("assignment"),
        "isProgramming": course.get("isProgramming", False),
        "youtube": course.get("youtube", []),
        "articles": course.get("articles", []),
        "progress": course.get("progress", {})
    }


def calculate_grade(progress, is_programming):
    progress = progress or {}

    if is_programming:
        notes_score = 20 if progress.get("notesCompleted") else 0
        videos_score = 20 if progress.get("videosCompleted") else 0
        assessment_score = round((progress.get("assessmentScore", 0) / 100) * 20)
        coding_score = progress.get("codingScore", 0)
        articles_score = 20 if progress.get("articlesCompleted") else 0

        overall_score = notes_score + videos_score + assessment_score + coding_score + articles_score
    else:
        notes_score = 25 if progress.get("notesCompleted") else 0
        videos_score = 25 if progress.get("videosCompleted") else 0
        assessment_score = round((progress.get("assessmentScore", 0) / 100) * 25)
        articles_score = 25 if progress.get("articlesCompleted") else 0

        overall_score = notes_score + videos_score + assessment_score + articles_score

    if overall_score >= 90:
        grade = "A+"
    elif overall_score >= 80:
        grade = "A"
    elif overall_score >= 70:
        grade = "B"
    elif overall_score >= 60:
        grade = "C"
    elif overall_score >= 50:
        grade = "D"
    else:
        grade = "F"

    return overall_score, grade


@app.route("/")
def home():
    return "AI Course Builder Backend Running with MongoDB"


# ---------------------------
# REGISTER API
# ---------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400

    try:
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return jsonify({"error": "Email already exists"}), 409

        hashed_password = generate_password_hash(password)

        result = users_collection.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": "user"
        })

        return jsonify({
            "message": "User registered successfully",
            "user_id": str(result.inserted_id)
        }), 201

    except Exception as e:
        print("BACKEND ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# LOGIN API
# ---------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        user = users_collection.find_one({"email": email})

        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        if not check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid email or password"}), 401

        return jsonify({
            "message": "Login successful",
            "user": {
                "id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"],
                "role": user.get("role", "user")
            }
        }), 200

    except Exception as e:
        print("LOGIN ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# GENERATE + SAVE COURSE API
# ---------------------------
@app.route("/generate", methods=["POST", "OPTIONS"])
def generate():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200

    data = request.get_json()
    topic = data.get("topic")
    user_id = data.get("user_id")

    if not topic:
        return jsonify({"error": "Topic required"}), 400

    try:
        course = generate_course(topic)

        if user_id:
            progress = {
                "notesCompleted": False,
                "videosCompleted": False,
                "assessmentCompleted": False,
                "codingCompleted": False,
                "articlesCompleted": False,
                "assessmentScore": 0,
                "codingScore": 0
            }

            course_doc = {
                "user_id": ObjectId(user_id),
                "title": course.get("title"),
                "topic": topic,
                "modules": course.get("modules", []),
                "mcq": course.get("mcq", []),
                "assignment": course.get("assignment"),
                "isProgramming": course.get("isProgramming", False),
                "youtube": course.get("youtube", []),
                "articles": course.get("articles", []),
                "progress": progress
            }

            result = courses_collection.insert_one(course_doc)
            course["id"] = str(result.inserted_id)
            course["user_id"] = user_id

        return jsonify({"course": course}), 200

    except Exception as e:
        print("GENERATE ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# GET ALL COURSES OF A USER
# ---------------------------
@app.route("/courses/<user_id>", methods=["GET"])
def get_courses(user_id):
    try:
        courses = courses_collection.find(
            {"user_id": ObjectId(user_id)}
        ).sort("_id", -1)

        courses_list = [serialize_course(course) for course in courses]

        return jsonify({"courses": courses_list}), 200

    except Exception as e:
        print("GET COURSES ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# GET ONE COURSE
# ---------------------------
@app.route("/course/<course_id>", methods=["GET"])
def get_course(course_id):
    try:
        course = courses_collection.find_one({"_id": ObjectId(course_id)})

        if not course:
            return jsonify({"error": "Course not found"}), 404

        return jsonify({"course": serialize_course(course)}), 200

    except Exception as e:
        print("GET COURSE ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# DELETE COURSE
# ---------------------------
@app.route("/course/<course_id>", methods=["DELETE"])
def delete_course(course_id):
    try:
        result = courses_collection.delete_one({"_id": ObjectId(course_id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Course not found"}), 404

        return jsonify({"message": "Course deleted successfully"}), 200

    except Exception as e:
        print("DELETE ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# UPDATE PROGRESS
# ---------------------------
@app.route("/course/<course_id>/progress", methods=["PUT"])
def update_progress(course_id):
    data = request.get_json()
    progress = data.get("progress")

    if not progress:
        return jsonify({"error": "Progress data required"}), 400

    try:
        result = courses_collection.update_one(
            {"_id": ObjectId(course_id)},
            {"$set": {"progress": progress}}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Course not found"}), 404

        return jsonify({"message": "Progress updated successfully"}), 200

    except Exception as e:
        print("UPDATE PROGRESS ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# ADMIN DASHBOARD
# ---------------------------
@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():
    admin_email = request.args.get("email")

    if not admin_email:
        return jsonify({"error": "Admin email required"}), 400

    try:
        admin_user = users_collection.find_one({"email": admin_email})

        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Unauthorized access"}), 403

        users = users_collection.find({}, {"name": 1, "email": 1, "role": 1})

        dashboard_data = []

        for user in users:
            if user.get("role") == "admin":
                continue

            user_courses = list(courses_collection.find({"user_id": user["_id"]}))

            if not user_courses:
                dashboard_data.append({
                    "user_id": str(user["_id"]),
                    "name": user.get("name", ""),
                    "email": user.get("email", ""),
                    "course_title": "No course yet",
                    "progress_percent": 0,
                    "grade": "-"
                })
                continue

            for course in user_courses:
                progress = course.get("progress", {})
                is_programming = course.get("isProgramming", False)

                checklist_items = [
                    progress.get("notesCompleted", False),
                    progress.get("videosCompleted", False),
                    progress.get("assessmentCompleted", False),
                    progress.get("articlesCompleted", False)
                ]

                if is_programming:
                    checklist_items.append(progress.get("codingCompleted", False))

                completed_count = sum(1 for item in checklist_items if item)
                progress_percent = round((completed_count / len(checklist_items)) * 100)

                overall_score, grade = calculate_grade(progress, is_programming)

                dashboard_data.append({
                    "user_id": str(user["_id"]),
                    "name": user.get("name", ""),
                    "email": user.get("email", ""),
                    "course_title": course.get("title", ""),
                    "progress_percent": progress_percent,
                    "grade": grade
                })

        return jsonify({"dashboard": dashboard_data}), 200

    except Exception as e:
        print("ADMIN DASHBOARD ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)