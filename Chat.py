from flask import Blueprint, request, jsonify
import openai
from flask_cors import CORS

#Initialize the chat blueprint
def create_chat_app():
    chat_bp = Blueprint('chat', __name__)
    CORS(chat_bp)

    # Directly using your OpenAI API key
    openai.api_key = "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"  # Replace with your API key
    # Replace with your API key

    @chat_bp.route('/chat', methods=['POST'])
    def chat():
        user_message = request.json.get('message')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        try:
            # Use the updated Chat API method
            client = openai.OpenAI(api_key=openai.api_key)

            response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": """You are an AI assistant for AI-Solutions, a fictitious start-up company. 
        You only answer questions related to AI-Solutions, its AI-powered virtual assistant, software solutions, and digital employee experience. 
        If a question is unrelated, politely refuse to answer.

        Here are frequently asked questions (FAQs) and their answers:

        What makes your AI solutions stand out in the industry?
           ➡️ Our solutions are built on advanced machine learning models and customized strategies designed specifically for your business needs.

        In which countries can I find your company?
           ➡️ We proudly serve clients across North America, Europe, Asia, and are expanding globally with regional offices and remote services.

        Which industries does your company provide its services?
           ➡️ We care to education, healthcare, retail, manufacturing, Telecomunication, and more—empowering industries through smart automation.

        What kind of support does AI-Solutions provide?
           ➡️We offer 24/7 technical support, regular updates, and dedicated AI specialists to ensure smooth implementation and maintenance

         What is your service expertise?
           ➡️ Our expertise spans natural language processing, predictive analytics, computer vision, and AI-driven business intelligence.
        """},
        {"role": "user", "content": user_message}
    ],
    max_tokens=300
)


            ai_response = response.choices[0].message.content

            return jsonify({'response': ai_response})

        except Exception as e:
            print(e)
            return jsonify({'error': str(e)}), 500

    return chat_bp