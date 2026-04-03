import os
from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI not found in .env file")

client = MongoClient(MONGO_URI)
db = client["ai_course_builder"]
users_collection = db["users"]

def create_admin():
    name = "Admin"
    email = "admin@gmail.com"
    password = "admin123"
    hashed_password = generate_password_hash(password)
    role = "admin"

    existing_user = users_collection.find_one({"email": email})

    if existing_user:
        users_collection.update_one(
            {"email": email},
            {"$set": {"role": "admin"}}
        )
        print("Admin already exists. Role updated to admin.")
    else:
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role
        })
        print("Admin created successfully.")

if __name__ == "__main__":
    create_admin()