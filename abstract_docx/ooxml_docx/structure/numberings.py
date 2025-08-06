from __future__ import annotations
from typing import Optional

from abstract_docx.utils.pydantic import ArbitraryBaseModel

from rich.tree import Tree
from abstract_docx.utils.printing import rich_tree_to_str

from abstract_docx.ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from abstract_docx.ooxml_docx.structure.properties import RunProperties, ParagraphProperties
from abstract_docx.ooxml_docx.structure.styles import OoxmlStyleTypes, OoxmlStyles, ParagraphStyle, _NumberingStyle

import logging
logger = logging.getLogger(__name__)


class NumberingStyle(_NumberingStyle):
	"""_summary_

	Important: This is the complete version and the one that should be used for imports.
	
	:param _NumberingStyle: Incomplete class of NumberingStyle defined in 'styles.py'.
	"""
	abstract_numbering_parent: Optional[AbstractNumbering] = None  # w:styleLink
	abstract_numbering_children: Optional[list[AbstractNumbering]] = None  # w:numStyleLink
	
	numbering: Optional[Numbering] = None
	indentation_level: Optional[int] = None

	# @classmethod
	# def load_from_incomplete(cls, incomplete_numbering_style: _NumberingStyle) -> NumberingStyle:
	# 	# ! This is the most straightforward solution I have been able to find so far...
	# 	# The problem is that the NumberingStyle returned by styles.find() is the one defined at styles.py
	# 	# And it expects the NumberingStyle defined in this script
	# 	# (which is the complete one to avoid circular dependencies)
	# 	# Moreover, the .model_dump() cannot be used to unpack correctly the necessary fields
	# 	return cls(
	# 		**{k: v for k, v in incomplete_numbering_style.model_dump().items()if k in Style.model_fields},
	# 		properties=incomplete_numbering_style.properties
	# 	)

class Level(OoxmlElement):
	"""_summary_

	"""
	id: int
	# Note that abstract numbering is optional in order to facilitate the construction
	# however, it should not be empty and always associated to an abstract numbering definition.
	abstract_numbering: Optional[AbstractNumbering] = None

	properties: Optional[list[OoxmlElement]] = None  # TODO, this is actually never used because it does not have the commodity of xpath_query
	run_properties: Optional[RunProperties] = None
	paragraph_properties: Optional[ParagraphProperties] = None
	
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
			run_properties=RunProperties(ooxml=ooxml_run_properties) if ooxml_run_properties is not None else None,
			paragraph_properties=(
				ParagraphProperties(ooxml=ooxml_paragraph_properties) if ooxml_paragraph_properties is not None else None
			),
			style=cls._parse_style(ooxml_level=ooxml_level, styles=styles)
		)
	
	@staticmethod
	def _parse_style(ooxml_level: OoxmlElement, styles: OoxmlStyles) -> Optional[NumberingStyle | ParagraphStyle]:
		"""_summary_

		:param ooxml_level: _description_
		:param styles: _description_
		:raises ValueError: _description_
		:return: _description_
		"""

		style_id: Optional[str] = ooxml_level.xpath_query(query="./w:pStyle/@w:val", singleton=True)
		if style_id is None:
			return None
		style_id = str(style_id)

		numbering_style_search_result: Optional[NumberingStyle] = styles.find(id=style_id, type=OoxmlStyleTypes.NUMBERING)
		if numbering_style_search_result is not None:
			return numbering_style_search_result
		
		paragraph_style_search_result: Optional[ParagraphStyle] = styles.find(id=style_id, type=OoxmlStyleTypes.PARAGRAPH)
		if paragraph_style_search_result is not None:
			return paragraph_style_search_result
		
		raise KeyError(f"Inexistent style referenced: {style_id=}.")

	def __str__(self) -> str:
		return f"[bold]{self.id}[/bold]: '{self.style.id if self.style is not None else ''}'"


class AbstractNumberingAssociatedStyles(ArbitraryBaseModel):
	"""_summary_

	Assumption: Only numbering styles can be associated to abstract numberings
	 through the <w:numStyleLink> and <w:styleLink> mechanism
	"""
	# Assumption: An abstract numbering can only have at maximum 1 style link
	# Nowhere does it specify if there can be only one of each maximum
	# ! TODO: Further investigate this
	style_parent: Optional[NumberingStyle] = None  # numStyleLink
	style_children: Optional[list[NumberingStyle]] = None  # styleLink

	def __str__(self) -> str:
		return rich_tree_to_str(self._tree_str_())
	
	def _tree_str_(self) -> Tree:
		tree = Tree("[bold cyan]Associated styles[/bold cyan]")

		if self.style_parent is not None:
			tree.add(f"[bold]Parent[/bold]: '{self.style_parent.id}'")
		
		if self.style_children is not None:
			s = ", ".join([f"'{style.id}'" for style in self.style_children])
			tree.add(f"[bold]Children[/bold]: [{s}]")

		return tree


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
		abstract_numbering._associate_to_levels_and_styles()

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
	def _parse_associated_styles(
		ooxml_abstract_numbering: OoxmlElement, styles: OoxmlStyles
	) -> Optional[AbstractNumberingAssociatedStyles]:
		"""_summary_

		:param ooxml_abstract_numbering: _description_
		:param styles: _description_
		:return: _description_
		"""
		style_parent: Optional[NumberingStyle] = None
		style_children: Optional[list[NumberingStyle]] = None

		style_parent_id: Optional[str] = ooxml_abstract_numbering.xpath_query(query="./w:numStyleLink/@w:val", singleton=True)
		if style_parent_id is not None:
			style_parent = styles.find(id=str(style_parent_id), type=OoxmlStyleTypes.NUMBERING)
			if style_parent is None:
				raise KeyError(f"Inexistent parent style referenced: {style_parent_id=}.")

		style_children_ids: Optional[list[str]] = ooxml_abstract_numbering.xpath_query(query="./w:styleLink/@w:val")
		if style_children_ids is not None:
			style_children: list[NumberingStyle] = []
			for style_child_id in style_children_ids:
				style_child: Optional[_NumberingStyle] = styles.find(id=str(style_child_id), type=OoxmlStyleTypes.NUMBERING)
				if style_child is not None:
					style_children.append(style_child)
				else:
					raise KeyError(f"Inexistent child style referenced: {style_child_id=}.")
		
		return (
			AbstractNumberingAssociatedStyles(style_parent=style_parent, style_children=style_children) 
			if style_parent is not None or style_children is not None else None
		)
	
	def _associate_to_levels_and_styles(self) -> None:
		# Associate abstract numbering to each one of its levels
		for level in self.levels.values():
			level.abstract_numbering = self
		
		if self.associated_styles is not None:
			if self.associated_styles.style_parent is not None:
				# Associate to the numbering style which the abstract numbering is based on (<w:numStyleLink>)
				if self.associated_styles.style_parent.abstract_numbering_children is None:
					self.associated_styles.style_parent.abstract_numbering_children = []
				self.associated_styles.style_parent.abstract_numbering_children.append(self)

			if self.associated_styles.style_children is not None:
				# Associate to the numbering styles which are based on the abstract numbering (<w:styleLink>)
				for style in self.associated_styles.style_children:
					style.abstract_numbering_parent = self

	def __str__(self) -> str:		
		return rich_tree_to_str(self._tree_str_())
	
	def _tree_str_(self) -> Tree:
		tree = Tree(f"[bold]{self.id}[/bold]: '{self.name if self.name is not None else ''}'")

		if self.associated_styles is not None:
			tree.add(self.associated_styles._tree_str_())

		level_tree = tree.add("[bold cyan]Levels[/bold cyan]")
		for level in self.levels.values():
			level_tree.add(level.__str__())

		return tree


class LevelOverride(OoxmlElement):
	"""_summary_

	:return: _description_
	"""
	id: int
	level: Optional[Level] = None
	start_override: Optional[int] = None

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

		return cls(
			element=ooxml_level_override.element,
			id=id,
			level=cls._parse_level(ooxml_level_override=ooxml_level_override, styles=styles, id=id),
			start_override=cls._parse_start_override(ooxml_level_override=ooxml_level_override)
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
				f" and override level definition id (<w:lvl w:ilvl={level.id}>) do not match."
			))

		return level
	
	@staticmethod
	def _parse_start_override(ooxml_level_override: OoxmlElement) -> Optional[int]:
		start_override: Optional[int] = ooxml_level_override.xpath_query(query="./w:startOverride/@w:val", singleton=True)
		if start_override is not None:
			start_override = int(start_override)
		
		return start_override


class Numbering(OoxmlElement):
	"""
	"""
	id: int
	abstract_numbering: AbstractNumbering
	overrides: dict[int, LevelOverride] = {}

	def _associate_abstract_numbering(self) -> None:
		"""Associates the numbering to its abstract numbering."""
		if self.abstract_numbering.numberings is None:
			self.abstract_numbering.numberings = []
		self.abstract_numbering.numberings.append(self)

	def _associate_overrides(self) -> None:
		"""Associates the numbering to each one of its overrides."""
		for override in self.overrides.values():
			override.numbering = self

	@classmethod
	def parse(
		cls, ooxml_numbering: OoxmlElement, abstract_numberings: list[AbstractNumbering], styles: OoxmlStyles
	) -> Numbering:
		"""_summary_

		:param ooxml_numbering: _description_
		:return: _description_
		"""
		abstract_numbering: AbstractNumbering = cls._parse_abstract_numbering(
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

		numbering._associate_abstract_numbering()
		numbering._associate_overrides()

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
			raise ValueError(
				f"No abstract numbering definition <w:abstractNum> found for abstractNumId: {abstract_numbering}."
			)

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
			
			# Associate overridden level (if level exists in abstract numbering)
			if level_override.id in abstract_numbering.levels.keys():
				level_override.overridden_level = abstract_numbering.levels[level_override.id]

			level_overrides[level_override.id] = level_override

		return level_overrides
	
	def find_style_level(self, style: ParagraphStyle | NumberingStyle, visited_abstract_numberings: Optional[list[int]] = None) -> int:
		"""_summary_
		There are 3 cases when parsing the indentation level (ordered by priority):
		 - The indentation level is explicit, by stating the indentation level in the numbering properties.
		 (Even though the OOXML documentation says it should never happen, in practice it does, therefore,
		 the assumption is made that if the indentation level is explicitly stated, it should take preference)
		 - The indentation level is implicit, by referencing the style inside the respective level.
		 - Lowest indentation level assumption, so there can never be an empty indentation level.
		:param numbering_style: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		# Ensure that same abstract numbering is not visited twice to avoid infinite recursive loops in the search
		if visited_abstract_numberings is None:
			visited_abstract_numberings = []
		if self.abstract_numbering.id in visited_abstract_numberings:
			raise RecursionError("")  # TODO

		# Case: Style contains an indentation level marker.
		if isinstance(style, ParagraphStyle):
			indentation_level: Optional[int] = style.properties.xpath_query(query="./w:numPr/w:ilvl/@w:val", singleton=True)
		elif isinstance(style, NumberingStyle):
			indentation_level: Optional[int] = style.properties.xpath_query(query="./w:ilvl/@w:val", singleton=True)
		else:
			raise TypeError(
				f"Invalid OOXML style type (must be 'Paragraph' or 'Numbering'): {type(style)} (for {style.id=})."
			)
		
		if indentation_level is not None:
			return int(indentation_level)

		# Case: Indentation level is marked by the style inside the level object.
		for i, level in self.abstract_numbering.levels.items():
			if level.style is not None and level.style.id == style.id:
				return i
		
		if (
			self.abstract_numbering.associated_styles is not None 
			and self.abstract_numbering.associated_styles.style_parent is not None
			and self.abstract_numbering.associated_styles.style_parent.numbering is not None
		):
			visited_abstract_numberings.append(self.abstract_numbering.id)
			return self.abstract_numbering.associated_styles.style_parent.numbering.find_style_level(
				style=style, visited_abstract_numberings=visited_abstract_numberings
			)
		
		# In some cases (because of ooxml manipulation from external programs),	
		#  it might be assumed that the level to be used is the lowest one available.
		# Raise a warning to log that this assumption has been made.
		logger.warning(f"Lowest indentation level assumption made for: {style.id=}")
		return 0


def _reload_incomplete_numbering_styles_into_complete(numbering_styles: list[_NumberingStyle]) -> None:
	for numbering_style in numbering_styles:
		# Monkey patching
		numbering_style.__class__ = NumberingStyle
		numbering_style.abstract_numbering_parent = None
		numbering_style.abstract_numbering_children = None
		numbering_style.numbering = None

		if numbering_style.children is not None:
			_reload_incomplete_numbering_styles_into_complete(numbering_styles=numbering_style.children)
			

class OoxmlNumberings(ArbitraryBaseModel):
	abstract_numberings: list[AbstractNumbering] = []
	numberings: list[Numbering] = []

	def _associate_styles_and_numberings(
			self, styles: list[ParagraphStyle | NumberingStyle], style_type: OoxmlStyleTypes
		) -> None:
		for style in styles:
			if style.properties is not None:
				match style_type:
					case OoxmlStyleTypes.PARAGRAPH:
						numbering_id: Optional[int] = style.properties.xpath_query(
							query="./w:numPr/w:numId/@w:val", singleton=True
						)
					case OoxmlStyleTypes.NUMBERING:
						numbering_id: Optional[int] = style.properties.xpath_query(query="./w:numId/@w:val", singleton=True)
					case _:
						raise KeyError((
							f"Invalid OOXML style type"
							f" (must be 'OoxmlStyleTypes.PARAGRAPH' or 'OoxmlStyleTypes.Numbering'): {style_type}."
						))
				
				if numbering_id is not None:
					numbering_id = int(numbering_id)
				numbering: Optional[Numbering] = self.find(id=numbering_id) if numbering_id is not None else None
				
				if numbering is not None:
					style.numbering = numbering
					# Indentation level is found after all the styles have been assigned their respective numbering

				elif numbering_id is not None:
					# In some cases (because of ooxml manipulation from external programs),
					#  there is a numbering reference to an inexistent numbering instance.
					# They are harmless and will be corrected in the abstract_docx normalization step.
					# Raises a warning instead of an error and proceeds.
					logger.warning(f"Inexistent numbering referenced: {numbering_id=} (inside {style.id=})")

			if style.children is not None:
				self._associate_styles_and_numberings(styles=style.children, style_type=style_type)
	
	def _find_styles_indentation_levels(self, styles: list[ParagraphStyle | NumberingStyle]) -> None:
		"""
		Indentation levels need to be found after the numberings have been assigned due to their recursive nature
		"""
		for style in styles:
			if style.numbering is not None:
				style.indentation_level = style.numbering.find_style_level(style=style)
			
			if style.children is not None:
				self._find_styles_indentation_levels(styles=style.children)


	@classmethod
	def build(cls, ooxml_numbering_part: OoxmlPart, styles: OoxmlStyles) -> OoxmlNumberings:
		"""_summary_

		:return: _description_
		"""
		# It is necessary to first reload the numbering styles into the complete class definition
		_reload_incomplete_numbering_styles_into_complete(numbering_styles=styles.roots.numbering)

		abstract_numberings: list[AbstractNumbering] = cls._parse_abstract_numberings(
			ooxml_numbering_part=ooxml_numbering_part, styles=styles
		)
		
		ooxml_numberings: OoxmlNumberings = cls(
			abstract_numberings=abstract_numberings,
			numberings=cls._parse_numberings(
				ooxml_numbering_part=ooxml_numbering_part, abstract_numberings=abstract_numberings, styles=styles
			)
		)

		#
		ooxml_numberings._associate_styles_and_numberings(styles=styles.roots.paragraph, style_type=OoxmlStyleTypes.PARAGRAPH)
		ooxml_numberings._associate_styles_and_numberings(styles=styles.roots.numbering, style_type=OoxmlStyleTypes.NUMBERING)
		ooxml_numberings._find_styles_indentation_levels(styles=styles.roots.paragraph+styles.roots.numbering)

		return ooxml_numberings
	

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

		return [
			AbstractNumbering.parse(ooxml_abstract_numbering=ooxml_abstract_numbering, styles=styles)
			for ooxml_abstract_numbering in ooxml_abstract_numberings
		] if ooxml_abstract_numberings is not None else []

		
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

	
	def find(self, id: int) -> Optional[Numbering]:
		"""
		Helper function for searching a numbering based on its id inside the numbering tree.

		Only numberings are of interest because any other outside ooxml element will always reference a numbering,
		 not an abstract numbering. 
		(With the only exception being the inheritance system between styles and abstract numberings properties)

		Because ids are assumed to be unique, this function will return the first match.

		:param id: Id of the numbering being searched.
		:return: Result of the search, a single Numbering object or None when no match is found.
		"""
		for numbering in self.numberings:
			if numbering.id == id:
				return numbering
		
		# No match found
		return None

	def __str__(self) -> str:
		return rich_tree_to_str(self._tree_str_())
	
	def _tree_str_(self) -> Tree:
		tree = Tree("[bold cyan]:input_numbers: Abstract numberings[/bold cyan]")
		for i, abstract_numbering in enumerate(self.abstract_numberings):
			tree.add(abstract_numbering._tree_str_())
		
		return tree
