from __future__ import annotations
from typing import Optional
from ooxml_docx.structure.styles import OoxmlStyles
import ooxml_docx.structure.properties as OOXML_PROPERTIES
from ooxml_docx.ooxml import OoxmlElement

from colour import Color

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format import Style, StyleProperties, RunSpecificStyleProperties, Script, ParagraphSpecificStyleProperties, Justification, Indentation


def load_default_style(ooxml_styles: OoxmlStyles) -> Style:
	run_properties: Optional[OOXML_PROPERTIES.RunProperties] = ooxml_styles.doc_defaults.default_run_properties
	if run_properties is not None:
		font_size: Optional[float] = run_properties.xpath_query(query="./w:sz/@w:val", singleton=True)
		run_specific_style_properties: RunSpecificStyleProperties = RunSpecificStyleProperties(
			font_size=float(font_size) if font_size is not None else 1.0,  # TODO: investigate further about default font size
			color=Color,  # TODO: actually implement color parsing
			bold=run_properties.xpath_query(query="./w:b", singleton=True) is not None,
			italic=run_properties.xpath_query(query="./w:i", singleton=True) is not None,
			# Even though it is not a toggle property, we will treat it as such because of the tool intended use
			underline=run_properties.xpath_query(query="./w:i", singleton=True) is not None,
			script=Script.from_ooxml_val(v=run_properties.xpath_query(query="./w:vertAlign/@w:val", singleton=True))
		)
	else:
		run_specific_style_properties: RunSpecificStyleProperties = RunSpecificStyleProperties.default()

	paragraph_properties: Optional[OOXML_PROPERTIES.ParagraphProperties] = ooxml_styles.doc_defaults.default_paragraph_properties
	if paragraph_properties is not None:
		paragraph_specific_style_properties: ParagraphSpecificStyleProperties = ParagraphSpecificStyleProperties(
			justification=Justification.from_ooxml_val(
				v=paragraph_properties.xpath_query(query="./w:jc/@w:val", singleton=True)
			),
			indentation=Indentation.from_ooxml(
				element=paragraph_properties.xpath_query(query="./w:ind", singleton=True)
			)
		)
	else:
		paragraph_specific_style_properties: ParagraphSpecificStyleProperties = ParagraphSpecificStyleProperties.default()

	return Style(
			id="__DocDefaults__",  # TODO: what happens if for some reason there already exists a style with this id?
			properties=StyleProperties(
				run_properties=run_specific_style_properties, paragraph_properties=paragraph_specific_style_properties
			)
		)



def styles_normalization(ooxml_styles: OoxmlStyles) -> OoxmlStyles:
	default_style: Style = load_default_style(ooxml_styles=ooxml_styles)

		