import ooxml_docx.document.paragraph as OOXML_PARAGRAPH

from abstract_docx.views.format.styles import Style, StyleProperties

def document_normalization(ooxml_document, effective_styles, effective_numberings):
	return
	for p in ooxml_document.ooxml_docx.structure.document.body:
		if isinstance(p, OOXML_PARAGRAPH.Paragraph):
			print("+"*42)
			if p.style is not None:
				#print("style=", effective_styles.get_mapped_id(ooxml_style_id=p.style.id))
				pass
			if p.properties is not None:
				effective_style = Style(
					id="dummy",
					properties=StyleProperties.aggregate_ooxml(
					agg=(
						effective_styles.get(ooxml_style_id=p.style.id).properties
						if p.style is not None else effective_styles.get_default().properties
					),
					add=StyleProperties.from_ooxml(run_properties=p.properties.run_properties, paragraph_properties=p.properties),
					default=effective_styles.get_default().properties
				))
				matched = False
				for x in effective_styles.effective_styles.values():
					if x == effective_style:
						if p.style is not None:
							if effective_styles.get(p.style.id).id == x.id:
								print(effective_styles.get(p.style.id).id, "==")
							else:
								print(effective_styles.get(p.style.id).id, "=>", x.id)
						else:
							print("~ =>", x.id)
						matched = True
						break
				
				if not matched:
					if p.style is not None:
						print(effective_styles.get(p.style.id).id, "=> ~")
					else:
						print("~ => ~")
						
				
				
				