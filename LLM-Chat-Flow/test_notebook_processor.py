import pytest
from notebook_processor import NotebookProcessor, CellType
from unittest.mock import MagicMock, patch
import nbformat


@pytest.fixture
def processor():
    return NotebookProcessor(api_key="test_key", model="gpt-4")


def test_generate_variation(processor):
    with patch.object(
        processor.client.chat.completions,
        "create",
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="variation"))]
        ),
    ) as mock_create:
        result = processor.generate_variation("test content", "user")
        assert result == "variation"
        mock_create.assert_called_once()


def test_identify_cell_type():
    assert NotebookProcessor.identify_cell_type("system") == CellType.SYSTEM
    assert NotebookProcessor.identify_cell_type("tools") == CellType.TOOLS


def test_process_notebook(processor):
    with patch.object(
        processor.client.chat.completions,
        "create",
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="variation"))]
        ),
    ) as mock_create:
        notebook = nbformat.v4.new_notebook(
            cells=[nbformat.v4.new_code_cell("system code")]
        )
        processor.process_notebook(notebook)
        mock_create.assert_called_once()
