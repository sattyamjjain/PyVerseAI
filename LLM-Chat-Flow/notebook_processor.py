import nbformat
from nbformat import NotebookNode
from openai import OpenAI, APIConnectionError, APIError
from utils import setup_logger
from enum import Enum


class CellType(Enum):
    SYSTEM = "system"
    TOOLS = "tools"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_USE = "tool_use"
    TOOL_OUTPUT = "tool_output"
    CODE_MARKDOWN = "code/markdown"


class NotebookProcessor:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.logger = setup_logger("llm-chat-flow-logger")

    def generate_variation(self, cell_content: str, role: str) -> str:
        """Generate a variation of the conversation."""
        self.logger.debug(f"Generating variation for role: {role}")
        try:
            prompt = f"Generate a variation of the following {role} conversation:\n\n{cell_content}\n\nThe variation should have the same meaning and functionality but be rephrased."
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )
            return response.choices[0].message.content.strip()
        except APIConnectionError as e:
            self.logger.error(f"Error connecting to the API: {e}")
            return cell_content
        except APIError as e:
            self.logger.error(f"API returned an error: {e}")
            return cell_content
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            return cell_content

    def process_cell(self, cell: NotebookNode) -> None:
        """Process a cell in the notebook."""
        self.logger.debug(f"Processing cell: {cell['cell_type']}")
        if cell["cell_type"] in ("code", "markdown"):
            cell_type = self.identify_cell_type(cell["source"])
            cell["source"] = self.generate_variation(cell["source"], cell_type.value)

    @staticmethod
    def identify_cell_type(source: str) -> CellType:
        """Identify the type of cell based on its content."""
        if "system" in source:
            return CellType.SYSTEM
        elif "tools" in source:
            return CellType.TOOLS
        elif "user" in source:
            return CellType.USER
        elif "assistant" in source:
            return CellType.ASSISTANT
        elif "tool_use" in source:
            return CellType.TOOL_USE
        elif "tool_output" in source:
            return CellType.TOOL_OUTPUT
        else:
            return CellType.CODE_MARKDOWN

    def process_notebook(self, notebook: NotebookNode) -> NotebookNode:
        """Process the entire notebook."""
        self.logger.info("Processing notebook.")
        try:
            for cell in notebook["cells"]:
                self.process_cell(cell)
            return notebook
        except Exception as e:
            self.logger.error(f"Error processing notebook: {e}")
            return notebook

    def load_notebook(self, notebook_path: str) -> NotebookNode:
        """Load a notebook from a file."""
        self.logger.info(f"Loading notebook from: {notebook_path}")
        try:
            with open(notebook_path, "r") as f:
                notebook = nbformat.read(f, as_version=4)
            return notebook
        except FileNotFoundError as e:
            self.logger.error(f"Notebook file not found: {e}")
            raise
        except nbformat.reader.NotJSONError as e:
            self.logger.error(f"Notebook file is not valid JSON: {e}")
            raise
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while loading the notebook: {e}"
            )
            raise

    def save_notebook(self, notebook: NotebookNode, notebook_path: str) -> None:
        """Save a notebook to a file."""
        self.logger.info(f"Saving notebook to: {notebook_path}")
        try:
            with open(notebook_path, "w") as f:
                nbformat.write(notebook, f)
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while saving the notebook: {e}"
            )
            raise

    def process_and_save_notebook(
        self, input_notebook_path: str, output_notebook_path: str
    ) -> None:
        """Load, process, and save a notebook."""
        self.logger.info(
            f"Processing notebook from {input_notebook_path} to {output_notebook_path}"
        )
        try:
            notebook = self.load_notebook(input_notebook_path)
            modified_notebook = self.process_notebook(notebook)
            self.save_notebook(modified_notebook, output_notebook_path)
        except Exception as e:
            self.logger.error(f"An error occurred while processing the notebook: {e}")
