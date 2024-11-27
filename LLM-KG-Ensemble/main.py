import os

import pandas as pd
from dotenv import load_dotenv
from src.knowledge_graph.neo4j_connection import Neo4jConnection
from src.entity_extraction.entity_extraction import extract_entities
from src.data_ingestion.world_bank_ingestion import fetch_world_bank_documents
from src.data_ingestion.open_tenders_ingestion import fetch_open_tenders
from src.data_ingestion.ocds_ingestion import fetch_ocds_data
from src.data_ingestion.sam_gov_ingestion import fetch_sam_gov_opportunities
from src.query_interface.query_interface import Neo4jQueryInterface
from src.chatbot.chatbot import chatbot_app

# Load environment variables from the .env file
load_dotenv()


# Define the main workflow function
# Function to run the workflow
def run_workflow():
    # Step 1: Check for the existence of World Bank, SAM.gov, Open Tenders, and OCDS datasets
    world_bank_data_path = "data/processed/world_bank_documents.csv"
    sam_gov_data_path = "data/processed/sam_gov_opportunities.csv"
    open_tenders_data_path = "data/processed/open_tenders.csv"
    ocds_data_path = "data/processed/ocds_data.csv"

    datasets = {
        "world_bank": world_bank_data_path,
        "sam_gov": sam_gov_data_path,
        "open_tenders": open_tenders_data_path,
        "ocds": ocds_data_path,
    }

    for dataset_name, file_path in datasets.items():
        if not os.path.exists(file_path):
            print(f"{dataset_name} data file missing, fetching data...")
            if dataset_name == "world_bank":
                fetch_and_save_world_bank_data()
            elif dataset_name == "sam_gov":
                fetch_and_save_sam_gov_data()
            elif dataset_name == "open_tenders":
                fetch_open_tenders()
            elif dataset_name == "ocds":
                fetch_ocds_data()
        else:
            print(f"{dataset_name} data file {file_path} found.")

    # Step 2: Set up Neo4j connection using environment variables
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    conn = Neo4jConnection(uri, user, password)

    # Step 3: Ingest documents into Neo4j and create relationships
    print("Ingesting documents and creating entities in Neo4j...")
    extract_and_create_entity_relationships(conn, world_bank_data_path, "world_bank")
    extract_and_create_entity_relationships(conn, sam_gov_data_path, "sam_gov")
    extract_and_create_entity_relationships(
        conn, open_tenders_data_path, "open_tenders"
    )
    extract_and_create_entity_relationships(conn, ocds_data_path, "ocds")

    # Create relationships
    print("Creating relationships between entities from the datasets...")
    create_entity_relationships(conn, world_bank_data_path)
    create_entity_relationships(conn, sam_gov_data_path)
    create_entity_relationships(conn, open_tenders_data_path)
    create_entity_relationships(conn, ocds_data_path)

    # Step 4: Query Neo4j using the query interface
    query_neo4j(uri, user, password)

    # Step 5: Close the Neo4j connection
    conn.close()
    print("Workflow completed successfully!")


# Function to run the chatbot using Flask
def run_chatbot():
    print("Starting chatbot server...")
    chatbot_app.run(debug=True, port=5001)


# Function to query Neo4j after ingestion
def query_neo4j(uri, user, password):
    query_interface = Neo4jQueryInterface(uri, user, password)

    print("What query would you like to perform?")
    print("1. Get documents related to a specific entity")
    print("2. Get entities related to a specific document type")
    print("3. Get documents related to multiple entities")
    print("4. Get documents within a time range")
    print("5. Get entity frequency analysis")

    choice = input("Enter your choice (1, 2, 3, 4, or 5): ")

    if choice == "1":
        entity_name = input("Enter the entity name (e.g., 'Pakistan'): ")
        documents = query_interface.query_documents_by_entity(entity_name)
        print(f"Documents related to {entity_name}:")
        for doc in documents:
            print(doc)

    elif choice == "2":
        document_type = input("Enter the document type (e.g., 'Award Notice'): ")
        entities = query_interface.query_entities_by_document(document_type)
        print(f"Entities related to {document_type}:")
        for entity in entities:
            print(entity)

    elif choice == "3":
        entity_names = input(
            "Enter the entity names separated by commas (e.g., 'Pakistan, Energy'): "
        ).split(",")
        documents = query_interface.query_documents_by_multiple_entities(entity_names)
        print(f"Documents related to {', '.join(entity_names)}:")
        for doc in documents:
            print(doc)

    elif choice == "4":
        start_date = input("Enter the start date (YYYY-MM-DD): ")
        end_date = input("Enter the end date (YYYY-MM-DD): ")
        document_type = input(
            "Enter the document type (optional, press Enter to skip): "
        )
        documents = query_interface.query_documents_by_time_range(
            start_date, end_date, document_type
        )
        print(f"Documents between {start_date} and {end_date}:")
        for doc in documents:
            print(doc)

    elif choice == "5":
        entities = query_interface.query_entity_frequency()
        print(f"Entity frequency analysis:")
        for entity in entities:
            print(f"{entity['entity']}: {entity['mention_count']} mentions")

    query_interface.close()


# Function to extract and create relationships between entities
def extract_and_create_entity_relationships(conn, file_path, dataset_type):
    df = pd.read_csv(file_path)
    for index, row in df.iterrows():
        try:
            document_type = row["document_type"]
            country = row["country"]
            organization_name = row.get("organization_name", None)
            awardee_name = row.get("awardee_name", None)

            if pd.notna(document_type) and pd.notna(country):
                conn.create_document_node(row["document_date"], document_type, country)
                conn.create_country_node(country)

            if (
                dataset_type == "sam_gov"
                and pd.notna(organization_name)
                and pd.notna(awardee_name)
            ):
                conn.create_organization_node(organization_name)
                conn.create_entity_node(awardee_name, "Awardee")
                conn.create_document_entity_relationship(document_type, awardee_name)

        except KeyError as e:
            print(f"Missing column in row {index}: {e}")
            continue

    print(f"Entities and relationships created for {dataset_type} dataset.")


# Function to create relationships between entities
def create_entity_relationships(conn, file_path):
    df = pd.read_csv(file_path)
    for index, row in df.iterrows():
        try:
            document_type = row["document_type"]
            country = row["country"]
            organization_name = row.get("organization_name", None)

            if pd.notna(document_type) and pd.notna(country):
                conn.create_document_country_relationship(document_type, country)
            if pd.notna(organization_name):
                conn.create_document_entity_relationship(
                    document_type, organization_name
                )

        except KeyError as e:
            print(f"Missing column in row {index}: {e}")
            continue

    print(f"Entity relationships created for {file_path}")


# Fetch World Bank data and save to processed directory
def fetch_and_save_world_bank_data():
    df = fetch_world_bank_documents()
    if df is not None:
        os.makedirs("data/processed", exist_ok=True)
        df.to_csv("data/processed/world_bank_documents.csv", index=False)
        print("World Bank data fetched and saved.")
    else:
        print("Failed to fetch World Bank data.")


# Fetch SAM.gov data and save to processed directory
def fetch_and_save_sam_gov_data():
    print("SAM.gov data file missing, fetching data from SAM.gov API...")

    # Define the date range for fetching the SAM.gov data
    posted_from = "01/01/2023"
    posted_to = "12/31/2023"

    # Fetch the SAM.gov data
    df = fetch_sam_gov_opportunities(posted_from, posted_to)

    if df is not None and not df.empty:
        os.makedirs("data/processed", exist_ok=True)
        df.to_csv("data/processed/sam_gov_opportunities.csv", index=False)
        print("SAM.gov data saved to data/processed/sam_gov_opportunities.csv")
    else:
        print("No data fetched from SAM.gov.")


# Ingest additional SAM.gov data (e.g., organizations and awards) into Neo4j
def ingest_additional_sam_gov_data(conn, file_path):
    df = pd.read_csv(file_path)
    if df is not None and not df.empty:
        print("Ingesting additional SAM.gov data into Neo4j...")
        for index, row in df.iterrows():
            if pd.notna(row["organization_name"]):
                conn.create_organization_node(row["organization_name"])
            if pd.notna(row["awardee_name"]):
                conn.create_award_node(
                    awardee=row["awardee_name"],
                    amount=row["award_amount"],
                    city=row["awardee_city"],
                    state=row["awardee_state"],
                    zip_code=row["awardee_zip"],
                    country=row["awardee_country"],
                )
        print("Additional SAM.gov data ingested successfully.")
    else:
        print("No additional SAM.gov data to ingest.")


# Entity extraction and ingestion function
def extract_and_ingest_entities_from_data(conn, file_path, column_name):
    df = pd.read_csv(file_path)
    for index, row in df.iterrows():
        text = row.get(column_name, "")
        if pd.notna(text) and text.strip():
            extracted_entities = extract_entities(text)
            for entity in extracted_entities:
                # Create the entity node
                conn.create_entity_node(entity["word"], entity["entity"])

                # Create the relationship between document and entity (MENTIONED_IN)
                conn.create_document_entity_relationship(
                    document_type=row[column_name],
                    entity_name=entity["word"],
                )
        else:
            print(f"Skipping empty or missing text in row {index}")


# Main function to prompt user to choose between workflow or chatbot
if __name__ == "__main__":
    print("Welcome! What would you like to do?")
    print("1. Run data ingestion workflow")
    print("2. Start the chatbot")

    choice = input("Enter your choice (1 or 2): ")

    if choice == "1":
        run_workflow()
    elif choice == "2":
        run_chatbot()
    else:
        print("Invalid choice. Please choose 1 or 2.")