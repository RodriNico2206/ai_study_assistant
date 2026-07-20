# AI Study Assistant
The AI Study Assistant is a tool designed to generate comprehensive study guides from large PDF documents. It utilizes a hierarchical Map-Reduce process to handle large documents within free tier token limits, ensuring efficient and effective processing.

## Key Features
* Processes PDF files in batches to avoid token limits
* Generates summaries using a configured model
* Reduces summaries hierarchically to create a global overview
* Supports custom instructions for tailored summaries
* Automatically saves the global overview to a Markdown file

## Directory Hierarchy
```markdown
.
├── .gitignore
├── README.md
├── calculo-trascendentes-tempranas-zill-4th_funciones_global_summary.md
├── config.json
├── poetry.lock
├── pyproject.toml
├── src
│   └── ai_study_assistant
│       ├── config.py
│       ├── extractors.py
│       ├── generator.py
│       └── main.py
└── summaries
```

## Module Functionality
The AI Study Assistant consists of several modules:
* `config.py`: Handles configuration loading and validation
* `extractors.py`: Not used in the provided code, potentially for future PDF extraction functionality
* `generator.py`: Generates summaries and reduces them hierarchically
* `main.py`: The entry point of the application, responsible for processing PDF files and generating study guides

## Prerequisites and Environment Setup
* Python 3.8 or later
* Poetry package manager
* A compatible PDF reader (e.g., PyPDF2)

To set up the environment:
1. Activate the virtual environment using `source venv/bin/activate` 
2. Install Poetry using the official installation instructions.
3. Create a new virtual environment using `poetry install`.

### Configuration
The AI Study Assistant uses a JSON configuration file to load parameters. The configuration file should contain the following parameters:
* `MODEL_NAME`: The model identifier used for summary generation (for example `llama-3.1-8b-instant`).
* `BATCH_SIZE`: The number of PDF pages processed in each batch when generating partial summaries. A smaller batch size reduces token usage per request, while a larger batch size may improve throughput.
* `GROQ_API_KEY`: Your API key for the Groq service, required to authenticate requests to the Groq API for model access.
* `input_path`: The path to the input PDF file
* `custom_instructions`: Optional custom instructions for the summary generation (default: empty string)

Example configuration file:
```json
{
    "MODEL_NAME": "llama-3.1-8b-instant",
    "BATCH_SIZE": 2,
    "GROQ_API_KEY": "YOUR_GROQ_API_KEY",
    "input_path": "path/to/input.pdf",
    "custom_instructions": "Custom instructions for the summary"
}
```

## Installation
To install the AI Study Assistant, run the following command:
```bash
poetry install
```

## Usage Example
To run the AI Study Assistant, use the following command:
```bash
poetry run python src/ai_study_assistant/main.py --config path/to/config.json
```
Replace `path/to/config.json` with the actual path to your configuration file.

## Usage Restrictions
* The AI Study Assistant only supports PDF files.
* The input PDF file should be in the same directory as the configuration file or specified using an absolute path.
* The `custom_instructions` parameter is optional, but if provided, it should be a string.

## Workflow Diagram
```mermaid
graph LR
    A[Load Configuration] -->|Load input_path and custom_instructions| B[Process PDF]
    B -->|Split PDF into batches| C[Generate Summaries]
    C -->|Reduce summaries hierarchically| D[Generate Global Overview]
    D -->|Save global overview to Markdown file| E[Finish]
```
Note: This diagram illustrates the high-level workflow of the AI Study Assistant. The actual implementation may vary depending on the specific requirements and configuration.