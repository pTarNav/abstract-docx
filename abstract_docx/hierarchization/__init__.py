from __future__ import annotations
from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx

from abstract_docx.normalization import EffectiveStructureFromOoxml
from abstract_docx.hierarchization.format.styles import HierarchicalStylesFromOoxml


class HierarchicalStructureFromOoxml(ArbitraryBaseModel):
	styles: HierarchicalStylesFromOoxml
	

	@classmethod
	def hierarchization(cls, effective_structure_from_ooxml: EffectiveStructureFromOoxml) -> HierarchicalStylesFromOoxml:
		hierarchical_styles_from_ooxml: HierarchicalStylesFromOoxml = HierarchicalStylesFromOoxml.hierarchization(
			effective_structure_from_ooxml=effective_structure_from_ooxml
		)
		
		return cls(
			styles=hierarchical_styles_from_ooxml
		)