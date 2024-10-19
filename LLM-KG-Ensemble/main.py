import os

import pandas as pd
from dotenv import load_dotenv
from src.knowledge_graph.neo4j_connection import Neo4jConnection
from src.entity_extraction.entity_extraction import extract_entities
from src.data_ingestion.world_bank_ingestion import fetch_world_bank_documents
from src.data_ingestion.sam_gov_ingestion import fetch_sam_gov_opportunities

# Load environment variables from the .env file
load_dotenv()


# Define the main workflow function
def run_workflow():
    # Step 1: Check for World Bank and SAM.gov data, and fetch if missing

    # World Bank data file check
    world_bank_data_path = "data/processed/world_bank_documents.csv"
    if not os.path.exists(world_bank_data_path):
        print("World Bank data file missing, fetching data from World Bank API...")
        fetch_and_save_world_bank_data()
    else:
        print(f"World Bank data file {world_bank_data_path} found.")

    # SAM.gov data file check
    sam_gov_data_path = "data/processed/sam_gov_opportunities.csv"
    if not os.path.exists(sam_gov_data_path):
        print("SAM.gov data file missing, fetching data from SAM.gov API...")
        fetch_and_save_sam_gov_data()
    else:
        print(f"SAM.gov data file {sam_gov_data_path} found.")

    # Step 2: Set up Neo4j connection using environment variables
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    conn = Neo4jConnection(uri, user, password)

    # Step 3: Ingest documents into Neo4j and create relationships (World Bank example)
    print("Ingesting World Bank documents into Neo4j...")
    conn.ingest_documents_from_csv(world_bank_data_path)
    conn.create_country_nodes_from_documents(world_bank_data_path)
    conn.create_document_country_relationships_from_csv(world_bank_data_path)

    print("Ingesting SAM.gov data into Neo4j...")
    conn.ingest_documents_from_csv(sam_gov_data_path)
    conn.create_country_nodes_from_documents(sam_gov_data_path)
    conn.create_document_country_relationships_from_csv(sam_gov_data_path)

    # Step 4: Entity extraction from sample or actual text (expand as needed)
    print("Extracting entities from World Bank data...")
    extract_and_ingest_entities_from_data(conn, world_bank_data_path, "document_type")

    print("Extracting entities from SAM.gov data...")
    extract_and_ingest_entities_from_data(conn, sam_gov_data_path, "document_type")

    print("Ingesting SAM.gov organizations and awards into Neo4j...")
    ingest_additional_sam_gov_data(conn, sam_gov_data_path)

    # Step 6: Close the Neo4j connection
    conn.close()
    print("Workflow completed successfully!")


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
    print("Fetching data from SAM.gov API...")

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
                conn.create_entity_node(entity["word"], entity["entity"])
        else:
            print(f"Skipping empty or missing text in row {index}")


# Execute the workflow
if __name__ == "__main__":
    run_workflow()
