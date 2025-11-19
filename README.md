# abstract-docx

*abstract-docx* is a tool that allows users to parse *Word* (``docx``) documents, with focus on achieving high fidelity tree representation of the document.

It is designed for situation where precise structural and hierarchical preservation matters, such as parsing technical documentation, legal text, or heavily formatted reports.

With correct numbering support, it handles multi-level numbered paragraphs, exactly as rendered in *Word*.

Unlike many ``.docx`` parsers, *abstract-docx* focuses on structure first rather than just extracting plain text. This means you can navigate a document's hierarchy exactly as it appears in the file.

## Installation set-up and sample usage
Clone the GitHub repository locally and install dependencies.
```
pip install -r "abstract-docx/requirements.txt"
pip install -e "abstract-docx/."
```

Sample usage:
```python
from abstract_docx.main import AbstractDocx

# Read and parse the .docx file
# Apply the heuristic layer to obtain the effective and hierarchical structures
doc: AbstractDocx = AbstractDocx.read(file_path="<your-file-name>.docx")

# Visualize result
doc.print()
```

## Technical documentation

The document tree structure is formed by **blocks**, which contain the hierarchical relationships through parent-child relationships. As well as the block content based on it's type.

There are two main types of **blocks**:
- Paragraphs:
- Tables:

### Views


## Future plans

Interoperability with the *python-docx* package.
