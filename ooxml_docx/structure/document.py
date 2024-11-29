from __future__ import annotations
from typing import Optional
from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from ooxml_docx.structure.properties import RunProperties, ParagraphProperties, TableProperties, TableRowProperties, TableCellProperties
from ooxml_docx.structure.styles import RunStyle, ParagraphStyle, TableStyle, OoxmlStyles, OoxmlStyleTypes


class RunContent(OoxmlElement):
	text: str


SPECIAL_RUN_TEXT_TAGS: list[str] = ["br", "cr", "sym", "tab", "noBreakHyphen", "softHyphen"]


class SpecialRunText(RunContent):

	@classmethod
	def parse(cls, ooxml_special_text: OoxmlElement) -> SpecialRunText:
		"""_summary_

		:param ooxml_special_text: _description_
		:return: _description_
		"""
		return cls(
			element=ooxml_special_text.element,
			text=cls._compute_representation(ooxml_special_text=ooxml_special_text)
		)

	@staticmethod
	def _compute_representation(ooxml_special_text: OoxmlElement) -> str:
		"""_summary_

		:param ooxml_special_text: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		match ooxml_special_text.local_name:
			case "br":
				return "\n"
			case "cr":
				return "\r\n"
			case "sym":
				# Parse the character attribute (hexadecimal to integer)
				# Checking if the value is in the private use area (starts with "F"), shifting it in that case
				char: str = str(ooxml_special_text.xpath_query(query="./@w:char", nullable=False, singleton=True))
				return chr(int(char, 16) - 0xF000 if char.startswith("F") else int(char, 16))
			case "tab":
				return "\t"
			case "noBreakHyphen":
				return "\u2011"
			case "softHyphen":
				return "\u00AD"
			case _:
				raise ValueError(f"No representation string for special run content: <w:{ooxml_special_text.local_name}>")


class RunText(RunContent):

	@classmethod
	def parse(cls, ooxml_text: OoxmlElement) -> RunText:
		"""_summary_

		:param ooxml_text: _description_
		:return: _description_
		"""
		return cls(element=ooxml_text.element,text=str(ooxml_text.element.text))


class Run(OoxmlElement):
	content: list[RunText | SpecialRunText]
	
	properties: Optional[RunProperties] = None
	style: Optional[RunStyle] = None

	@classmethod
	def parse(cls, ooxml_run: OoxmlElement, styles: OoxmlStyles) -> Run:
		"""_summary_

		:param ooxml_run: _description_
		:return: _description_
		"""
		properties: Optional[RunProperties] = ooxml_run.xpath_query(query="./rPr", singleton=True)

		return cls(
			element=ooxml_run.element,
			content=cls._parse_content(ooxml_run=ooxml_run),
			properties=RunProperties(ooxml=properties) if properties is not None else None,
			style=cls._parse_style(ooxml_run=ooxml_run, styles=styles)
		)

	@staticmethod
	def _parse_content(ooxml_run: OoxmlElement) -> list[RunText | SpecialRunText]:
		"""_summary_

		:param ooxml_run: _description_
		:return: _description_
		"""
		ooxml_content: Optional[list[OoxmlElement]] = ooxml_run.xpath_query(query="./*[not(self::w:rPr)]")
		if ooxml_content is None:
			return []
		
		content: list[RunText | SpecialRunText] = []
		for ooxml_element in ooxml_content:
			if ooxml_element.local_name == "t":
				element: RunText = RunText.parse(ooxml_text=ooxml_element)
			elif ooxml_element.local_name in SPECIAL_RUN_TEXT_TAGS:
				element: SpecialRunText = SpecialRunText.parse(ooxml_special_text=ooxml_element)
			else:
				print("found strange run content", ooxml_element.local_name)
				continue
			content.append(element)

		return content

	@staticmethod
	def _parse_style(ooxml_run: OoxmlElement, styles: OoxmlStyles) -> Optional[RunStyle]:
		"""_summary_

		:param ooxml_run: _description_
		:param styles: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		style_id: Optional[str] = ooxml_run.xpath_query(query="./w:rPr/w:rStyle/@w:val", singleton=True)
		if style_id is None:
			return None
		style_id = str(style_id)

		run_style_search_result: Optional[RunStyle] = styles.find(id=style_id, type=OoxmlStyleTypes.RUN)
		if run_style_search_result is not None:
			return run_style_search_result

		raise ValueError("")  # TODO
	
	def __str__(self) -> str:
		return f"{{[{', '.join([repr(element.text) for element in self.content])}], }}"

class Hyperlink(OoxmlElement):
	miau: str


class Paragraph(OoxmlElement):
	content: list[Run | Hyperlink] = []
	
	properties: Optional[ParagraphProperties] = None
	style: Optional[ParagraphStyle] = None

	@classmethod
	def parse(cls, ooxml_paragraph: OoxmlElement, styles: OoxmlStyles) -> Paragraph:
		"""_summary_

		:param ooxml_paragraph: _description_
		:return: _description_
		"""
		return cls(
			element=ooxml_paragraph.element,
			content=cls._parse_content(ooxml_paragraph=ooxml_paragraph, styles=styles)
		)

	@staticmethod
	def _parse_content(ooxml_paragraph: OoxmlElement, styles: OoxmlStyles) -> list[Run | Hyperlink]:
		"""_summary_

		:param ooxml_paragraph: _description_
		:raises ValueError: _description_
		:return: _description_
		"""

		ooxml_content: Optional[list[OoxmlElement]] = ooxml_paragraph.xpath_query(query="./w:r | ./w:hyperlink")
		if ooxml_content is None:
			return []
		
		content: list[Run | Hyperlink] = []
		for ooxml_element in ooxml_content:
			match ooxml_element.local_name:
				case "r":
					element: Run = Run.parse(ooxml_run=ooxml_element, styles=styles)
				case "hyperlink":
					continue
				case _:
					raise ValueError("")  # TODO
			content.append(element)
		
		print(", ".join([element.__str__() for element in content]))
		return content


class TableCell(OoxmlElement):
	content: list[Paragraph | Table] = []
	properties: Optional[TableCellProperties] = None


class TableRow(OoxmlElement):
	cells: list[TableCell]
	properties: Optional[TableRowProperties] = None


class Table(OoxmlElement):
	rows: list[TableRow] = []

	properties: Optional[TableProperties] = None
	style: Optional[TableStyle] = None

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
	def build(cls, ooxml_document_part: OoxmlPart, styles: OoxmlStyles) -> OoxmlDocument:
		"""_summary_

		:param ooxml_document_part: _description_
		:return: _description_
		"""
		
		return cls(
			element=ooxml_document_part.ooxml.element,
			body=cls._parse_body(ooxml_document_part=ooxml_document_part, styles=styles)
		)
	
	@staticmethod
	def _parse_body(ooxml_document_part: OoxmlPart, styles: OoxmlStyles) -> list[Paragraph | Table]:
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
						element: Paragraph = Paragraph.parse(ooxml_paragraph=ooxml_element, styles=styles)
					case "tbl":
						element: Table = Table.parse(ooxml_table=ooxml_element)
					case _:
						raise ValueError("")  # TODO
				content.append(element)
				
		return content
		


