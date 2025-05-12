from __future__ import annotations
from typing import Optional
from enum import Enum

from utils.pydantic import ArbitraryBaseModel

from rich.tree import Tree
from utils.printing import rich_tree_to_str

from ooxml_docx.ooxml import OoxmlElement
from ooxml_docx.relationships import OoxmlRelationships
from ooxml_docx.structure.properties import ParagraphProperties, NumberingProperties
from ooxml_docx.structure.styles import ParagraphStyle, OoxmlStyles, OoxmlStyleTypes
from ooxml_docx.structure.numberings import NumberingStyle, Numbering, OoxmlNumberings
from ooxml_docx.document.run import Run


class OoxmlHyperlinkType(Enum):
	INTERNAL = "internal"
	EXTERNAL = "external"


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
			type=target_type,
			target=cls._parse_target(ooxml_hyperlink=ooxml_hyperlink, type=target_type, relationships=relationships)
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
			return OoxmlHyperlinkType.EXTERNAL
		
		anchor_id: Optional[str] = ooxml_hyperlink.xpath_query(query="./@w:anchor", singleton=True)
		if anchor_id is not None:
			return OoxmlHyperlinkType.INTERNAL

		raise ValueError("Undefined hyperlink type, cannot find target id reference.")

	@staticmethod
	def _parse_target(
		ooxml_hyperlink: OoxmlElement, type: OoxmlHyperlinkType, relationships: OoxmlRelationships
	) -> Optional[str | Bookmark]:
		"""_summary_

		:param ooxml_hyperlink: _description_
		:return: _description_
		"""
		if type == OoxmlHyperlinkType.EXTERNAL:
			relationship_id: str = str(ooxml_hyperlink.xpath_query(query="./@r:id", nullable=False, singleton=True))
			return relationships.content[relationship_id].target
		elif type == OoxmlHyperlinkType.INTERNAL:
			return None

	def __str__(self) -> str:
		return rich_tree_to_str(self._tree_str_())
	
	def _tree_str_(self) -> Tree:
		tree = Tree("hyperlink")
		return tree


class Paragraph(OoxmlElement):
	content: list[Run | Hyperlink] = []
	
	properties: Optional[ParagraphProperties] = None
	style: Optional[ParagraphStyle | NumberingStyle] = None
	
	numbering: Optional[Numbering] = None
	indentation_level: Optional[int] = None

	@classmethod
	def parse(
			cls, 
			ooxml_paragraph: OoxmlElement, 
			styles: OoxmlStyles, 
			numberings: OoxmlNumberings, 
			relationships: OoxmlRelationships
		) -> Paragraph:
		"""_summary_

		:param ooxml_paragraph: _description_
		:return: _description_
		"""
		properties: Optional[OoxmlElement] = ooxml_paragraph.xpath_query(query="./w:pPr", singleton=True)
		style: Optional[ParagraphStyle | NumberingStyle] = cls._parse_style(ooxml_paragraph=ooxml_paragraph, styles=styles)

		numbering_parse_result: Optional[tuple[Numbering, int]] = cls._parse_numbering(
			ooxml_paragraph=ooxml_paragraph,
			style=style,  
			numberings=numberings
		)

		return cls(
			element=ooxml_paragraph.element,
			content=cls._parse_content(ooxml_paragraph=ooxml_paragraph, styles=styles, relationships=relationships),
			properties=ParagraphProperties(ooxml=properties) if properties is not None else None,
			style=style,
			numbering=numbering_parse_result[0] if numbering_parse_result is not None else None,
			indentation_level=numbering_parse_result[1] if numbering_parse_result is not None else None
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
		ooxml_content: Optional[list[OoxmlElement]] = ooxml_paragraph.xpath_query(
			query="./*[not(self::w:pPr or self::w:bookmarkStart or self::w:bookmarkEnd)]"
		)
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
					# ! TODO: remove continue
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

		# TODO: What happens if an external program adds a style reference that does not exist?
		# TODO: Research by replicating this, if the word program accepts it as valid ooxml then so should I
		raise ValueError(f"Undefined style reference for style id: {style_id}")
	
	@staticmethod
	def _parse_numbering(
			ooxml_paragraph: OoxmlElement, style: Optional[NumberingStyle], numberings: OoxmlNumberings
		) -> Optional[tuple[Numbering, int]]:
		ooxml_numbering: Optional[NumberingProperties] = ooxml_paragraph.xpath_query(
			query="./w:pPr/w:numPr", singleton=True
		)

		# Case: Direct numbering properties
		# Direct formatting of numbering properties always overrides any numbering style
		if ooxml_numbering is not None:
			numbering_id: int = int(ooxml_numbering.xpath_query(query="./w:numId/@w:val", nullable=False, singleton=True))
			numbering: Optional[Numbering] = numberings.find(id=numbering_id)
			
			if numbering is None:
				# In some cases (because of ooxml manipulation from external programs),
				#  there is a numbering reference to an inexistent numbering instance.
				# They are harmless and will be corrected in the abstract_docx normalization step.
				# Raises a warning instead of an error and proceeds.
				print(f"\033[33m[Warning] Inexistent numbering referenced: {numbering_id=}\033[0m")
				return None				

			indentation_level: Optional[int] = ooxml_numbering.xpath_query(query="./w:ilvl/@w:val", singleton=True)
			if indentation_level is None:
				# Defaults to the lowest one specified inside the numbering definition
				indentation_level = 0  # TODO: check if this can be anything besides 0
				print(f"\033[33m[Warning] Lowest indentation level assumption for a paragraph.\033[0m")
			indentation_level = int(indentation_level)

			return numbering, indentation_level
		
		# TODO: Think about if this is necessary, or will it always be better to check numbering through style?
		# TODO: if the latter is decided, need to check the processes that treat numbering afterwards (mainly abstract_docx normalization)
		# Case: Numbering properties via numbering style or paragraph style
		if style is not None and style.numbering is not None:
			return style.numbering, style.indentation_level

		return None

	def __str__(self) -> str:
		return rich_tree_to_str(self._tree_str_())

	def _tree_str_(self) -> Tree:
		tree = Tree("[bold]Paragraph[/bold]")

		if self.style is not None:
			tree.add(f"[bold]Style[/bold]: '{self.style.id}'")
		
		if self.numbering is not None:
			tree.add(f"[bold]Numbering[/bold]: '{self.numbering.id}'")
		if self.indentation_level is not None:
			tree.add(f"[bold]Indentation level[/bold]: '{self.indentation_level}'")

		if len(self.content) != 0:
			content_tree = tree.add("[bold cyan]Content[/bold cyan]")
			for i, content in enumerate(self.content):
				content_tree.add(content._tree_str_())

		return tree