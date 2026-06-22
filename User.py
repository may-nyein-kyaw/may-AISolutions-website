from flask import Blueprint, request, jsonify
from flask_cors import CORS
import mysql.connector
from flask_jwt_extended import JWTManager, create_access_token

# Create a Blueprint for user routes
user_bp = Blueprint('user', __name__)

# CORS setup for user routes
CORS(user_bp)

# Database connection configuration
config = {
    'user': 'root',
    'password': '12345678',
    'host': 'localhost',
    'database': 'aisolutionsdb', 
    'raise_on_warnings': True
}

# Helper function to connect to the database
def get_db_connection():
    try:
        connection = mysql.connector.connect(**config)
        print("Database connection successful!")
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to the database: {err}")
        return None

# User Login (No password hashing)
@user_bp.route("/user/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Missing credentials"}), 400

    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Failed to connect to the database"}), 500

    cursor = connection.cursor(dictionary=True)

    # Fetch user from database
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if user:
        # Generate JWT token
        access_token = create_access_token(identity=username)
        
        # Print the generated token for debugging
        print(f"Generated Token: {access_token}")
        print(f"id: {user['id']}")
        
        return jsonify({"message": "Login successful",
                         "token": access_token,
                         "user_id": user["id"]}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401

# Route to fetch all users (Returns passwords in plaintext)
@user_bp.route('/users', methods=['GET'])
def get_users():
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Failed to connect to the database"}), 500

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(users), 200

# Get user by ID
@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return jsonify(user), 200
    else:
        return jsonify({"error": "User not found"}), 404

# Route to add a new user (Stores plaintext passwords)
@user_bp.route('/users', methods=['POST'])
def add_user():
    data = request.json
    name = data.get('name')
    username = data.get('username')
    password = data.get('password')
    level = data.get('level')

    if not all([name, username, password, level]):
        return jsonify({"error": "Missing required fields"}), 400

    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Failed to connect to the database"}), 500

    cursor = connection.cursor()

    query = "INSERT INTO users (name, username, password, level) VALUES (%s, %s, %s, %s)"
    values = (name, username, password, level)
    cursor.execute(query, values)
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "User added successfully"}), 201

# Route to update a user
@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.json
    name = data.get('name')
    username = data.get('username')
    password = data.get('password')
    level = data.get('level')

    if not any([name, username, password, level]):
        return jsonify({"error": "At least one field is required to update"}), 400

    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Failed to connect to the database"}), 500

    cursor = connection.cursor()

    update_fields = []
    values = []
    if name:
        update_fields.append("name = %s")
        values.append(name)
    if username:
        update_fields.append("username = %s")
        values.append(username)
    if password:  # Store password directly without hashing
        update_fields.append("password = %s")
        values.append(password)
    if level:
        update_fields.append("level = %s")
        values.append(level)

    values.append(user_id)
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
    cursor.execute(query, values)
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "User updated successfully"}), 200

# Route to delete a user
@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Failed to connect to the database"}), 500

    cursor = connection.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "User deleted successfully"}), 200

# Function to create and return the **Blueprint only**
def create_user_app():
    return user_bp  # ✅ Only return the blueprint
