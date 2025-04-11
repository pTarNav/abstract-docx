from __future__ import annotations
from typing import Optional
from ooxml_docx.structure.styles import OoxmlStyles
import ooxml_docx.structure.styles as OOXML_STYLES

from abstract_docx.views.format import Style, StyleProperties, RunStyleProperties, ParagraphStyleProperties, ToggleProperty, Underline, Indentation

def load_default_style(doc_defaults: OOXML_STYLES.DocDefaults) -> Style:
	return Style(
		id="__DocDefaults__",  # TODO: what happens if for some reason there already exists a style with this id?
		properties=StyleProperties.from_ooxml(
			run_properties=doc_defaults.default_run_properties,
			paragraph_properties=doc_defaults.default_paragraph_properties,
			must_default=True
		)
	)

def aggregate_effective_style(agg_style: Style, add_style: Style, default_style: Style) -> Style:
	# Can assume that agg_style will never have empty style properties since it inherits from the default style at the root
	return Style(
		id=add_style.id,
		properties=StyleProperties(
			run_style_properties=RunStyleProperties(
				font_size=add_style.properties.run_style_properties.font_size if add_style.properties.run_style_properties.font_size is not None else agg_style.properties.run_style_properties.font_size,
				font_color=add_style.properties.run_style_properties.font_color if add_style.properties.run_style_properties.font_color is not None else agg_style.properties.run_style_properties.font_color,
				font_script=add_style.properties.run_style_properties.font_script if add_style.properties.run_style_properties.font_script is not None else agg_style.properties.run_style_properties.font_script,
				# TODO: add table style possible toggle properties into the xor
				bold=default_style.properties.run_style_properties.bold or ToggleProperty(bool(add_style.properties.run_style_properties.bold) ^ agg_style.properties.run_style_properties.bold),
				italic=default_style.properties.run_style_properties.italic or ToggleProperty(bool(add_style.properties.run_style_properties.italic) ^ agg_style.properties.run_style_properties.italic),
				underline=default_style.properties.run_style_properties.underline or Underline(bool(add_style.properties.run_style_properties.underline) ^ agg_style.properties.run_style_properties.underline)
			),
			paragraph_style_properties=ParagraphStyleProperties(
				justification=add_style.properties.paragraph_style_properties.justification if add_style.properties.paragraph_style_properties.justification is not None else agg_style.properties.paragraph_style_properties.justification,
				indentation=Indentation(
					start=add_style.properties.paragraph_style_properties.indentation.start if add_style.properties.paragraph_style_properties.indentation.start is not None else agg_style.properties.paragraph_style_properties.indentation.start,
					end=add_style.properties.paragraph_style_properties.indentation.end if add_style.properties.paragraph_style_properties.indentation.end is not None else agg_style.properties.paragraph_style_properties.indentation.end,
					first=add_style.properties.paragraph_style_properties.indentation.first if add_style.properties.paragraph_style_properties.indentation.first is not None else agg_style.properties.paragraph_style_properties.indentation.first
				)
			)
		)
	)

def compute_effective_style(ooxml_style: OOXML_STYLES.Style, agg_effective_style: Style, default_style: Style):
	match type(ooxml_style):
		case OOXML_STYLES.RunStyle:
			other_shallow_effective_style_properties: StyleProperties = StyleProperties.from_ooxml(
				run_properties=ooxml_style.properties
			)
		case OOXML_STYLES.ParagraphStyle:
			other_shallow_effective_style_properties: StyleProperties = StyleProperties.from_ooxml(
				run_properties=ooxml_style.run_properties, paragraph_properties=ooxml_style.properties
			)
		case _:
			raise ValueError("") # TODO

	agg_effective_style: Style = aggregate_effective_style(
		agg_style=agg_effective_style,
		add_style=Style(id=ooxml_style.id, properties=other_shallow_effective_style_properties),
		default_style=default_style
	)

	print(ooxml_style.id, "=>", agg_effective_style)

	if ooxml_style.children is not None:
		for child in ooxml_style.children:
			compute_effective_style(ooxml_style=child, agg_effective_style=agg_effective_style, default_style=default_style)
	

def styles_normalization(ooxml_styles: OoxmlStyles) -> OoxmlStyles:
	default_style: Style = load_default_style(doc_defaults=ooxml_styles.doc_defaults)

	# Compute effective styles top-down through the basedOn hierarchy
	for ooxml_style in ooxml_styles.roots.paragraph:
		compute_effective_style(ooxml_style=ooxml_style, agg_effective_style=default_style, default_style=default_style)
	for ooxml_style in ooxml_styles.roots.run:
		compute_effective_style(ooxml_style=ooxml_style, agg_effective_style=default_style, default_style=default_style)
	
	
