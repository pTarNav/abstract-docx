from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import Style
from abstract_docx.views.format.numberings import Index, Numbering, Enumeration, Level

class Format(ArbitraryBaseModel):
	style: Style
	index: Optional[Index] = None

# TODO: move to styles.py
class StylesView(ArbitraryBaseModel):
	styles: dict[str, Style]
	priority_keys: dict[int, list[str]]

	@classmethod
	def load(cls, styles: dict[str, Style], ordered_styles: list[list[Style]]) -> StylesView:
		return cls(
			styles=styles,
			priority_keys={
				priority_level: [style.id for style in styles_in_priority_level]
				for priority_level, styles_in_priority_level in enumerate(ordered_styles)
			}
		)

	@property
	def priorities(self) -> dict[int, list[Style]]:
		return {level: [self.styles[name] for name in styles_keys] for level, styles_keys in self.priority_keys.items()}


class NumberingsView(ArbitraryBaseModel):
	numberings: dict[int, Numbering]
	enumerations: dict[str, Enumeration]
	levels: dict[str, Level]

	priority_keys: dict[int, list[str]]

	@classmethod
	def load(
		cls, numberings: dict[int, Numbering],
		enumerations: dict[str, Enumeration],
		levels: dict[str, Level],
		ordered_levels: list[list[Level]]
	) -> NumberingsView:
		return cls(
			numberings=numberings,
			enumerations=enumerations,
			levels=levels,
			priority_keys={
				priority_level: [style.id for style in levels_in_priority_level]
				for priority_level, levels_in_priority_level in enumerate(ordered_levels)
			}
		)

	@property
	def priorities(self) -> dict[int, list[Level]]:
		return {level: [self.levels[name] for name in levels_keys] for level, levels_keys in self.priority_keys.items()}

class FormatsView(ArbitraryBaseModel):
	styles: StylesView
	numberings: NumberingsView