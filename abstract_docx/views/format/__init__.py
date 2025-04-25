from __future__ import annotations

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import Style
from abstract_docx.views.format.numberings import Numbering


class Format(ArbitraryBaseModel):
	style: Style
	numbering: Numbering