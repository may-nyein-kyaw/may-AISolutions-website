from flask import Blueprint, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import mysql.connector
from flask import send_from_directory

# Create a Blueprint
solutions_bp = Blueprint("solution", __name__)
CORS(solutions_bp)

# Database connection configuration
db_config = {
    'user': 'root',
    'password': '12345678',
    'host': 'localhost',
    'database': 'aisolutionsdb',
}

UPLOAD_FOLDER = "solutionuploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@solutions_bp.route("/solutions/<int:solution_id>", methods=["GET"])
def get_solution(solution_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT solutions.*, users.name AS writer_name
            FROM solutions
            JOIN users ON solutions.user_id = users.id
            WHERE solutions.id = %s
        """, (solution_id,))

        solution = cursor.fetchone()
        cursor.close()
        conn.close()

        if solution:
            # Make sure the image path is just the filename
            if solution["image1"]:
                solution["image1"] = f"/solutionuploads/{os.path.basename(solution['image1'])}"
            if solution["image2"]:
                solution["image2"] = f"/solutionuploads/{os.path.basename(solution['image2'])}"
            return jsonify(solution), 200

        return jsonify({"error": "Solution not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500




# API to get the latest solution ID
@solutions_bp.route("/latest-solution-id", methods=["GET"])
def get_latest_solution_id():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT MAX(id) FROM solutions")
        latest_id = cursor.fetchone()[0]  # Get the latest ID

        cursor.close()
        conn.close()

        if latest_id is None:
            latest_id = 1  # Default to 1 if no solutions exist
        else:
            latest_id += 1  # Increment for the new solution

        return jsonify({"latest_solution_id": latest_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Function to create and return the solutions blueprint
def create_solutions_app():
    return solutions_bp

# API to create a solution (User ID from frontend)
@solutions_bp.route("/solutions", methods=["POST"])
def create_solutions():
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
        query = """INSERT INTO solutions (user_id, title, paragraph1, paragraph2, image1, image2)
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (user_id, data["title"], data["paragraph1"], data["paragraph2"],
                               image_paths[0], image_paths[1]))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Solution created successfully"}), 201

    except Exception as e:
        print(f"Error while creating solution: {e}") 
        return jsonify({"error": str(e)}), 500

# API to get all solutions (Anyone can view)
@solutions_bp.route("/solutions", methods=["GET"])
def get_solutions():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch solutions in descending order (latest first)
        cursor.execute("""
            SELECT solutions.*, users.name AS writer_name
            FROM solutions
            JOIN users ON solutions.user_id = users.id
            ORDER BY solutions.id DESC
        """)
        
        solutions = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(solutions), 200

    except Exception as e:

        return jsonify({"error": str(e)}), 500


# API to delete a solution (No extra checks, frontend handles admin access)
@solutions_bp.route("/solutions/<int:solution_id>", methods=["DELETE"])
def delete_solution(solution_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM solutions WHERE id = %s", (solution_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Solution deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve uploaded images
@solutions_bp.route("/solutionuploads/<filename>")
def serve_image(filename):
    try:
        # Serve image from the uploads folder
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({"error": f"Failed to serve image: {str(e)}"}), 500


# API to upload an image separately
@solutions_bp.route("/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename).replace("\\", "/")  # Convert \ to /
    file.save(filepath)

    return jsonify({"image_url": filepath}), 200

 # Import this at the top of your file

@solutions_bp.route("/solutions/<int:solution_id>", methods=["PUT"])
def update_solution(solution_id):
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
        cursor.execute("SELECT user_id FROM solutions WHERE id = %s", (solution_id,))
        existing_user = cursor.fetchone()

        # Debugging: Check if Solution exists
        if not existing_user:
            print(f"Solution with ID {solution_id} not found.")
            return jsonify({"error": "Solution not found"}), 404

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
                cursor.execute(f"SELECT image{i} FROM solutions WHERE id = %s", (solution_id,))
                existing_image = cursor.fetchone()[0]
                image_paths.append(existing_image)
                print(f"Using existing image{i}: {existing_image}")

        # Ensure exactly 3 images are provided (either URLs or uploaded images)
        if len(image_paths) != 2:
            print("Error: Exactly 2 images are required")
            return jsonify({"error": "Exactly 2 images are required"}), 400

        # Update the solution with new or existing images
        query = """UPDATE solutions
                   SET title = %s, paragraph1 = %s, paragraph2 = %s, 
                       image1 = %s, image2 =%s
                   WHERE id = %s"""
        cursor.execute(query, (data["title"], data["paragraph1"], data["paragraph2"],
                               image_paths[0],image_paths[1] , solution_id))
        print(f"Solution {solution_id} updated with images.")

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Solution updated successfully"}), 200

    except Exception as e:
        # Debugging: Output the full error message
        print(f"Error updating solution: {e}")
        return jsonify({"error": str(e)}), 500