from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format import Format
from abstract_docx.views.format.styles import Style

import ooxml_docx.document.run as OOXML_RUN

class Block(ArbitraryBaseModel):
	id: int
	format: Optional[Format] = None  # Only the root block of the document will have empty format

	parent: Optional[Block] = None
	children: Optional[list[Block]] = None

	# TODO: put level indexes inside index
	level_indexes: Optional[dict[int, int]] = None

# TODO: change Text for Run
class Text(ArbitraryBaseModel):
	text: str
	style: Style

	@classmethod
	def from_ooxml(cls, ooxml_run: OOXML_RUN.Run, style: Style) -> Text:
		return cls(
			text="".join([run_content.text for run_content in ooxml_run.content]),
			style=style
		)
	
	def concat(self, other: Text) -> None:
		if self.style != other.style:
			raise ValueError("Cannot concatenate two Texts that do not share the same style properties.")

		self.text += other.text


class Run(Text):
	pass


class Hyperlink(Text):
	target: str


class Paragraph(Block):
	content: list[Text]

	def __str__(self):
		return "".join([content.text for content in self.content])


class CellMergeRange(ArbitraryBaseModel):
	start_row_loc: int
	start_column_loc: int
	row_span: int
	column_span: int


class Cell(ArbitraryBaseModel):
	loc: tuple[int, int]
	blocks: list[Block]

	def __str__(self):
		return " ".join([str(block) for block in self.blocks])  # TODO: it will fail for nested tables but cannot be bothered for now

class Row(ArbitraryBaseModel):
	loc: int
	cells: list[Cell]


class Table(Block):
	rows: list[Row]
	cell_merge_ranges: Optional[list[CellMergeRange]] = None
	caption: Optional[Paragraph] = None

	def __str__(self):
		s: str = ""
		for row in self.rows:
			s += f"| {' | '.join([str(cell).strip() for cell in row.cells])} |@NEWLINE@"
			
		return s

class DocumentView(ArbitraryBaseModel):
	blocks: dict[int, Block]
	root: Block

	@classmethod
	def load(cls, blocks: dict[int, Block], root: Block) -> DocumentView:
		return cls(blocks=blocks, root=root)