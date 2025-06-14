from __future__ import annotations
from utils.pydantic import ArbitraryBaseModel

from abstract_docx.normalization import EffectiveStructureFromOoxml

from abstract_docx.hierarchization.format.styles import HierarchicalStylesFromOoxml
from abstract_docx.hierarchization.format.numberings import HierarchicalNumberingsFromOoxml
from abstract_docx.hierarchization.document import HierarchicalDocumentFromOoxml


class HierarchicalStructureFromOoxml(ArbitraryBaseModel):
	styles: HierarchicalStylesFromOoxml
	numberings: HierarchicalNumberingsFromOoxml
	document: HierarchicalDocumentFromOoxml

	@classmethod
	def hierarchization(cls, effective_structure_from_ooxml: EffectiveStructureFromOoxml) -> HierarchicalStylesFromOoxml:
		hierarchical_styles_from_ooxml: HierarchicalStylesFromOoxml = HierarchicalStylesFromOoxml.hierarchization(
			effective_structure_from_ooxml=effective_structure_from_ooxml
		)

		hierarchical_numberings_from_ooxml: HierarchicalNumberingsFromOoxml = HierarchicalNumberingsFromOoxml.hierarchization(
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			hierarchical_styles_from_ooxml=hierarchical_styles_from_ooxml
		)
		
		hierarchical_document_from_ooxml: HierarchicalDocumentFromOoxml = HierarchicalDocumentFromOoxml.hierarchization(
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			hierarchical_styles_from_ooxml=hierarchical_styles_from_ooxml,
			hierarchical_numberings_from_ooxml=hierarchical_numberings_from_ooxml
		)

		return cls(
			styles=hierarchical_styles_from_ooxml,
			numberings=hierarchical_numberings_from_ooxml,
			document=hierarchical_document_from_ooxml
		)