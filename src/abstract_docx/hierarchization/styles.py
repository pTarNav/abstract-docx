from __future__ import annotations
from typing import Optional
from enum import Enum

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.data_models.styles import Style

from abstract_docx.normalization import EffectiveStructureFromOoxml


class AvailableStylePriorityParameters(Enum):
	FONT_SIZE = "font_size"
	FONT_COLOR = "font_color"
	FONT_SCRIPT = "font_script"
	BOLD = "bold"
	ITALIC = "italic"
	UNDERLINE = "underline"
	JUSTIFICATION = "justification"
	INDENTATION = "indentation"

class StylesPriorityParameters(list):

	@classmethod
	def load(cls, priorities: list[AvailableStylePriorityParameters]):
		normalized = []
		seen = set()
		for idx, item in enumerate(priorities):
			# Coerce strings to enum, or verify enums
			if isinstance(item, AvailableStylePriorityParameters):
				enum_item = item
			else:
				try:
					enum_item = AvailableStylePriorityParameters(item)
				except ValueError:
					raise ValueError(f"Invalid style priority parameter at position {idx}: {item!r}")
			
			# Check for duplicates
			if enum_item in seen:
				raise ValueError(f"Duplicate style priority parameter not allowed: {enum_item.value!r}")
			seen.add(enum_item)
			normalized.append(enum_item)
		
		return cls(normalized)


DEFAULT_STYLES_PRIORITY_PARAMETERS: StylesPriorityParameters = StylesPriorityParameters.load(
	priorities=[AvailableStylePriorityParameters.FONT_SIZE, AvailableStylePriorityParameters.BOLD, AvailableStylePriorityParameters.INDENTATION]
)

class HierarchicalStylesFromOoxml(ArbitraryBaseModel):
	priority_ordered_styles: list[list[Style]]

	effective_structure_from_ooxml: EffectiveStructureFromOoxml
	styles_priority_parameters: StylesPriorityParameters

	@classmethod
	def hierarchization(
		cls,
		effective_structure_from_ooxml: EffectiveStructureFromOoxml,
		styles_priority_parameters: StylesPriorityParameters=DEFAULT_STYLES_PRIORITY_PARAMETERS
	) -> HierarchicalStylesFromOoxml:
		hierarchical_styles_from_ooxml: HierarchicalStylesFromOoxml = cls(
			priority_ordered_styles=[],
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			styles_priority_parameters=styles_priority_parameters
		)
		hierarchical_styles_from_ooxml.compute()

		return hierarchical_styles_from_ooxml

	def compute_priority_difference(self, style: Style, style_priority_representative: Style) -> int:
		"""
		Returns -1 if style has lower priority than the style priority representative
		Returns 0 if style has the same priority as the style priority representative
		Returns 1 if style has higher priority than the style priority representative
		"""

		for priority in self.styles_priority_parameters:
			match priority:
				case AvailableStylePriorityParameters.FONT_SIZE:
					if (
						style.properties.run_style_properties.font_size 
						!= style_priority_representative.properties.run_style_properties.font_size
					):
						if (
							style.properties.run_style_properties.font_size 
							< style_priority_representative.properties.run_style_properties.font_size
						):
							return -1
						
						return 1
				case AvailableStylePriorityParameters.BOLD:
					if (
						style.properties.run_style_properties.bold 
						!= style_priority_representative.properties.run_style_properties.bold
					):
						if (
							not style.properties.run_style_properties.bold
							and style_priority_representative.properties.run_style_properties.bold
						):
							return -1
						
						return 1
				case AvailableStylePriorityParameters.INDENTATION:
					# TODO: How to take into account first line indentation
					if (
						style.properties.paragraph_style_properties.indentation.start 
						!= style_priority_representative.properties.paragraph_style_properties.indentation.start
					):
						if (
							style.properties.paragraph_style_properties.indentation.start 
							> style_priority_representative.properties.paragraph_style_properties.indentation.start
						):
							return -1
						
						return 1
		
		return 0
	
	def compute(self) -> None:
		for effective_style in self.effective_structure_from_ooxml.styles.effective_styles.values():
			if len(self.priority_ordered_styles) == 0:
				self.priority_ordered_styles.append([effective_style])
			else:
				for i, priority in enumerate(self.priority_ordered_styles):
					priority_difference: int = self.compute_priority_difference(
						style=effective_style, style_priority_representative=priority[0]
					)

					match priority_difference:
						case -1:
							# Continue searching for equal or lower priority (if possible)
							if i == len(self.priority_ordered_styles) - 1:
								self.priority_ordered_styles.append([effective_style])
						case 0:
							# Insert style into the current priority level (and stop search)
							priority.append(effective_style)
							break
						case 1:
							# Insert style one priority level above of the current priority level (and stop search)
							self.priority_ordered_styles.insert(i, [effective_style])
							break
	