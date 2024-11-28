from __future__ import annotations
from typing import Optional
from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from ooxml_docx.structure.properties import rPr, pPr, tblPr, trPr, tcPr

class Run(OoxmlElement):
	text: str
	properties: Optional[rPr] = None


class Hyperlink(OoxmlElement):
	miau: str


class Paragraph(OoxmlElement):
	content: list[Run | Hyperlink] = []
	properties: Optional[pPr] = None

	@classmethod
	def parse(cls, ooxml_paragraph: OoxmlElement) -> Paragraph:
		"""_summary_

		:param ooxml_paragraph: _description_
		:return: _description_
		"""
		return cls(element=ooxml_paragraph.element)


class TableCell(OoxmlElement):
	content: list[Paragraph | Table] = []
	properties: Optional[tcPr] = None


class TableRow(OoxmlElement):
	cells: list[TableCell]
	properties: Optional[trPr] = None


class Table(OoxmlElement):
	rows: list[TableRow] = []
	properties: Optional[tblPr] = None

	@classmethod
	def parse(cls, ooxml_table: OoxmlElement) -> Table:
		"""_summary_

		:param ooxml_table: _description_
		:return: _description_
		"""
		return cls(element=ooxml_table.element)


class OoxmlDocument(OoxmlElement):
	body: list[Paragraph | Table] = []

	@classmethod
	def build(cls, ooxml_document_part: OoxmlPart) -> OoxmlDocument:
		"""_summary_

		:param ooxml_document_part: _description_
		:return: _description_
		"""
		
		return cls(
			element=ooxml_document_part.ooxml.element,
			body=cls._parse_body(ooxml_document_part=ooxml_document_part)
		)
	
	@staticmethod
	def _parse_body(ooxml_document_part: OoxmlPart) -> list[Paragraph | Table]:
		"""_summary_

		:param ooxml_document_part: _description_
		:return: _description_
		"""
		ooxml_body: Optional[OoxmlElement] = ooxml_document_part.ooxml.xpath_query(query="./w:body", singleton=True)
		if ooxml_body is None:
			return []

		content: list[Paragraph | Table] = []
		ooxml_content: Optional[OoxmlElement] = ooxml_body.xpath_query(query="./w:p | ./w:tbl")
		if ooxml_content is not None:
			for ooxml_element in ooxml_content:
				match ooxml_element.local_name:
					case "p":
						element: Paragraph = Paragraph.parse(ooxml_paragraph=ooxml_element)
					case "tbl":
						element: Table = Table.parse(ooxml_table=ooxml_element)
					case _:
						raise ValueError("")  # TODO
				content.append(element)
				
		return content
		


