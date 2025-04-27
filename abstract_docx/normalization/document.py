import ooxml_docx.document.paragraph as OOXML_PARAGRAPH

from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml
from abstract_docx.normalization.format.numberings import EffectiveNumberingsFromOoxml

from abstract_docx.views.format.styles import Style, StyleProperties
from abstract_docx.views.document import Paragraph, Run, Block

import ooxml_docx.document.run as OOXML_RUN
from abstract_docx.views.format import Format

def _associate_effective_styles(effective_blocks: list[Block], effective_styles_from_ooxml: EffectiveStylesFromOoxml) -> None:
	"""_summary_
	"""
	# TODO: optimize this loops
	for effective_block in effective_blocks:
			if isinstance(effective_block, Paragraph):
				found_effective_style_match: bool = False
				for effective_style in effective_styles_from_ooxml.effective_styles.values():
						if effective_block.format.style == effective_style:
							effective_block.format.style = effective_style
							found_effective_style_match = True
							break
				
				if not found_effective_style_match:
					effective_styles_from_ooxml.effective_styles[effective_block.format.style.id] = effective_block.format.style

				for effective_text in effective_block.content:
					found_effective_style_match: bool = False
					for effective_style in effective_styles_from_ooxml.effective_styles.values():
							if effective_text.style == effective_style:
								effective_text.style = effective_style
								found_effective_style_match = True
								break
					
					if not found_effective_style_match:
						effective_styles_from_ooxml.effective_styles[effective_text.style.id] = effective_text.style

def content_normalization(ooxml_paragraph: OOXML_PARAGRAPH.Paragraph, effective_paragraph_style: Style, effective_styles_from_ooxml: EffectiveStylesFromOoxml, block_id: int) -> list[Run]:
	content: list[Run] = []
	for c in ooxml_paragraph.content:
		content_id = f"__@PARAGRAPH={block_id}@RUN={len(content)}__"
		if isinstance(c, OOXML_RUN.Run):
			if c.style is not None:
				effective_run_style: Style = Style(
					id=content_id,
					properties=StyleProperties.aggregate_ooxml(
						agg=effective_paragraph_style.properties,
						add=effective_styles_from_ooxml.get(ooxml_style_id=c.style.id).properties,
						default=effective_styles_from_ooxml.get_default().properties
					)
				)
			else:
				effective_run_style: Style = effective_paragraph_style
			
			if c.properties is not None:
				effective_run_style: Style = Style(
					id=content_id,
					properties=StyleProperties.aggregate_ooxml(
						agg=effective_run_style.properties,
						add=StyleProperties.from_ooxml(run_properties=c.properties),
						default=effective_styles_from_ooxml.get_default().properties
					)
				)

			curr_run = Run.from_ooxml(ooxml_run=c, style=effective_run_style)
			if len(content) > 0 and isinstance(content[-1], Run) and content[-1].style == curr_run.style:
				content[-1].concat(other=curr_run)
			else:
				content.append(curr_run)
	
	return content


def document_normalization(ooxml_document, effective_styles_from_ooxml: EffectiveStylesFromOoxml, effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml):
	effective_blocks: list[Block] = []
	for block_id, p in enumerate(ooxml_document.ooxml_docx.structure.document.body):
		if isinstance(p, OOXML_PARAGRAPH.Paragraph):
			# TODO: actually assign effective style to paragraph data model
			if p.properties is not None:
				effective_paragraph_style: Style = Style(
					id=f"__@PARAGRAPH={block_id}__",
					properties=StyleProperties.aggregate_ooxml(
						agg=(
							effective_styles_from_ooxml.get(ooxml_style_id=p.style.id).properties
							if p.style is not None else effective_styles_from_ooxml.get_default().properties
						),
						add=(StyleProperties.from_ooxml(run_properties=p.properties.run_properties, paragraph_properties=p.properties)),
						default=effective_styles_from_ooxml.get_default().properties
					)
				)

				found_effective_style_match: bool = False
				for effective_style in effective_styles_from_ooxml.effective_styles.values():
					if effective_paragraph_style == effective_style:
						effective_paragraph_style = effective_style
						found_effective_style_match = True
						break
				
				if not found_effective_style_match:
					effective_styles_from_ooxml.effective_styles[effective_paragraph_style.id] = effective_paragraph_style
			else:
				if p.style is not None:
					effective_paragraph_style: Style = effective_styles_from_ooxml.get(ooxml_style_id=p.style.id)
				else:
					effective_paragraph_style: Style = effective_styles_from_ooxml.get_default()
			
			effective_paragraph_content = content_normalization(ooxml_paragraph=p, effective_paragraph_style=effective_paragraph_style, effective_styles_from_ooxml=effective_styles_from_ooxml, block_id=block_id)
			effective_paragraph: Paragraph = Paragraph(
				id=block_id,
				content=effective_paragraph_content,
				format=Format(style=effective_paragraph_style)
			)
			effective_blocks.append(effective_paragraph)
			print([x.text for x in effective_paragraph.content])
	
	print(set(effective_styles_from_ooxml.effective_styles.keys()))
	_associate_effective_styles(effective_blocks=effective_blocks, effective_styles_from_ooxml=effective_styles_from_ooxml) # TODO. here we are doing more work than necessary, at a pragraph level we already do the style check and insertion
	print(set(effective_styles_from_ooxml.effective_styles.keys()))