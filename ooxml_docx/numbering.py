from __future__ import annotations
from typing import Optional
from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from ooxml_docx.properties import rPr, pPr
from ooxml_docx.styles import Style, OoxmlStyleTypes, OoxmlStyles, ParagraphStyle, NumberingStyle


class NumberingStyle(NumberingStyle):

	parent_abstract_numbering: Optional[AbstractNumbering] = None
	children_abstract_numbering: Optional[list[AbstractNumbering]] = None


class Level(OoxmlElement):
	"""_summary_

	"""
	id: int
	# Note that abstract numbering is optional in order to facilitate the construction
	# however, it should not be empty and always associated to an abstract numbering definition.
	abstract_numbering: Optional[AbstractNumbering] = None

	properties: Optional[list[OoxmlElement]] = None
	run_properties: Optional[rPr] = None
	paragraph_properties: Optional[pPr] = None
	
	style: Optional[NumberingStyle | ParagraphStyle] = None

	@classmethod
	def parse(cls, ooxml_level: OoxmlElement, styles: OoxmlStyles) -> Level:
		"""_summary_

		:param ooxml_level: _description_
		:return: _description_
		"""
		ooxml_run_properties: Optional[OoxmlElement] = ooxml_level.xpath_query(query="./w:rPr", singleton=True)
		ooxml_paragraph_properties: Optional[OoxmlElement] = ooxml_level.xpath_query(query="./w:pPr", singleton=True)
		
		return cls(
			element=ooxml_level.element,
			id=int(ooxml_level.xpath_query(query="./@w:ilvl", singleton=True, nullable=False)),
			properties=ooxml_level.xpath_query(
				query="./*[not(self::w:name or self::w:pPr or self::w:rPr or self::w:pStyle)]"
			),
			run_properties=rPr(ooxml=ooxml_run_properties) if ooxml_run_properties is not None else None,
			paragraph_properties=pPr(ooxml=ooxml_paragraph_properties) if ooxml_paragraph_properties is not None else None,
			style=cls._parse_style(ooxml_level=ooxml_level, styles=styles)
		)
	
	@staticmethod
	def _parse_style(ooxml_level: OoxmlElement, styles: OoxmlStyles) -> Optional[NumberingStyle | ParagraphStyle]:
		"""_summary_

		:param ooxml_level: _description_
		:param styles: _description_
		:return: _description_
		"""

		style_id: Optional[str] = ooxml_level.xpath_query(query="./w:pStyle/@w:val", singleton=True)
		if style_id is None:
			return None
		style_id = str(style_id)

		numbering_style_search_result: Optional[NumberingStyle] = styles.find(id=style_id, type=OoxmlStyleTypes.NUMBERING)
		if numbering_style_search_result is not None:
			return numbering_style_search_result
		
		return styles.find(id=style_id, type=OoxmlStyleTypes.PARAGRAPH)

	def __str__(self) -> str:
		return f"{self.id}"


class AbstractNumbering(OoxmlElement):
	"""_summary_

	"""
	id: int
	name: Optional[str] = None
	numberings: Optional[list[Numbering]] = None
	levels: dict[int, Level] = {}
	
	style: Optional[NumberingStyle] = None  # numStyleLink
	style_children: Optional[list[NumberingStyle]] = None  # styleLink

	@classmethod
	def parse(cls, ooxml_abstract_numbering: OoxmlElement, styles: OoxmlStyles) -> AbstractNumbering:
		"""_summary_

		:param ooxml_abstract_numbering: _description_
		:return: _description_
		"""
		name: Optional[str] = ooxml_abstract_numbering.xpath_query(query="./w:name/@w:val", singleton=True)
		
		abstract_numbering: AbstractNumbering = cls(
			element=ooxml_abstract_numbering.element,
			id=int(ooxml_abstract_numbering.xpath_query(query="./@w:abstractNumId", singleton=True, nullable=False)),
			name=str(name) if name is not None else None,
			levels=cls._parse_levels(ooxml_abstract_numbering=ooxml_abstract_numbering, styles=styles)
		)
		
		# Associate abstract numbering to each one of its levels
		for level in abstract_numbering.levels.values():
			level.abstract_numbering = abstract_numbering
		
		return abstract_numbering
		
	
	@staticmethod
	def _parse_levels(ooxml_abstract_numbering: OoxmlElement, styles: OoxmlStyles) -> dict[int, Level]:
		"""_summary_

		:param ooxml_abstract_numbering: _description_
		:return: _description_
		"""
		ooxml_levels: list[OoxmlElement] = ooxml_abstract_numbering.xpath_query(query="./w:lvl")
		if ooxml_levels is None:
			return {}
		
		levels: dict[int, Level] = {}
		for ooxml_level in ooxml_levels:
			level: Level = Level.parse(ooxml_level=ooxml_level, styles=styles)
			levels[level.id] = level
		
		return levels

	def __str__(self) -> str:
		s = f"\033[1m{self.id}\033[0m: '{self.name if self.name is not None else ''}'"
		s += f" [{','.join([level.__str__() for level in self.levels])}]\n"

		return s


class Numbering(OoxmlElement):
	"""
	"""
	id: int
	abstract_numbering: AbstractNumbering


class OoxmlNumbering(ArbitraryBaseModel):
	abstract_numberings: list[AbstractNumbering] = []
	numberings: list[Numbering] = []

	@classmethod
	def build(cls, ooxml_numbering_part: OoxmlPart, styles: OoxmlStyles) -> OoxmlNumbering:
		"""_summary_

		:return: _description_
		"""
		return cls(
			abstract_numberings=cls._parse_abstract_numberings(ooxml_numbering_part=ooxml_numbering_part, styles=styles),
			numberings=cls._parse_numberings(ooxml_numbering_part=ooxml_numbering_part)
		)
	
	@staticmethod
	def _parse_abstract_numberings(ooxml_numbering_part: OoxmlPart, styles: OoxmlStyles) -> list[AbstractNumbering]:
		"""_summary_

		:param ooxml_numbering_part: _description_
		:param ooxml_styles: _description_
		:return: _description_
		"""
		ooxml_abstract_numberings: Optional[list[OoxmlElement]] = ooxml_numbering_part.ooxml.xpath_query(
			query="./w:abstractNum"
		)
		if ooxml_abstract_numberings is None:
			return []
		
		abstract_numberings: list[AbstractNumbering] = []
		for ooxml_abstract_numbering in ooxml_abstract_numberings:
			abstract_numbering: AbstractNumbering = AbstractNumbering.parse(
				ooxml_abstract_numbering=ooxml_abstract_numbering, styles=styles
			)
			abstract_numberings.append(abstract_numbering)
		
		return abstract_numberings

		
	@staticmethod
	def _parse_numberings(ooxml_numbering_part: OoxmlPart) -> list[Numbering]:
		return []
	
	def __str__(self) -> str:
		s = "\033[36m\033[1mAbstract numberings\033[0m\n"
		for i, abstract_numbering in enumerate(self.abstract_numberings):
			arrow = "\u2514\u2500\u2500\u25BA" if i==len(self.abstract_numberings)-1 else "\u251c\u2500\u2500\u25BA"
			s += f" {arrow} {abstract_numbering.__str__()}"
		return s
