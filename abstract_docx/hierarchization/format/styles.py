from enum import Enum

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import Style
from abstract_docx.views.format import StylesView
from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml

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

def compute_priority_difference(styles_priority_parameters: StylesPriorityParameters, style: Style, priority_level_representative: Style) -> int:
	"""
	Returns -1 if style has lower priority than the priority level representative
	Returns 0 if style has the same priority as the priority level representative
	Returns 1 if style has higher priority than the priority level representative
	"""
	
	for priority in styles_priority_parameters:
		match priority:
			case AvailableStylePriorityParameters.FONT_SIZE:
				if style.properties.run_style_properties.font_size != priority_level_representative.properties.run_style_properties.font_size:
					if style.properties.run_style_properties.font_size < priority_level_representative.properties.run_style_properties.font_size:
						return -1
					else:
						return 1
			case AvailableStylePriorityParameters.BOLD:
				if style.properties.run_style_properties.bold != priority_level_representative.properties.run_style_properties.bold:
					if not style.properties.run_style_properties.bold and priority_level_representative.properties.run_style_properties.bold:
						return -1
					else:
						return 1
			case AvailableStylePriorityParameters.INDENTATION:
				# TODO: How to take into account first line indentation
				if style.properties.paragraph_style_properties.indentation.start != priority_level_representative.properties.paragraph_style_properties.indentation.start:
					if style.properties.paragraph_style_properties.indentation.start > priority_level_representative.properties.paragraph_style_properties.indentation.start:
						return -1
					else:
						return 1
	return 0
				

def styles_hierarchization(effective_styles: EffectiveStylesFromOoxml) -> StylesView:
	priorities = [AvailableStylePriorityParameters.FONT_SIZE, AvailableStylePriorityParameters.BOLD, AvailableStylePriorityParameters.INDENTATION]
	styles_priority_parameters: StylesPriorityParameters = StylesPriorityParameters.load(priorities=priorities)

	ordered_styles: list[list[Style]] = []

	for effective_style in effective_styles.values():
		if len(ordered_styles) == 0:
			ordered_styles.append([effective_style])
		else:
			for i, priority_level in enumerate(ordered_styles):
				priority_difference: int = compute_priority_difference(
					styles_priority_parameters=styles_priority_parameters,
					style=effective_style,
					priority_level_representative=priority_level[0]
				)
				match priority_difference:
					case -1:
						# Continue searching for equal or lower priority level (if possible)
						if i == len(ordered_styles) - 1:
							ordered_styles.append([effective_style])
					case 0:
						# Insert style into the current priority level (and stop search)
						priority_level.append(effective_style)
						break
					case 1:
						# Insert style one priority level above of the current priority level (and stop search)
						ordered_styles.insert(i, [effective_style])
						break
	
	return StylesView.load(styles=effective_styles, ordered_styles=ordered_styles)

	