from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import StylesView
from abstract_docx.views.format.numberings import Numbering, Enumeration, Level

from abstract_docx.normalization import EffectiveStructureFromOoxml

from abstract_docx.hierarchization.format.styles import HierarchicalStylesFromOoxml


class HierarchicalNumberingsFromOoxml(ArbitraryBaseModel):
	priority_ordered_levels: list[list[Level]]
	
	effective_structure_from_ooxml: EffectiveStructureFromOoxml

	styles_view: StylesView

	@staticmethod
	def _precompute_styles_view(
		effective_structure_from_ooxml: EffectiveStructureFromOoxml,
		hierarchical_styles_from_ooxml: HierarchicalStylesFromOoxml,
	) -> StylesView:
		return StylesView.load(
			styles=effective_structure_from_ooxml.styles.effective_styles,
			priority_ordered_styles=hierarchical_styles_from_ooxml.priority_ordered_styles
		)
			
	@classmethod
	def hierarchization(
		cls,
		effective_structure_from_ooxml: EffectiveStructureFromOoxml,
		hierarchical_styles_from_ooxml: HierarchicalStylesFromOoxml
	) -> HierarchicalNumberingsFromOoxml:
		styles_view: StylesView = cls._precompute_styles_view(
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			hierarchical_styles_from_ooxml=hierarchical_styles_from_ooxml
		)

		hierarchical_numberings_from_ooxml: HierarchicalNumberingsFromOoxml = cls(
			priority_ordered_levels=[],
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			styles_view=styles_view
		)
		hierarchical_numberings_from_ooxml.compute()

		return hierarchical_numberings_from_ooxml
	
	def compute_priority_difference(self, level: Level, level_priority_representative: Level) -> int:
		"""
		Returns -1 if level has lower priority than the level priority representative
		Returns 0 if level has the same priority as the level priority representative
		Returns 1 if level has higher priority than the level priority representative
		"""
		
		# TODO: take actual level properties into account (not only style)

		return self.styles_view.priority_difference(
			curr_style=level.style, prev_style=level_priority_representative.style
		)

	def compute(self) -> None:
		for effective_level in self.effective_structure_from_ooxml.numberings.effective_levels.values():
			if len(self.priority_ordered_levels) == 0:
				self.priority_ordered_levels.append([effective_level])
			else:
				for i, priority in enumerate(self.priority_ordered_levels):
					priority_difference: int = self.compute_priority_difference(
						level=effective_level, level_priority_representative=priority[0]
					)

					match priority_difference:
						case -1:
							# Continue searching for equal or lower priority (if possible)
							if i == len(self.priority_ordered_levels) - 1:
								self.priority_ordered_levels.append([effective_level])
						case 0:
							# Insert level into the current priority level (and stop search)
							priority.append(effective_level)
							break
						case 1:
							# Insert level one priority level above of the current priority level (and stop search)
							self.priority_ordered_levels.insert(i, [effective_level])
							break
	
		