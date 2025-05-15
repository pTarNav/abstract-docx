from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import Style
from abstract_docx.views.format.numberings import Numbering, Level


class Format(ArbitraryBaseModel):
	style: Style
	numbering: Optional[Numbering] = None
	level: Optional[Level] = None


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
	

class FormatsView(ArbitraryBaseModel):
	styles: StylesView
	numberings: dict[int, Numbering]