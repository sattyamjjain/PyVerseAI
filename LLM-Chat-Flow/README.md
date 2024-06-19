# LLM-Chat-Flow

LLM-Chat-Flow is a project that demonstrates how to use GPT-4 to generate variations of RLHF (Reinforcement Learning with Human Feedback) conversations in Jupyter Notebooks. This project is designed to process input notebooks, generate variations of code cells using GPT-4, and save the modified notebooks.

## Features

- **Notebook Processing:** Automatically processes Jupyter Notebooks to generate variations of code cells.
- **Configuration:** Easily configurable through a YAML file.
- **Logging:** Logs important information for debugging and tracking purposes.
- **Testing:** Includes unit tests for core functionalities.

## Installation

### Prerequisites

- Python 3.7+
- pip

### Steps

1. Clone the repository:
    ```bash
    git clone https://github.com/sattyamjjain/PyVerseAI.git
    cd LLM-Chat-Flow
    ```

2. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3. Install the test requirements (optional, for running tests):
    ```bash
    pip install -r test-requirements.txt
    ```

## Configuration

The configuration is handled through a `config.yaml` file. You can adjust the parameters as needed:

```yaml
openai:
  api_key: api-key
  model: gpt-4-turbo

logging:
  file: llm-chat-flow.log

paths:
  input_dir: sample_inputs
  output_dir: sample_outputs
```

## Usage

### Running the Application

```bash
python main.py
```

This will load the configuration, process the input notebooks, and save the modified notebooks to the specified output directory.

### Sample Inputs and Outputs

- Input Notebooks: Place your input notebooks in the sample_inputs directory.
- Output Notebooks: The processed notebooks will be saved in the sample_outputs directory.

## Logging

The application logs important information to ```llm-chat-flow.log```. You can check this file for debugging and tracking the application's behavior.

## Testing

Unit tests are included to ensure the core functionalities work as expected. To run the tests, use:

```bash
pytest
```

This will execute the tests defined in test_notebook_processor.py.
