import os

from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    SAMPLE_INPUT_FILES_PATH,
    SAMPLE_OUTPUT_FILES_PATH,
)
from notebook_processor import NotebookProcessor


def generate_output_path(input_path: str, output_dir: str) -> str:
    """Generate an output file path based on the input file path."""
    filename = os.path.basename(input_path)
    output_filename = f"Modified_{filename}"
    return os.path.join(output_dir, output_filename)


def main() -> None:
    input_paths = [
        os.path.join(SAMPLE_INPUT_FILES_PATH, f)
        for f in os.listdir(SAMPLE_INPUT_FILES_PATH)
        if f.endswith(".ipynb")
    ]
    output_paths = [
        generate_output_path(path, SAMPLE_OUTPUT_FILES_PATH) for path in input_paths
    ]

    processor = NotebookProcessor(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)

    for input_path, output_path in zip(input_paths, output_paths):
        processor.process_and_save_notebook(input_path, output_path)


if __name__ == "__main__":
    main()
