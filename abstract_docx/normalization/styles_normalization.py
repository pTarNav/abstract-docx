from __future__ import annotations
from typing import Optional
from ooxml_docx.structure.styles import OoxmlStyles
import ooxml_docx.structure.styles as OOXML_STYLES


from colour import Color

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format import Style, StyleProperties, RunStyleProperties, FontSize, Script, ParagraphStyleProperties, Justification, Indentation

def load_default_style(doc_defaults: OOXML_STYLES.DocDefaults) -> Style:
	return Style(
			id="__DocDefaults__",  # TODO: what happens if for some reason there already exists a style with this id?
			properties=StyleProperties(
				run_style_properties=load_run_style_properties(
					run_properties=doc_defaults.default_run_properties, must_default=True
				),
				paragraph_style_properties=load_paragraph_style_properties(
					paragraph_properties=doc_defaults.default_paragraph_properties, must_default=True
				)
			)
		)





def styles_normalization(ooxml_styles: OoxmlStyles) -> OoxmlStyles:
	default_style: Style = load_default_style(ooxml_styles=ooxml_styles)

		