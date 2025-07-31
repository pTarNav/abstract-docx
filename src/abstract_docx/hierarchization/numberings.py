from __future__ import annotations
from typing import Optional
from enum import Enum

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.data_models.styles import StylesView
from abstract_docx.data_models.numberings import Numbering, Enumeration, Level, MarkerType

from abstract_docx.normalization import EffectiveStructureFromOoxml

from abstract_docx.hierarchization.styles import HierarchicalStylesFromOoxml


class AvailableNumberingsPriorityParameters(Enum):
	NONE = "none"
	BULLET = "bullet"
	DECIMAL = "decimal"
	LOWER_LETTER = "lower_letter"
	UPPER_LETTER = "upper_letter"
	LOWER_ROMAN = "lower_roman"
	UPPER_ROMAN = "upper_roman"

class NumberingsPriorityParameters(list):

	@classmethod
	def load(cls, priorities: list[AvailableNumberingsPriorityParameters]):
		normalized = []
		seen = set()
		for idx, item in enumerate(priorities):
			# Coerce strings to enum, or verify enums
			if isinstance(item, AvailableNumberingsPriorityParameters):
				enum_item = item
			else:
				try:
					enum_item = AvailableNumberingsPriorityParameters(item)
				except ValueError:
					raise ValueError(f"Invalid numbering priority parameter at position {idx}: {item!r}")
			
			# Check for duplicates
			if enum_item in seen:
				raise ValueError(f"Duplicate numbering priority parameter not allowed: {enum_item.value!r}")
			seen.add(enum_item)
			normalized.append(enum_item)
		
		return cls(normalized)

DEFAULT_NUMBERINGS_PRIORITY_PARAMETERS: NumberingsPriorityParameters = NumberingsPriorityParameters.load(
	priorities=[
		AvailableNumberingsPriorityParameters.UPPER_ROMAN,
		AvailableNumberingsPriorityParameters.UPPER_LETTER,
		AvailableNumberingsPriorityParameters.DECIMAL,
		AvailableNumberingsPriorityParameters.LOWER_ROMAN,
		AvailableNumberingsPriorityParameters.LOWER_LETTER,
		AvailableNumberingsPriorityParameters.BULLET,
		AvailableNumberingsPriorityParameters.NONE
	]
)

class HierarchicalNumberingsFromOoxml(ArbitraryBaseModel):
	priority_ordered_levels: list[list[Level]]
	
	effective_structure_from_ooxml: EffectiveStructureFromOoxml

	styles_view: StylesView

	numberings_priority_parameters: NumberingsPriorityParameters

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
		hierarchical_styles_from_ooxml: HierarchicalStylesFromOoxml,
		numberings_priority_parameters: NumberingsPriorityParameters = DEFAULT_NUMBERINGS_PRIORITY_PARAMETERS
	) -> HierarchicalNumberingsFromOoxml:
		styles_view: StylesView = cls._precompute_styles_view(
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			hierarchical_styles_from_ooxml=hierarchical_styles_from_ooxml
		)

		hierarchical_numberings_from_ooxml: HierarchicalNumberingsFromOoxml = cls(
			priority_ordered_levels=[],
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			styles_view=styles_view,
			numberings_priority_parameters=numberings_priority_parameters
		)
		hierarchical_numberings_from_ooxml.compute()

		return hierarchical_numberings_from_ooxml
	
	def compute_priority_difference(self, level: Level, level_priority_representative: Level) -> int:
		"""
		Returns -1 if level has lower priority than the level priority representative
		Returns 0 if level has the same priority as the level priority representative
		Returns 1 if level has higher priority than the level priority representative
		"""

		for priority in self.numberings_priority_parameters:
			priority: MarkerType = MarkerType(priority.value)
			
			if (
				level.properties.marker_type == priority
				and level_priority_representative.properties.marker_type != priority
			):
				return 1
			if (
				level.properties.marker_type != priority
				and level_priority_representative.properties.marker_type == priority
			):
				return -1
			
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
	
		