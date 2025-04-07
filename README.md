# abstract-docx

The tool can be divided into two modules:
- ***ooxml_docx***: Parses the underlying OOXML code inside the .docx file, capturing the necessary relations between OOXML objects. The idea is that this module is responsible of presenting a clean view of the OOXML code, but without making any changes to it. Any normalization or process that might change the underlying OOXML code will be done in the *abstract_docx* module.