from flask import Blueprint, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import mysql.connector
from flask import send_from_directory

# Create a Blueprint
gallery_bp = Blueprint("gallery", __name__)
CORS(gallery_bp)

# Function to create and return the blogs blueprint
def create_gallery_app():
    return gallery_bp

# Database connection configuration
db_config = {
    'user': 'root',
    'password': '12345678',
    'host': 'localhost',
    'database': 'aisolutionsDB',
}

# Update folder name to 'galleryUploads'
UPLOAD_FOLDER = "galleryUploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# API to get all gallery items (Anyone can view)
@gallery_bp.route("/gallery", methods=["GET"])
def get_gallery():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch gallery items in descending order (latest first)
        cursor.execute("""
            SELECT gallery.*, users.name AS uploader_name
            FROM gallery
            JOIN users ON gallery.user_id = users.id
            ORDER BY gallery.id DESC
        """)
        
        gallery_items = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(gallery_items), 200

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


# API to get the latest gallery ID
@gallery_bp.route("/latest-gallery-id", methods=["GET"])
def get_latest_gallery_id():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT MAX(id) FROM gallery")
        latest_id = cursor.fetchone()[0]  # Get the latest ID

        cursor.close()
        conn.close()

        if latest_id is None:
            latest_id = 1  # Default to 1 if no galleries exist
        else:
            latest_id += 1  # Increment for the new gallery

        return jsonify({"latest_gallery_id": latest_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gallery_bp.route("/gallery/<int:item_id>", methods=["GET"])
def get_gallery_item(item_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT gallery.*, users.name AS uploader_name
            FROM gallery
            JOIN users ON gallery.user_id = users.id
            WHERE gallery.id = %s
        """, (item_id,))

        gallery_item = cursor.fetchone()
        cursor.close()
        conn.close()

        if gallery_item:
            # Make sure the image path is just the filename
            if gallery_item["image"]:
                gallery_item["image"] = f"/galleryUploads/{os.path.basename(gallery_item['image'])}"
            return jsonify(gallery_item), 200

        return jsonify({"error": "Gallery item not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API to create a gallery item (User ID from frontend)
@gallery_bp.route("/gallery", methods=["POST"])
def create_gallery_item():
    try:
        data = request.form
        images = request.files.getlist("images")
        user_id = data.get("user_id")  # Get user ID from frontend

        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        if len(images) != 1:
            return jsonify({"error": "Exactly 1 image required"}), 400

        # Save images and get their filenames
        image_paths = []
        for img in images:
            filename = secure_filename(img.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            img.save(filepath)
            image_paths.append(filepath)

        # Save gallery item to database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = """INSERT INTO gallery (user_id, title, description, image)
                   VALUES (%s, %s, %s, %s)"""
        cursor.execute(query, (user_id, data["title"], data["description"], image_paths[0]))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Gallery item created successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API to delete a gallery item (No extra checks, frontend handles admin access)
@gallery_bp.route("/gallery/<int:item_id>", methods=["DELETE"])
def delete_gallery_item(item_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM gallery WHERE id = %s", (item_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Gallery item deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@gallery_bp.route("/gallery/<int:item_id>", methods=["PUT"])
def update_gallery(item_id):
    try:
        data = request.form
        image = request.files.get("image")  # Get image from the form data

        # Debugging: Output received data and image
        print("Received data:", data)
        print("Received image:", image.filename if image else None)

        # Ensure title is provided
        if not data.get("title"):
            return jsonify({"error": "Title is required"}), 400

        # Connect to DB
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Retrieve existing item_id to prevent updating it
        cursor.execute("SELECT user_id FROM gallery WHERE id = %s", (item_id,))
        existing_user = cursor.fetchone()

        # Debugging: Check if gallery item exists
        if not existing_user:
            print(f"Gallery item with ID {item_id} not found.")
            return jsonify({"error": "Gallery item not found"}), 404

        user_id = existing_user[0]  # Keep the original user_id

        # Prepare updated image path if new image is uploaded
        image_path = None

        # Process uploaded image (FileStorage object)
        if image and isinstance(image, FileStorage):  # Check if it's a file object
            filename = secure_filename(image.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image.save(image_path)
            print(f"Image saved: {filename} at {image_path}")
        else:
            # Handle case where no new image is uploaded; retain existing image
            cursor.execute("SELECT image FROM gallery WHERE id = %s", (item_id,))
            image_path = cursor.fetchone()[0]
            print(f"Using existing image: {image_path}")

        # Ensure exactly 1 image is provided (either uploaded or existing)
        if not image_path:
            print("Error: Image is required")
            return jsonify({"error": "Image is required"}), 400

        # Update the gallery item with the new or existing image and description
        query = """UPDATE gallery
                   SET title = %s, description = %s, image = %s
                   WHERE id = %s"""
        cursor.execute(query, (data["title"], data["description"], image_path, item_id))
        print(f"Gallery item {item_id} updated with image.")

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Gallery item updated successfully"}), 200

    except Exception as e:
        # Debugging: Output the full error message
        print(f"Error updating gallery item: {e}")
        return jsonify({"error": str(e)}), 500


# Serve uploaded images from the galleryUploads folder
@gallery_bp.route("/galleryUploads/<filename>")
def serve_image(filename):
    try:
        # Serve image from the galleryUploads folder
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({"error": f"Failed to serve image: {str(e)}"}), 500


# API to upload an image separately for the gallery
@gallery_bp.route("/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename).replace("\\", "/")  # Convert \ to /
    file.save(filepath)

    return jsonify({"image_url": filepath}), 200
