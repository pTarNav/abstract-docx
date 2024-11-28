from __future__ import annotations
from typing import Optional
from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from ooxml_docx.structure.properties import rPr, pPr
from ooxml_docx.structure.styles import OoxmlStyleTypes, OoxmlStyles, ParagraphStyle, NumberingStyle, Style
from ooxml_docx.structure.styles import NumberingStyle as BaseNumberingStyle


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


class LevelOverride(OoxmlElement):
	"""_summary_

	:return: _description_
	"""
	id: int
	level: Optional[Level] = None
	start: Optional[int] = None

	# Note that numbering and overridden level are optional in order to facilitate the construction
	# however, they should not be empty and always associated to a numbering instance and the respective overridden level.
	numbering: Optional[Numbering] = None
	overridden_level: Optional[Level] = None

	@classmethod
	def parse(cls, ooxml_level_override: OoxmlElement, styles: OoxmlStyles) -> LevelOverride:
		"""_summary_

		:param ooxml_level_override: _description_
		:return: _description_
		"""
		id: int = int(ooxml_level_override.xpath_query(query="./@w:ilvl", nullable=False, singleton=True))
		start: Optional[int] = ooxml_level_override.xpath_query(query="./w:startOverride/@w:val", singleton=True)

		return cls(
			element=ooxml_level_override.element,
			id=id,
			level=cls._parse_level(ooxml_level_override=ooxml_level_override, styles=styles, id=id),
			start=int(start) if start is not None else None
		)

	@staticmethod
	def _parse_level(ooxml_level_override: OoxmlElement, styles: OoxmlStyles, id: int) -> Optional[Level]:
		"""_summary_

		:param ooxml_level_override: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		ooxml_level: Optional[OoxmlElement] = ooxml_level_override.xpath_query(query="./w:lvl", singleton=True)
		if ooxml_level is None:
			return None
		
		level: Level = Level.parse(ooxml_level=ooxml_level, styles=styles)

		# Check that the level override id and override level definition id match
		if level.id != id:
			raise ValueError((
				f"Level override id (<w:lvlOverride w:ilvl={id}>)"
				f" and override level definition id (<w:lvl w:ilvl={level.id}>) do not match"
			))

		return level

class Numbering(OoxmlElement):
	"""
	"""
	id: int
	abstract_numbering: AbstractNumbering
	overrides: dict[int, LevelOverride] = {}

	@classmethod
	def parse(
		cls, ooxml_numbering: OoxmlElement, abstract_numberings: list[AbstractNumbering], styles: OoxmlStyles
	) -> Numbering:
		"""_summary_

		:param ooxml_numbering: _description_
		:return: _description_
		"""
		abstract_numbering: AbstractNumbering =cls._parse_abstract_numbering(
				ooxml_numbering=ooxml_numbering, abstract_numberings=abstract_numberings
		)
		
		numbering: Numbering = cls(
			element=ooxml_numbering.element,
			id=int(ooxml_numbering.xpath_query(query="./@w:numId", nullable=False, singleton=True)),
			abstract_numbering=abstract_numbering,
			overrides=cls._parse_level_overrides(
				ooxml_numbering=ooxml_numbering, abstract_numbering=abstract_numbering, styles=styles
			)
		)

		#
		if numbering.abstract_numbering.numberings is None:
			numbering.abstract_numbering.numberings = []
		numbering.abstract_numbering.numberings.append(numbering)

		#
		for override in numbering.overrides.values():
			override.numbering = numbering

		return numbering
	
	@staticmethod
	def _parse_abstract_numbering(
		ooxml_numbering: OoxmlElement, abstract_numberings: list[AbstractNumbering]
	) -> AbstractNumbering:
		"""_summary_

		:param ooxml_numbering: _description_
		:param abstract_numberings: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		abstract_numbering_id: int = int(ooxml_numbering.xpath_query(
			query="./w:abstractNumId/@w:val", nullable=False, singleton=True
		))
		abstract_numbering: Optional[AbstractNumbering] = next(
			(
				abstract_numbering for abstract_numbering in abstract_numberings
				if abstract_numbering.id == abstract_numbering_id
			),
			None
		)
		if abstract_numbering is None:
			raise ValueError(f"No abstract numbering definition <w:abstractNum> found for abstractNumId: {abstract_numbering}")

		return abstract_numbering

	@staticmethod
	def _parse_level_overrides(
		ooxml_numbering: OoxmlElement, abstract_numbering: AbstractNumbering, styles: OoxmlStyles
	) -> dict[int, LevelOverride]:
		"""_summary_

		:param ooxml_numbering: _description_
		:param abstract_numbering: Abstract numbering associated to the numbering instance.
		:return: _description_
		"""
		ooxml_level_overrides: Optional[OoxmlElement] = ooxml_numbering.xpath_query(query="./w:lvlOverride")
		if ooxml_level_overrides is None:
			return {}
		
		level_overrides: dict[int, LevelOverride] = {}
		for ooxml_level_override in ooxml_level_overrides:
			level_override: LevelOverride = LevelOverride.parse(ooxml_level_override=ooxml_level_override, styles=styles)
			level_override.overridden_level = abstract_numbering.levels[level_override.id]  # Associate overridden level
			level_overrides[level_override.id] = level_override

		return level_overrides


class OoxmlNumberings(ArbitraryBaseModel):
	abstract_numberings: list[AbstractNumbering] = []
	numberings: list[Numbering] = []

	@classmethod
	def build(cls, ooxml_numbering_part: OoxmlPart, styles: OoxmlStyles) -> OoxmlNumberings:
		"""_summary_

		:return: _description_
		"""
		abstract_numberings: list[AbstractNumbering] = cls._parse_abstract_numberings(
			ooxml_numbering_part=ooxml_numbering_part, styles=styles
		)

		return cls(
			abstract_numberings=abstract_numberings,
			numberings=cls._parse_numberings(
				ooxml_numbering_part=ooxml_numbering_part, abstract_numberings=abstract_numberings, styles=styles
			)
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
		
		return [
			AbstractNumbering.parse(ooxml_abstract_numbering=ooxml_abstract_numbering, styles=styles)
			for ooxml_abstract_numbering in ooxml_abstract_numberings
		]

		
	@staticmethod
	def _parse_numberings(
		ooxml_numbering_part: OoxmlPart, abstract_numberings: list[AbstractNumbering], styles: OoxmlStyles
	) -> list[Numbering]:
		"""_summary_

		:param ooxml_numbering_part: _description_
		:return: _description_
		"""
		ooxml_numberings: Optional[list[OoxmlElement]] = ooxml_numbering_part.ooxml.xpath_query(query="./w:num")
		if ooxml_numberings is None:
			return []
		
		return [
			Numbering.parse(ooxml_numbering=ooxml_numbering, abstract_numberings=abstract_numberings, styles=styles)
			for ooxml_numbering in ooxml_numberings
		]
	
	def __str__(self) -> str:
		s = "\033[36m\033[1mAbstract numberings\033[0m\n"
		for i, abstract_numbering in enumerate(self.abstract_numberings):
			arrow = "\u2514\u2500\u2500\u25BA" if i==len(self.abstract_numberings)-1 else "\u251c\u2500\u2500\u25BA"
			s += f" {arrow} {abstract_numbering.__str__()}"
		return s
