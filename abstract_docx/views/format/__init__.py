from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import StylesView, Style
from abstract_docx.views.format.numberings import NumberingsView, Index


class Format(ArbitraryBaseModel):
	style: Style
	index: Optional[Index] = None


class FormatsView(ArbitraryBaseModel):
	styles: StylesView
	numberings: NumberingsView

	@classmethod
	def load(cls) -> FormatsView:
		pass
