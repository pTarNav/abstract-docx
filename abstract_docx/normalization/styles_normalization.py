from __future__ import annotations
from ooxml_docx.structure.styles import OoxmlStyles

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format import Style




def styles_normalization(ooxml_styles: OoxmlStyles) -> OoxmlStyles:
	for style in ooxml_styles.roots.paragraph:
		print(style.id)
		