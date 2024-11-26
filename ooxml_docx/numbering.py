from __future__ import annotations
from typing import Optional
from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from ooxml_docx.properties import rPr, pPr
from ooxml_docx.styles import OoxmlStyleTypes, OoxmlStyles, ParagraphStyle, NumberingStyle, Style
from ooxml_docx.styles import NumberingStyle as BaseNumberingStyle


class NumberingStyle(NumberingStyle):
	"""_summary_

	Important: This is the complete version and the one that should be used for imports.
	
	:param NumberingStyle: _description_
	"""
	abstract_numbering_parent: Optional[AbstractNumbering] = None
	abstract_numbering_children: Optional[list[AbstractNumbering]] = None


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

class AbstractNumberingAssociatedStyles(ArbitraryBaseModel):
	"""_summary_

	"""
	style: Optional[NumberingStyle] = None  # numStyleLink
	style_children: Optional[list[NumberingStyle]] = None  # styleLink


class AbstractNumbering(OoxmlElement):
	"""_summary_

	"""
	id: int
	name: Optional[str] = None

	numberings: Optional[list[Numbering]] = None
	levels: dict[int, Level] = {}

	associated_styles: Optional[AbstractNumberingAssociatedStyles] = None

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
			levels=cls._parse_levels(ooxml_abstract_numbering=ooxml_abstract_numbering, styles=styles),
			associated_styles=cls._parse_associated_styles(ooxml_abstract_numbering=ooxml_abstract_numbering, styles=styles)
		)
		abstract_numbering._associate_to_styles()

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
	
	@staticmethod
	def _parse_associated_styles(ooxml_abstract_numbering: OoxmlElement, styles: OoxmlStyles) -> AbstractNumberingAssociatedStyles:
		"""_summary_

		:param ooxml_abstract_numbering: _description_
		:param styles: _description_
		:return: _description_
		"""
		style: Optional[NumberingStyle] = None
		style_children: Optional[list[NumberingStyle]] = None

		style_id: Optional[str] = ooxml_abstract_numbering.xpath_query(query="./w:numStyleLink/@w:val", singleton=True)
		if style_id is not None:
			style = styles.find(id=str(style_id), type=OoxmlStyleTypes.NUMBERING)

		style_children_ids: Optional[list[str]] = ooxml_abstract_numbering.xpath_query(query="./w:styleLink/@w:val")
		if style_children_ids is not None:
			style_children = []
			for style_children_id in style_children_ids:
				style_child: Optional[NumberingStyle] = styles.find(id=str(style_children_id), type=OoxmlStyleTypes.NUMBERING)
				if style_child is not None:
					# ! This is the most straightforward solution I have been able to find so far...
					# The problem is that the NumberingStyle returned by styles.find() is the one defined at styles.py
					# And it expects the NumberingStyle defined in this script
					# (which is the complete one to avoid circular dependencies)
					# Moreover, the .model_dump() cannot be used to unpack correctly the necessary fields
					style_children.append(NumberingStyle(
						**{k: v for k, v in style_child.model_dump().items()if k in Style.model_fields},
						properties=style_child.properties
					))
		
		return AbstractNumberingAssociatedStyles(style=style, style_children=style_children)
	
	def _associate_to_styles(self) -> None:
		# Associate abstract numbering to each one of its levels
		for level in self.levels.values():
			level.abstract_numbering = self
		
		if self.associated_styles.style is not None:
			# Associate to the numbering style which the abstract numbering is based on (<w:numStyleLink>)
			if self.associated_styles.style.abstract_numbering_children is None:
				self.associated_styles.style.abstract_numbering_children = []
			self.associated_styles.style.abstract_numbering_children.append(self)

		if (self.associated_styles.style_children is not None and len(self.associated_styles.style_children) != 0):
			# Associate to the numbering styles which are based on the abstract numbering (<w:styleLink>)
			for style in self.associated_styles.style_children:
				style.abstract_numbering_parent = self

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
