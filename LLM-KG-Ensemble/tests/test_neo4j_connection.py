from unittest.mock import patch, MagicMock
from src.knowledge_graph.neo4j_connection import Neo4jConnection


@patch(
    "os.getenv",
    side_effect=lambda key: {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "test_password",
    }[key],
)  # Mock the environment variables
@patch("neo4j.GraphDatabase.driver")  # Mock Neo4j driver
def test_neo4j_connection(mock_driver, mock_getenv):
    # Mock the Neo4j driver and session
    mock_session = MagicMock()
    mock_driver.return_value.session.return_value = mock_session

    # Instantiate the Neo4jConnection
    conn = Neo4jConnection("bolt://localhost:7687", "neo4j", "test_password")
    assert conn is not None

    # Mock the transaction function that is supposed to run inside write_transaction
    def mock_create_document(tx, *args):
        return True  # Simulate success

    # Ensure that the write_transaction is called with the correct function and arguments
    mock_session.write_transaction.side_effect = mock_create_document

    # Run a test of creating a document node
    conn.create_document_node("2023-12-30", "Award Notice", "USA")

    # Ensure that write_transaction was called once
    mock_session.write_transaction.assert_called_once()

    # Ensure that the function inside write_transaction is being executed with the correct arguments
    mock_session.write_transaction.assert_called_once_with(
        mock_create_document, "2023-12-30", "Award Notice", "USA"
    )

    # Close the connection
    conn.close()
    mock_session.close.assert_called_once()
