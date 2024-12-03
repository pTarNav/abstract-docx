from __future__ import annotations
from typing import Optional
from enum import Enum
from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from ooxml_docx.relationships import OoxmlRelationships
from ooxml_docx.structure.properties import (
	RunProperties, ParagraphProperties, 
	TableProperties, TableConditionalProperties, TableRowProperties, TableCellProperties,
	NumberingProperties
)
from ooxml_docx.structure.styles import RunStyle, ParagraphStyle, TableStyle, OoxmlStyles, OoxmlStyleTypes
from ooxml_docx.structure.numberings import NumberingStyle, Numbering


class RunContent(OoxmlElement):
	text: str

	def __str__(self) -> str:
		return self.text


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
	content: list[RunContent] = []
	
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
	def _parse_content(ooxml_run: OoxmlElement) -> list[RunContent]:
		"""_summary_

		:param ooxml_run: _description_
		:return: _description_
		"""
		ooxml_content: Optional[list[OoxmlElement]] = ooxml_run.xpath_query(query="./*[not(self::w:rPr)]")
		if ooxml_content is None:
			return []
		
		content: list[RunContent] = []
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
		return self._tree_str_()
	
	def _tree_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		"""
		Computes string representation of a paragraph.

		:param depth: Indentation depth integer, defaults to 0.
		:param last: Paragraph is the last one from the parent element list, defaults to False.
		:param line_state: List of booleans indicating whether to include vertical connection for each previous indentation depth,
		 defaults to None to avoid mutable list initialization unexpected behavior.
		:return: Package string representation.
		"""
		if line_state is None:
			line_state = []
		
		# Compute string representation of package header
		prefix = " " if depth > 0 else ""
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)
		
		s = f"{arrow}"
		if self.style is not None:
			s += f" [\033[1m{self.style.id}\033[0m]"
		s += f" {''.join([repr(element.__str__()) for element in self.content])}\n"

		# Update the line state for the current depth
		if depth > 0:
			if depth >= len(line_state):
				line_state.append(not last)
			else:
				line_state[depth] = not last
		
		if len(self.content) > 1:
			# Compute string representation of content
			prefix = " "
			for level_state in line_state:
				prefix += "\u2502    " if level_state else "     "
			for i, element in enumerate(self.content):
				arrow = prefix + "\u2514\u2500\u2500\u25BA" if i == len(self.content)-1 else "\u251c\u2500\u2500\u25BA"
				s += f"{arrow} {repr(element.__str__())}\n"

		return s


class OoxmlHyperlinkType(Enum):
	internal = "INTERNAL"
	external = "EXTERNAL"


class BookmarkDelimiter(ArbitraryBaseModel):
	parent: Optional[OoxmlElement] = None
	previous: Optional[OoxmlElement] = None


class Bookmark(OoxmlElement):
	id: int  # Id is just used to relate <w:bookmarkStart> and <w:bookmarkEnd> elements
	name: str  # Actual id used to reference the bookmark, contained in <w:bookmarkStart>
	
	start_delimiter: Optional[BookmarkDelimiter] = None
	# Empty while the <w:bookmarkEnd> element has not been found yet, should not remain empty after the document is parsed
	end_delimiter: Optional[BookmarkDelimiter] = None

	@classmethod
	def start(cls, ooxml_bookmark_start: OoxmlElement) -> Bookmark:
		"""_summary_

		:param ooxml_bookmark_start: _description_
		:return: _description_
		"""
		return cls(
			element=ooxml_bookmark_start.element,
			id=int(ooxml_bookmark_start.xpath_query(query="./@w:id", nullable=False, singleton=True)),
			name=str(ooxml_bookmark_start.xpath_query(query="./@w:name", nullable=False, singleton=True))
		)
	
	@classmethod
	def end(cls, ooxml_bookmark_end: OoxmlElement) -> int:
		"""_summary_

		:param ooxml_bookmark_end: _description_
		:return: _description_
		"""
		return int(ooxml_bookmark_end.xpath_query(query="./@w:id", nullable=False, singleton=True))


class Hyperlink(OoxmlElement):
	content: list[Run] = []
	type: OoxmlHyperlinkType

	#  
	target: Optional[str | Bookmark] = None

	@classmethod
	def parse(cls, ooxml_hyperlink: OoxmlElement, styles: OoxmlStyles, relationships: OoxmlRelationships) -> Hyperlink:
		"""_summary_

		:param ooxml_hyperlink: _description_
		:return: _description_
		"""
		target_type: OoxmlHyperlinkType = cls._parse_type(ooxml_hyperlink=ooxml_hyperlink)

		return cls(
			element=ooxml_hyperlink.element,
			content=cls._parse_content(ooxml_hyperlink=ooxml_hyperlink, styles=styles),
			type=target_type
		)
	
	@staticmethod
	def _parse_content(ooxml_hyperlink: OoxmlElement, styles: OoxmlStyles) -> list[Run]:
		"""_summary_

		:param ooxml_hyperlink: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		ooxml_runs: Optional[list[OoxmlElement]] = ooxml_hyperlink.xpath_query(query="./w:r")
		if ooxml_runs is None:
			return []
		
		content: list[Run] = []
		for ooxml_run in ooxml_runs:
			content.append(Run.parse(ooxml_run=ooxml_run, styles=styles))
		
		return content

	@staticmethod
	def _parse_type(ooxml_hyperlink: OoxmlElement) -> OoxmlHyperlinkType:
		"""_summary_

		:param ooxml_hyperlink: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		relationship_id: Optional[str] = ooxml_hyperlink.xpath_query(query="./@r:id", singleton=True)
		if relationship_id is not None:
			return OoxmlHyperlinkType.external
		
		anchor_id: Optional[str] = ooxml_hyperlink.xpath_query(query="./@w:anchor", singleton=True)
		if anchor_id is not None:
			return OoxmlHyperlinkType.internal

		raise ValueError("Undefined hyperlink type, cannot find target id reference")

	@staticmethod
	def _parse_target(
		ooxml_hyperlink: OoxmlElement, type: OoxmlHyperlinkType, relationships: OoxmlRelationships
	) -> Optional[str | Bookmark]:
		"""_summary_

		:param ooxml_hyperlink: _description_
		:return: _description_
		"""
		if type == OoxmlHyperlinkType.external:
			relationship_id: str = str(ooxml_hyperlink.xpath_query(query="./@r:id", nullable=False, singleton=True))
			return relationships.content[relationship_id].target
		elif type == OoxmlHyperlinkType.internal:
			return None

	def _tree_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		return "hyperlink"

class Paragraph(OoxmlElement):
	content: list[Run | Hyperlink] = []
	
	properties: Optional[ParagraphProperties] = None
	style: Optional[ParagraphStyle | NumberingStyle] = None
	numbering: Optional[Numbering] = None

	@classmethod
	def parse(cls, ooxml_paragraph: OoxmlElement, styles: OoxmlStyles, relationships: OoxmlRelationships) -> Paragraph:
		"""_summary_

		:param ooxml_paragraph: _description_
		:return: _description_
		"""
		properties: Optional[ParagraphProperties] = ooxml_paragraph.xpath_query(query="./pPr", singleton=True)

		return cls(
			element=ooxml_paragraph.element,
			content=cls._parse_content(ooxml_paragraph=ooxml_paragraph, styles=styles, relationships=relationships),
			properties=ParagraphProperties(ooxml=properties) if properties is not None else None,
			style=cls._parse_style(ooxml_paragraph=ooxml_paragraph, styles=styles)
		)

	@staticmethod
	def _parse_content(
		ooxml_paragraph: OoxmlElement, styles: OoxmlStyles, relationships: OoxmlRelationships
	) -> list[Run | Hyperlink]:
		"""_summary_

		:param ooxml_paragraph: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		ooxml_content: Optional[list[OoxmlElement]] = ooxml_paragraph.xpath_query(query="./*[not(self::w:pPr or self::w:bookmarkStart or self::w:bookmarkEnd)]")
		if ooxml_content is None:
			return []
		
		content: list[Run | Hyperlink] = []
		for ooxml_element in ooxml_content:
			match ooxml_element.local_name:
				case "r":
					element: Run = Run.parse(ooxml_run=ooxml_element, styles=styles)
				case "hyperlink":
					element: Hyperlink = Hyperlink.parse(
						ooxml_hyperlink=ooxml_element, styles=styles, relationships=relationships
					)
				case _:
					continue
					raise ValueError(f"Unexpected OOXML element: <w:{ooxml_element.local_name}>")
			content.append(element)
		
		return content

	@staticmethod
	def _parse_style(ooxml_paragraph: OoxmlElement, styles: OoxmlStyles) -> Optional[ParagraphStyle | NumberingStyle]:
		"""_summary_

		:param ooxml_paragraph: _description_
		:param styles: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		style_id: Optional[str] = ooxml_paragraph.xpath_query(query="./w:pPr/w:pStyle/@w:val", singleton=True)
		if style_id is None:
			return None
		style_id = str(style_id)

		paragraph_style_search_result: Optional[ParagraphStyle] = styles.find(id=style_id, type=OoxmlStyleTypes.PARAGRAPH)
		if paragraph_style_search_result is not None:
			return paragraph_style_search_result
		
		numbering_style_search_result: Optional[NumberingStyle] = styles.find(id=style_id, type=OoxmlStyleTypes.NUMBERING)
		if numbering_style_search_result is not None:
			return numbering_style_search_result

		raise ValueError(f"Undefined style reference for style id: {style_id}")

	def __str__(self) -> str:
		return self._tree_str_()

	def _tree_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		"""
		Computes string representation of a paragraph.

		:param depth: Indentation depth integer, defaults to 0.
		:param last: Paragraph is the last one from the parent element list, defaults to False.
		:param line_state: List of booleans indicating whether to include vertical connection for each previous indentation depth,
		 defaults to None to avoid mutable list initialization unexpected behavior.
		:return: Package string representation.
		"""
		if line_state is None:
			line_state = []
		
		# Compute string representation of package header
		prefix = " " if depth > 0 else ""
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)

		s = f"{arrow}"
		if self.style is not None:
			s += f" [\033[1m{self.style.id}\033[0m]"
		s += " '"
		for element in self.content:
			s += "".join([_element.__str__() for _element in element.content])
		s += "'\n"

		# Update the line state for the current depth
		if depth > 0:
			if depth >= len(line_state):
				line_state.append(not last)
			else:
				line_state[depth] = not last

		# Compute string representation of content
		for i, element in enumerate(self.content):
			s += element._tree_str_(
				depth=depth+1, last=i==len(self.content)-1, line_state=line_state[:]  # Pass-by-value
			)

		return s

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
	
	def __str__(self) -> str:
		return ""
	
	def _tree_str_(self, depth: int, last: bool) -> str:
		return ""


class OoxmlDocument(OoxmlElement):
	body: list[Paragraph | Table] = []

	@classmethod
	def build(cls, ooxml_document_part: OoxmlPart, styles: OoxmlStyles, relationships: OoxmlRelationships) -> OoxmlDocument:
		"""_summary_

		:param ooxml_document_part: _description_
		:return: _description_
		"""

		return cls(
			element=ooxml_document_part.ooxml.element,
			body=cls._parse_body(ooxml_document_part=ooxml_document_part, styles=styles, relationships=relationships)
		)
	
	@staticmethod
	def _parse_body(ooxml_document_part: OoxmlPart, styles: OoxmlStyles, relationships: OoxmlRelationships) -> list[Paragraph | Table]:
		"""_summary_

		:param ooxml_document_part: _description_
		:return: _description_
		"""
		ooxml_body: Optional[OoxmlElement] = ooxml_document_part.ooxml.xpath_query(query="./w:body", singleton=True)
		if ooxml_body is None:
			return []

		ooxml_content: Optional[list[OoxmlElement]] = ooxml_body.xpath_query(query="./*[not(self::w:bookmarkStart or self::w:bookmarkEnd)]")
		if ooxml_content is None:
			return []

		content: list[Paragraph | Table] = []
		for ooxml_element in ooxml_content:
			match ooxml_element.local_name:
				case "p":
					element: Paragraph = Paragraph.parse(ooxml_paragraph=ooxml_element, styles=styles, relationships=relationships)
				case "tbl":
					element: Table = Table.parse(ooxml_table=ooxml_element)
				case _:
					continue
					raise ValueError(f"Unexpected OOXML element: <w:{ooxml_element.local_name}>")
			content.append(element)
			
		return content

	def __str__(self) -> str:
		s = "\033[36m\033[1mBody\033[0m\n"
		for i, element in enumerate(self.body):
			s += element._tree_str_(depth=1, last=i==len(self.body)-1)
		
		return s

