# abstract-docx

*abstract-docx* is a tool that allows users to parse *Word* (``docx``) documents, with focus on achieving high fidelity tree representation of the document.

It is designed for situation where precise structural and hierarchical preservation matters, such as parsing technical documentation, legal text, or heavily formatted reports.

With correct numbering support, it handles multi-level numbered paragraphs, exactly as rendered in *Word*.

Unlike many ``.docx`` parsers, *abstract-docx* focuses on structure first rather than just extracting plain text. This means you can navigate a document's hierarchy exactly as it appears in the file.

## Installation set-up and sample usage
Clone the GitHub repository locally and install dependencies.
```bash
pip install -r "abstract-docx/requirements.txt"
pip install -e "abstract-docx/."
```

Sample usage:
```python
from abstract_docx.main import AbstractDocx

doc: AbstractDocx = AbstractDocx.read(file_path="<your-file-name>.docx") # Read and parse the .docx file
doc() # Apply the heuristic layer to obtain the effective and hierarchical structures

# Visualize result
doc.print()
```

## Testing

### Running Tests

The project uses `pytest` for testing. To run the test suite:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run tests with coverage report
pytest --cov=src --cov-report=term-missing

# Run tests for a specific module
pytest tests/unit/utils/
pytest tests/unit/data_models/
pytest tests/unit/abstract_docx/

# Run a specific test file
pytest tests/unit/data_models/test_document.py

# Run a specific test
pytest tests/unit/data_models/test_document.py::TestRun::test_run_creation
```

### Test Coverage

The project maintains unit tests for core functionalities including:

- **Utility Modules** (`tests/unit/utils/`)
  - Pydantic base model configuration
  - XML and Rich tree printing utilities

- **Data Models** (`tests/unit/data_models/`)
  - Document structure (Block, Paragraph, Table, Run, etc.)
  - Style properties (FontSize, FontColor, RunStyleProperties, etc.)
  - Formatting and numbering

- **Main Module** (`tests/unit/abstract_docx/`)
  - AbstractDocx initialization and configuration
  - Error handling and validation

To generate a detailed coverage report:

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View the report
# Open htmlcov/index.html in your browser
```

### Installing Test Dependencies

Test dependencies are included in `requirements.txt`. If you need to install them separately:

```bash
pip install pytest pytest-cov
```

### Writing Tests

When contributing to the project, please:

1. Add tests for any new functionality
2. Ensure existing tests pass before submitting changes
3. Follow the existing test structure and naming conventions
4. Use descriptive test names that explain what is being tested
5. Include both positive and negative test scenarios
6. Mock external dependencies when appropriate

Test files should be placed in the appropriate subdirectory under `tests/unit/` and follow the naming convention `test_<module_name>.py`.

## Technical documentation

The document tree structure is formed by **blocks**, which contain the hierarchical relationships through parent-child relationships. As well as the block content based on it's type.

There are two main types of **blocks**:
- Paragraphs:
- Tables:

### Views


## Future plans

Interoperability with the *python-docx* package.