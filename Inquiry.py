from flask import Blueprint, request, jsonify
from flask_cors import CORS
import mysql.connector
from flask_mail import Message

def create_inquiries_app(mail):
    inquiries_bp = Blueprint('inquiries', __name__)
    CORS(inquiries_bp)

    # Database connection configuration
    config = {
        'user': 'root',
        'password': '12345678',
        'host': 'localhost',
        'database': 'aisolutionsdb',
        'raise_on_warnings': True
    }

    def get_db_connection():
        try:
            connection = mysql.connector.connect(**config)
            return connection
        except mysql.connector.Error as err:
            print(f"Error connecting to the database: {err}")
            return None

    def send_confirmation_email(user_email, user_name):
        """Sends an automated confirmation email to the user."""
        msg = Message(
            subject="Your Inquiry Has Been Received",
            sender="thureinrichard3@gmail.com",  # Use your Gmail
            recipients=[user_email],
            body=f"""
            Hi {user_name},

            Thank you for reaching out! We have received your inquiry and will get back to you soon.

            If you don’t receive a response within an hour, please submit your inquiry again.

            Best regards,  
            The AI Solutions Team
            """
        )

        try:
            mail.send(msg)
            print(f"Confirmation email sent to {user_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    # Create a new inquiry
    @inquiries_bp.route('/inquiries', methods=['POST'])
    def create_inquiry():
        data = request.json
        required_fields = ['name', 'email', 'phone', 'company', 'country', 'jobTitle', 'jobDetail', 'solution','state']
        
        if not all(data.get(field) for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        full_name = data['name']
        email = data['email']
        phone = data['phone']
        company = data['company']
        country = data['country']
        job_title = data['jobTitle']
        job_detail = data['jobDetail']
        solution = data['solution']
        state = data['state']

        connection = get_db_connection()
        if connection is None:
            return jsonify({"error": "Failed to connect to the database"}), 500

        cursor = connection.cursor()
        query = """
            INSERT INTO inquiries (full_name, email, phone, company, country, job_title, job_detail, solution, state)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (full_name, email, phone, company, country, job_title, job_detail, solution, state)
        cursor.execute(query, values)
        connection.commit()

        # Send confirmation email
        send_confirmation_email(email, full_name)

        cursor.close()
        connection.close()
        return jsonify({"message": "Inquiry created successfully. A confirmation email has been sent."}), 201

    # Get all inquiries with optional filters
    @inquiries_bp.route('/inquiries', methods=['GET'])
    def get_inquiries():
        country = request.args.get('country')
        state = request.args.get('state')
        name = request.args.get('name')
        date = request.args.get('date')
        solution = request.args.get('solution')

        connection = get_db_connection()
        if connection is None:
            return jsonify({"error": "Failed to connect to the database"}), 500

        cursor = connection.cursor(dictionary=True)
        
        # Base query for fetching inquiries
        query = "SELECT * FROM inquiries WHERE 1=1"
        params = []

        # Apply filters if provided
        if country:
            query += " AND country = %s"
            params.append(country)
        if state:
            query += " AND state = %s"
            params.append(state)
        if name:
            query += " AND full_name LIKE %s"
            params.append(f"%{name}%")
        if date:
            query += " AND DATE(created_at) = %s"  # Use created_at instead of date
            params.append(date)
        if solution:
            query += " AND solution = %s"
            params.append(solution)

        # Execute the query with parameters
        cursor.execute(query, params)
        inquiries = cursor.fetchall()

        cursor.close()
        connection.close()
        return jsonify(inquiries), 200
    
    # Fetch unique countries for the dropdown
    @inquiries_bp.route('/inquiries/countries', methods=['GET'])
    def get_countries():
        connection = get_db_connection()
        if connection is None:
            return jsonify({"error": "Failed to connect to the database"}), 500

        cursor = connection.cursor()
        query = "SELECT DISTINCT country FROM inquiries ORDER BY country"
        cursor.execute(query)
        countries = cursor.fetchall()

        cursor.close()
        connection.close()

        # Accessing the country name from the tuple
        return jsonify([country[0] for country in countries]), 200



    # Update an inquiry
    @inquiries_bp.route('/inquiries/<int:inquiry_id>', methods=['PUT'])
    def update_inquiry(inquiry_id):
        data = request.json
        update_fields = []
        values = []

        for key, value in data.items():
            if value:
                update_fields.append(f"{key} = %s")
                values.append(value)

        if not update_fields:
            return jsonify({"error": "No fields provided for update"}), 400

        values.append(inquiry_id)
        connection = get_db_connection()
        if connection is None:
            return jsonify({"error": "Failed to connect to the database"}), 500

        cursor = connection.cursor()
        query = f"UPDATE inquiries SET {', '.join(update_fields)} WHERE qid = %s"
        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()
        return jsonify({"message": "Inquiry updated successfully"}), 200

    # Delete an inquiry (Restricted to admin)
    @inquiries_bp.route('/inquiries/<int:inquiry_id>', methods=['DELETE'])
    def delete_inquiry(inquiry_id):
        connection = get_db_connection()
        if connection is None:
            return jsonify({"error": "Failed to connect to the database"}), 500

        cursor = connection.cursor()
        cursor.execute("DELETE FROM inquiries WHERE qid = %s", (inquiry_id,))
        connection.commit()

        cursor.close()
        connection.close()
        return jsonify({"message": "Inquiry deleted successfully"}), 200

    return inquiries_bp  # Return the Blueprint object
