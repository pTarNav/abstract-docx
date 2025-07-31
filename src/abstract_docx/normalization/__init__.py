from __future__ import annotations
from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx

from abstract_docx.normalization.styles import EffectiveStylesFromOoxml
from abstract_docx.normalization.numberings import EffectiveNumberingsFromOoxml
from abstract_docx.normalization.document import EffectiveDocumentFromOoxml


class EffectiveStructureFromOoxml(ArbitraryBaseModel):
	styles: EffectiveStylesFromOoxml
	numberings: EffectiveNumberingsFromOoxml
	document: EffectiveDocumentFromOoxml

	@classmethod
	def normalization(cls, ooxml_docx: OoxmlDocx) -> EffectiveStructureFromOoxml:
		effective_styles_from_ooxml: EffectiveStylesFromOoxml = EffectiveStylesFromOoxml.normalization(
			ooxml_styles=ooxml_docx.structure.styles
		)
		
		effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml = EffectiveNumberingsFromOoxml.normalization(
			ooxml_numberings=ooxml_docx.structure.numberings, effective_styles_from_ooxml=effective_styles_from_ooxml
		)
		
		effective_document_from_ooxml: EffectiveDocumentFromOoxml = EffectiveDocumentFromOoxml.normalization(
			ooxml_document=ooxml_docx.structure.document,
			effective_styles_from_ooxml=effective_styles_from_ooxml,
			effective_numberings_from_ooxml=effective_numberings_from_ooxml
		)
		
		return cls(
			styles=effective_styles_from_ooxml,
			numberings=effective_numberings_from_ooxml,
			document=effective_document_from_ooxml
		)