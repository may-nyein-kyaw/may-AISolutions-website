from flask import Blueprint, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import mysql.connector
from flask import send_from_directory

# Create a Blueprint
industries_bp = Blueprint("industry", __name__)
CORS(industries_bp)

# Database connection configuration
db_config = {
    'user': 'root',
    'password': '12345678',
    'host': 'localhost',
    'database': 'aisolutionsdb',
}

UPLOAD_FOLDER = "industryuploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@industries_bp.route("/industries/<int:industry_id>", methods=["GET"])
def get_industry(industry_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT industries.*, users.name AS writer_name
            FROM industries
            JOIN users ON industries.user_id = users.id
            WHERE industries.id = %s
        """, (industry_id,))

        industry = cursor.fetchone()
        cursor.close()
        conn.close()

        if industry:
            if industry["image1"]:
                industry["image1"] = f"/industryuploads/{os.path.basename(industry['image1'])}"
            if industry["image2"]:
                industry["image2"] = f"/industryuploads/{os.path.basename(industry['image2'])}"
            return jsonify(industry), 200


        return jsonify({"error": "Industry not found"}), 404

    except Exception as e:
        print("Error fetching industry:", e)
        return jsonify({"error": str(e)}), 500


@industries_bp.route("/latest-industry-id", methods=["GET"])
def get_latest_industry_id():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT MAX(id) FROM industries")
        latest_id = cursor.fetchone()[0]  

        cursor.close()
        conn.close()

        if latest_id is None:
            latest_id = 1  
        else:
            latest_id += 1  

        return jsonify({"latest_industry_id": latest_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def create_industries_app():
    return industries_bp

# API to create a solution (User ID from frontend)
@industries_bp.route("/industries", methods=["POST"])
def create_industry():
    try:
        data = request.form
        images = request.files.getlist("images")
        user_id = data.get("user_id")  # Get user ID from frontend

        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        if len(images) != 2:
            return jsonify({"error": "Exactly 2 images required"}), 400

        # Save images and get their filenames
        image_paths = []
        for img in images:
            filename = secure_filename(img.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            img.save(filepath)
            image_paths.append(filepath)

        # Save solution to database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = """INSERT INTO industries (user_id, title, paragraph1, paragraph2, image1, image2)
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (user_id, data["title"], data["paragraph1"], data["paragraph2"],
                               image_paths[0], image_paths[1]))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Industry created successfully"}), 201

    except Exception as e:
        print(f"Error while creating solution: {e}") 
        return jsonify({"error": str(e)}), 500

@industries_bp.route("/industries", methods=["GET"])
def get_industries():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT industries.*, users.name AS writer_name
            FROM industries
            JOIN users ON industries.user_id = users.id
            ORDER BY industries.id DESC
        """)
        
        industries = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(industries), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@industries_bp.route("/industries/<int:industry_id>", methods=["DELETE"])
def delete_industry(industry_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM industries WHERE id = %s", (industry_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Industry deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@industries_bp.route("/industryuploads/<filename>")
def serve_image(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({"error": f"Failed to serve image: {str(e)}"}), 500

# API to upload an image separately
@industries_bp.route("/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename).replace("\\", "/")  # Convert \ to /
    file.save(filepath)

    return jsonify({"image_url": filepath}), 200

@industries_bp.route("/industries/<int:industry_id>", methods=["PUT"])
def update_industry(industry_id):
    try:
        data = request.form
        image1 = request.files.get("image1")  # Get image1 from the form data
        image2 = request.files.get("image2")  # Get image2 from the form data

        # Debugging: Output received data and images
        print("Received data:", data)
        print("Received image1:", image1.filename if image1 else None)

        # Ensure title and paragraphs are provided
        if not data.get("title"):
            return jsonify({"error": "Title is required"}), 400

        # Connect to DB
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Retrieve existing user_id to prevent updating it
        cursor.execute("SELECT user_id FROM industries WHERE id = %s", (industry_id,))
        existing_user = cursor.fetchone()

        # Debugging: Check if Solution exists
        if not existing_user:
            print(f"Industry with ID {industry_id} not found.")
            return jsonify({"error": "Industry not found"}), 404

        user_id = existing_user[0]  # Keep the original user_id

        # Prepare updated image paths if new images are uploaded
        image_paths = []

        # Process uploaded images (FileStorage objects)
        for img, i in zip([image1, image2 ], range(1, 3)):
            if img and isinstance(img, FileStorage):  # Check if it's a file object
                filename = secure_filename(img.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                img.save(filepath)
                image_paths.append(filepath)
                print(f"Image{i} saved: {filename} at {filepath}")
            else:
                # Handle case where no new image is uploaded for that specific slot
                cursor.execute(f"SELECT image{i} FROM industries WHERE id = %s", (industry_id,))
                existing_image = cursor.fetchone()[0]
                image_paths.append(existing_image)
                print(f"Using existing image{i}: {existing_image}")

        # Ensure exactly 3 images are provided (either URLs or uploaded images)
        if len(image_paths) != 2:
            print("Error: Exactly 2 images are required")
            return jsonify({"error": "Exactly 2 images are required"}), 400

        # Update the solution with new or existing images
        query = """UPDATE industries
                   SET title = %s, paragraph1 = %s, paragraph2 = %s, 
                       image1 = %s, image2 =%s
                   WHERE id = %s"""
        cursor.execute(query, (data["title"], data["paragraph1"], data["paragraph2"],
                               image_paths[0],image_paths[1] , industry_id))
        print(f"Solution {industry_id} updated with images.")

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Industry updated successfully"}), 200

    except Exception as e:
        # Debugging: Output the full error message
        print(f"Error updating Industry: {e}")
        return jsonify({"error": str(e)}), 500