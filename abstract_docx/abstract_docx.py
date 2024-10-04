from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Literal


class Block(BaseModel):
	id: str
	parent: Optional[Block] = None
	children: Optional[list[Block]] = None


class Text(BaseModel):
	content: str


class Hyperlink(BaseModel):
	text: list[Text]
	url: str | Block


class Paragraph(Block):
	content: list[Text | Hyperlink]	


class Item(Block):
	parent: Numbering  # Override Block parent to force numbering structure
	
	numbering_id: str


class Numbering(Block):
	children: list[Item]  # Override Block children to force items structure


class Cell(Block):
	parent: Table  # Override Block parent to force table structure

	row_id: int
	col_id: int


class Table(Block):
	children: list[list[Cell]]  # Override Block children to force cells structure
