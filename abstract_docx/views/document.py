from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format import Format


class Text(ArbitraryBaseModel):
	text: str
	# TODO: Text (run formatting)


class Block(ArbitraryBaseModel):
	id: int
	format: Format

	parent: Optional[Block] = None
	children: Optional[list[Block]] = None


class Paragraph(Block):
	text: list[Text]