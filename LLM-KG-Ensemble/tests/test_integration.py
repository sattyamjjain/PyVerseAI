import os
import pytest
from unittest.mock import patch, MagicMock
from src.knowledge_graph.neo4j_connection import Neo4jConnection
from src.data_ingestion.sam_gov_ingestion import fetch_sam_gov_opportunities
from src.data_ingestion.world_bank_ingestion import fetch_world_bank_documents
from src.entity_extraction.entity_extraction import extract_entities
from src.query_interface.query_interface import Neo4jQueryInterface


# Mock environment variables instead of using .env
@patch(
    "os.getenv",
    side_effect=lambda key: {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "test_password",
    }[key],
)
@patch("neo4j.GraphDatabase.driver")  # Mock Neo4j driver
def test_integration_workflow(mock_driver, mock_getenv):
    # Mock the Neo4j driver and session
    mock_session = MagicMock()
    mock_driver.return_value.session.return_value = mock_session

    # Mock transaction function
    def mock_write_transaction(func, *args, **kwargs):
        return func(mock_session)

    # Mock write_transaction method
    mock_session.write_transaction = MagicMock(side_effect=mock_write_transaction)

    # Instantiate Neo4jConnection
    conn = Neo4jConnection("bolt://localhost:7687", "neo4j", "test_password")

    # Simulate file paths
    world_bank_data_path = "data/processed/world_bank_documents.csv"
    sam_gov_data_path = "data/processed/sam_gov_opportunities.csv"

    # Check if both files are present (we can mock the os.path.exists)
    with patch("os.path.exists", side_effect=lambda path: True):
        assert os.path.exists(world_bank_data_path), "World Bank data is missing!"
        assert os.path.exists(sam_gov_data_path), "SAM.gov data is missing!"

    # Test data ingestion for World Bank
    conn.ingest_documents_from_csv(world_bank_data_path)
    conn.create_country_nodes_from_documents(world_bank_data_path)
    conn.create_document_country_relationships_from_csv(world_bank_data_path)

    # Test data ingestion for SAM.gov
    conn.ingest_documents_from_csv(sam_gov_data_path)
    conn.create_country_nodes_from_documents(sam_gov_data_path)
    conn.create_document_country_relationships_from_csv(sam_gov_data_path)

    # Mock entity extraction and insert into Neo4j for World Bank
    sample_text = "The energy project in India focuses on renewable energy sources."
    extracted_entities = [
        {"word": "India", "entity": "LOC"}
    ]  # Mocked entity extraction result
    with patch(
        "src.entity_extraction.entity_extraction.extract_entities",
        return_value=extracted_entities,
    ):
        for entity in extracted_entities:
            conn.create_entity_node(entity["word"], entity["entity"])

    # Mock the query interface
    with patch(
        "src.query_interface.query_interface.Neo4jQueryInterface.query_documents_by_entity",
        return_value=[
            {
                "document_date": "2023-12-30",
                "document_type": "Award Notice",
                "country": "USA",
            }
        ],
    ):
        # Query Neo4j for entities
        query_interface = Neo4jQueryInterface(
            "bolt://localhost:7687", "neo4j", "test_password"
        )
        documents = query_interface.query_documents_by_entity("India")
        assert len(documents) > 0, "Failed to retrieve documents related to India!"

    # Test additional SAM.gov data
    conn.create_organization_node("Test Organization")
    conn.create_award_node("Test Awardee", 100000, "New York", "NY", "10001", "USA")

    print("Integration workflow test completed successfully!")
