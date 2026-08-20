from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection, init_database

app = Flask(__name__)
app.secret_key = "renewcast-dev-secret-key"
CORS(app, supports_credentials=True)

# Make sure the database exists when the server starts
init_database()


@app.route("/")
def home():
    return jsonify({
        "message": "RenewCast backend is running!"
    })


@app.route("/api/test")
def test():
    return jsonify({
        "status": "success",
        "message": "Backend connection is working!"
    })


@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "Name, email and password are required."
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "message": "Password must be at least 6 characters."
        }), 400

    password_hash = generate_password_hash(password)

    try:
        connection = get_connection()

        connection.execute(
            """
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (name, email, password_hash)
        )

        connection.commit()
        connection.close()

        return jsonify({
            "success": True,
            "message": "Account created successfully!"
        }), 201

    except Exception as error:
        if "UNIQUE constraint failed" in str(error):
            return jsonify({
                "success": False,
                "message": "An account with this email already exists."
            }), 409

        return jsonify({
            "success": False,
            "message": "Something went wrong while creating the account."
        }), 500


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    connection = get_connection()

    user = connection.execute(
        """
        SELECT id, name, email, password_hash
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    connection.close()
    if user is None or not check_password_hash(
        user["password_hash"], password
    ):
        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401

    session["user_id"] = user["id"]
    session["user_email"] = user["email"]

    return jsonify({
        "success": True,
        "message": "Login successful!",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    })
@app.route("/api/me", methods=["GET"])
def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Not logged in."
        }), 401

    connection = get_connection()

    user = connection.execute(
        """
        SELECT id, name, email
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    if user is None:
        session.clear()
        return jsonify({
            "success": False,
            "message": "User not found."
        }), 401

    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    })

if __name__ == "__main__":
    app.run(debug=True)