from ooxml_docx.structure.numberings import OoxmlNumberings, AbstractNumbering, NumberingStyle


def walk(abstract_numbering: AbstractNumbering, depth: int):
	print("\t"*depth, abstract_numbering.id)
	if abstract_numbering.associated_styles is not None:
		style_parent: NumberingStyle = abstract_numbering.associated_styles.style_parent
		if style_parent is not None:
			if style_parent.abstract_numbering_parent is not None:
				print("\t"*depth, "--through styleLink--")
				walk(abstract_numbering=style_parent.abstract_numbering_parent, depth=depth+1)
			if style_parent.numbering is not None:
				print("\t"*depth, "--through numbering--")
				walk(abstract_numbering=style_parent.numbering.abstract_numbering, depth=depth+1)

	

def numberings_normalization(ooxml_numberings: OoxmlNumberings):
	# Assumption: There cannot be any loop with the style_parent and style_children relationship.
	# TODO: some kind of validation of this assumption and raise error if not the case (maybe track visited nodes and if cycle raise)
	for numbering in ooxml_numberings.numberings:
		print("#", numbering.id, "#")
		walk(abstract_numbering=numbering.abstract_numbering, depth=1)
		
