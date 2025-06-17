# abstract-docx
## Installation set-up and sample usage
Clone the GitHub repository locally and install dependencies.
```
pip install -r "abstract-docx/requirements.txt"
pip install -e "abstract-docx/."
```

Sample usage:
```
from abstract_docx.main import AbstractDocx

doc: AbstractDocx = AbstractDocx.read(file_path="<your-file-name>.docx") # Read and parse the .docx file
doc() # Apply the heuristic layer to obtain the effective and hierarchical structures

# Visualize result
doc.print()
```
