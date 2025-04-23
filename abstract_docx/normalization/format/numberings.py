from ooxml_docx.structure.numberings import OoxmlNumberings

def numberings_normalization(ooxml_numberings: OoxmlNumberings):
	for numbering in ooxml_numberings.numberings:
		print(numbering.id, "->", numbering.abstract_numbering.id)
		if numbering.abstract_numbering.associated_styles:
			if numbering.abstract_numbering.associated_styles.style:
				x = numbering.abstract_numbering.associated_styles.style
				print("<-:", x.id, "~>", x.numbering.id, "->", x.numbering.abstract_numbering.id)
			if numbering.abstract_numbering.associated_styles.style_children:
				for style_child in numbering.abstract_numbering.associated_styles.style_children:
					print(":->", style_child.id, "~>", style_child.numbering.id, "->", style_child.numbering.abstract_numbering.id)
			