from __future__ import annotations
from typing import Optional

from abstract_docx.utils.pydantic import ArbitraryBaseModel

from abstract_docx.core.data_models.styles import Style
from abstract_docx.core.data_models.numberings import Index

import abstract_docx.ooxml_docx.document.run as OOXML_RUN


class Format(ArbitraryBaseModel):
	style: Style
	index: Optional[Index] = None


class Block(ArbitraryBaseModel):
	id: int
	format: Optional[Format] = None  # Only the root block of the document will have empty format

	parent: Optional[Block] = None
	children: Optional[list[Block]] = None

	# TODO: put level indexes inside index
	level_indexes: Optional[dict[int, int]] = None


class Run(ArbitraryBaseModel):
	text: str
	style: Style

	@classmethod
	def from_ooxml(cls, ooxml_run: OOXML_RUN.Run, style: Style) -> Run:
		return cls(
			text="".join([run_content.text for run_content in ooxml_run.content]),
			style=style
		)
	
	def concat(self, other: Run) -> None:
		if self.style != other.style:
			raise ValueError("Cannot concatenate two Runs that do not share the same style properties.")

		self.text += other.text


class Hyperlink(ArbitraryBaseModel):
	content: list[Run]
	target: Optional[str] = None
	style: Style
	
	@property
	def text(self) -> str:
		return "".join(run.text for run in self.content)


PARAGRAPH_CONTENT = list[Run | Hyperlink]

class Paragraph(Block):
	content: PARAGRAPH_CONTENT

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