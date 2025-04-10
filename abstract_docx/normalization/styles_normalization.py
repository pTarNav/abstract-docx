from __future__ import annotations
from typing import Optional
from ooxml_docx.structure.styles import OoxmlStyles
import ooxml_docx.structure.styles as OOXML_STYLES

from abstract_docx.views.format import Style, StyleProperties

def load_default_style(doc_defaults: OOXML_STYLES.DocDefaults) -> Style:
	return Style(
		id="__DocDefaults__",  # TODO: what happens if for some reason there already exists a style with this id?
		properties=StyleProperties.from_ooxml(
			run_properties=doc_defaults.default_run_properties,
			paragraph_properties=doc_defaults.default_paragraph_properties,
			must_default=True
		)
	)

def styles_normalization(ooxml_styles: OoxmlStyles) -> OoxmlStyles:
	default_style: Style = load_default_style(doc_defaults=ooxml_styles.doc_defaults)
	print(default_style)
		