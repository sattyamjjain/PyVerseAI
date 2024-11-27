from flask import Flask, request, jsonify
from src.query_interface.query_interface import Neo4jQueryInterface
import os

# Initialize the Flask app
chatbot_app = Flask(__name__)

# Load Neo4j credentials from environment variables
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")


@chatbot_app.route("/chat", methods=["POST"])
def chatbot():
    user_input = request.json.get("message")
    response = handle_chatbot_query(user_input)
    return jsonify({"response": response})


def handle_chatbot_query(user_input):
    neo4j_interface = Neo4jQueryInterface(uri, user, password)
    if "documents related to" in user_input.lower():
        entity_name = user_input.split("related to")[-1].strip()
        documents = neo4j_interface.query_documents_by_entity(entity_name)
        if documents:
            return f"Documents related to {entity_name}: {documents}"
        else:
            return f"No documents found for {entity_name}."

    elif "entities related to" in user_input.lower():
        document_type = user_input.split("related to")[-1].strip()
        entities = neo4j_interface.query_entities_by_document(document_type)
        if entities:
            return f"Entities related to {document_type}: {entities}"
        else:
            return f"No entities found for {document_type}."

    # You can add more conversational patterns here
    else:
        return "I didn't understand your query. Please try again."
