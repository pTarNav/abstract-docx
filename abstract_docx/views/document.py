from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format import Format
from abstract_docx.views.format.styles import Style

import ooxml_docx.document.run as OOXML_RUN

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


class Block(ArbitraryBaseModel):
	id: int
	format: Optional[Format] = None  # Only the root block of the document will have empty format

	parent: Optional[Block] = None
	children: Optional[list[Block]] = None


class Paragraph(Block):
	content: list[Text]

	def __str__(self):
		return "".join([content.text for content in self.content])
	