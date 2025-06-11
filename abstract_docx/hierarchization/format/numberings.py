from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.numberings import Numbering, Enumeration, Level

from abstract_docx.normalization import EffectiveStructureFromOoxml


class HierarchicalNumberingsFromOoxml(ArbitraryBaseModel):
	priority_ordered_enumeration_and_levels: dict[str, list[list[Level]]]
	effective_structure_from_ooxml: EffectiveStructureFromOoxml

	@classmethod
	def hierarchization(
		cls, effective_structure_from_ooxml: EffectiveStructureFromOoxml	
	) -> HierarchicalNumberingsFromOoxml:
		
		hierarchical_numberings_from_ooxml: HierarchicalNumberingsFromOoxml = cls(
			priority_ordered_enumerations_and_levels={},
			effective_structure_from_ooxml=effective_structure_from_ooxml
		)
		hierarchical_numberings_from_ooxml.compute()
		
	def compute(self) -> None:
		pass