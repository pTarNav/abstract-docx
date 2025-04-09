from __future__ import annotations
from typing import Optional
from ooxml_docx.structure.styles import OoxmlStyles
from ooxml_docx.structure.properties import ParagraphProperties, RunProperties
from ooxml_docx.ooxml import OoxmlElement

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format import Style, VisualProperties, Script, Justification, Indentation


def load_default_style(ooxml_styles: OoxmlStyles) -> OoxmlStyles:
	run_properties: Optional[RunProperties] = ooxml_styles.doc_defaults.default_run_properties
	if run_properties is not None:
		font_size: Optional[float] = run_properties.xpath_query(query="./w:sz/@w:val", singleton=True)
		font_size = float(font_size) if font_size is not None else 1.0  # TODO: investigate further about default font size

		# TODO: color

		bold: bool = run_properties.xpath_query(query="./w:b", singleton=True) is not None
		italic: bool = run_properties.xpath_query(query="./w:i", singleton=True) is not None
		
		# Even though it is not a toggle property, we will treat it as such
		underline: bool = run_properties.xpath_query(query="./w:i", singleton=True) is not None
		
		script: Script = Script.from_ooxml_val(v=run_properties.xpath_query(query="./w:vertAlign/@w:val", singleton=True))
	else:
		font_size 


	paragraph_properties: Optional[ParagraphProperties] = ooxml_styles.doc_defaults.default_paragraph_properties
	if paragraph_properties is not None:
		justification: Justification = Justification.from_ooxml_val(
			v=paragraph_properties.xpath_query(query="./w:jc/@w:val", singleton=True)
		)
		indentation: Indentation = Indentation.from_ooxml(
			element=paragraph_properties.xpath_query(query="./w:ind", singleton=True)
		)



def styles_normalization(ooxml_styles: OoxmlStyles) -> OoxmlStyles:
	default_style: Style = load_default_style(ooxml_styles=ooxml_styles)
		