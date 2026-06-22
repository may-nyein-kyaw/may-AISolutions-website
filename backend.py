from flask import Flask
from Blog import create_blogs_app
from Solution import create_solutions_app
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from User import create_user_app
from Inquiry import create_inquiries_app  # Corrected import
from Industry import create_industries_app
from Gallery import create_gallery_app
from Chat import create_chat_app

# Initialize Flask app
def create_main_app():
    app = Flask(__name__)

    CORS(app)

    # Flask-Mail Configuration
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USERNAME"] = "nant.mnyeink@gmail.com"  # Replace with your email
    app.config["MAIL_PASSWORD"] = "newn ntzu uzwk xjhn"  # Use correct App Password
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USE_SSL"] = False

     # JWT Configuration
    app.config["JWT_SECRET_KEY"] = "ilovemaynyeinkyaw" 

    # Initialize Mail
    mail = Mail(app)
    jwt = JWTManager(app) 

    # Register blueprints
    user_app = create_user_app()
    inquiries_app = create_inquiries_app(mail)  # Pass mail instance

    app.register_blueprint(user_app)
    app.register_blueprint(inquiries_app)
    app.register_blueprint(create_chat_app()) 
    app.register_blueprint(create_industries_app())
    app.register_blueprint(create_blogs_app())
    app.register_blueprint(create_solutions_app())
    app.register_blueprint(create_gallery_app())

    return app

if __name__ == "__main__":
    app = create_main_app()
    app.run(debug=True)
