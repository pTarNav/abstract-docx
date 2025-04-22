from ooxml_docx.structure.numberings import OoxmlNumberings

def numberings_normalization(ooxml_numberings: OoxmlNumberings):
	for numbering in ooxml_numberings.numberings:
		print(numbering.id)
		print(numbering.abstract_numbering)