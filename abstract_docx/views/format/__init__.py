from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import Style
from abstract_docx.views.format.numberings import Numbering, Level


class Format(ArbitraryBaseModel):
	style: Style
	numbering: Optional[Numbering] = None
	level: Optional[Level] = None


StylesView = dict[int, dict[str, Style]] 

class FormatsView(ArbitraryBaseModel):
	styles: StylesView
	numberings: dict[int, Numbering]