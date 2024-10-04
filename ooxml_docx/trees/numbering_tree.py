from __future__ import annotations
from pydantic import Field, model_validator, field_validator, computed_field
from typing import Optional, Literal, Any

from lxml.etree import _Element as etreeElement

from ooxml_docx.trees.common import AbstractNumbering, Numbering, NumberingStyle, Level, LevelProperties, pPr, rPr
from ooxml_docx.trees.style_tree import OoxmlDocxStyleTree
from utils.etree import xpath_query, element_skeleton
from utils.pydantic import ArbitraryBaseModel


class OoxmlDocxNumberingTree(ArbitraryBaseModel):
	"""
	"""
	abstract_numberings: list[AbstractNumbering]
	numberings: list[Numbering]

	# Save metadata information as well as elements that are not explicitly parsed
	element_skeleton: etreeElement
	skipped_elements: Optional[list[etreeElement]] = None # mainly numbering styles


	@classmethod
	def build(cls, ooxml_numbering_part: etreeElement, style_tree: OoxmlDocxStyleTree) -> OoxmlDocxNumberingTree:
		"""_summary_

		:return: _description_
		"""
		return ""


class OoxmlDocxNumberingTreeInterface(ArbitraryBaseModel):
	"""_summary_

	"""
	ooxml_numbering_part: etreeElement
	style_tree: OoxmlDocxStyleTree

	def numbering_tree(self) -> OoxmlDocxNumberingTree:
		"""_summary_

		:return: _description_
		"""
		abstract_numberings, numberings = self._compute_numbering_trees()

		return "miau"
	

	def _compute_numbering_trees(self) -> tuple[list[AbstractNumbering], list[Numbering]]:
		"""_summary_

		:return: _description_
		"""
		abstract_numberings: list[AbstractNumbering] = []
		
		abstract_numberings_elements: list[etreeElement] = xpath_query(
			element=self.ooxml_numbering_part, query="./w:abstractNum", nullable=False
		)
		for abstract_numbering_element in abstract_numberings_elements:
			abstract_numbering: AbstractNumbering = self._compute_abstract_numbering(abstract_numbering=abstract_numbering_element)
			# Associate the abstract numbering definition to each one of its levels
			for level in abstract_numbering.levels.values():
				level.abstract_numbering = abstract_numbering
			
			abstract_numberings.append(abstract_numbering)

	def _compute_abstract_numbering(self, abstract_numbering: etreeElement) -> AbstractNumbering:
		"""_summary_

		The numbering instances associated to the abstract numbering definition
		 will be linked later on when numberings are processed.
		"""

		# Capture general style attributes and child elements
		id: int = int(xpath_query(
			element=abstract_numbering, query="./@w:abstractNumId", singleton=True, nullable=False
		))
		name: Optional[str] = xpath_query(
			element=abstract_numbering, query="./w:name/@w:val", singleton=True
		)
		if name is not None:
			name = str(name)
		
		# Parse indentation levels
		levels: dict[str, Level] = self._compute_levels(abstract_numbering=abstract_numbering)

		# Capture associated styles
		style, style_children = self._compute_abstract_numbering_associated_styles(
			abstract_numbering=abstract_numbering
		)
		
		return AbstractNumbering(
			id=id, name=name,
			levels=levels,
			style=style, style_children=style_children,
			element_skeleton=element_skeleton(element=abstract_numbering),
			skipped_elements=xpath_query(
				element=abstract_numbering,
				query="./*[not(self::w:name or self::w:lvl or self::w:numStyleLink or self::w:styleLink)]"
			)
		)

	def _compute_abstract_numbering_associated_styles(self, abstract_numbering: etreeElement) -> tuple[Optional[NumberingStyle], Optional[list[NumberingStyle]]]:
		"""_summary_

		:param abstract_numbering: _description_
		:return: _description_
		"""
		style: Optional[NumberingStyle] = None
		style_children: Optional[list[Numbering]] = None

		style_id: Optional[str] = xpath_query(
			element=abstract_numbering, query="./w:numStyleLink/@w:val", singleton=True
		)
		if style_id is not None:
			style = self.style_tree.find(id=str(style_id), type="numbering")

		style_children_ids: Optional[list[str]] = xpath_query(
			element=abstract_numbering, query="./w:styleLink/@w:val"
		)
		if style_children_ids is not None:
			style_children = [
				self.style_tree.find(id=str(style_children_id), type="numbering")
				for style_children_id in style_children_ids
			]
		
		return style, style_children
	
	def _compute_levels(self, abstract_numbering: etreeElement) -> dict[int, Level]:
		"""_summary_

		:param abstract_numbering: _description_
		:return: _description_
		"""
		levels: dict[int, Level] = {}

		levels_elements: list[etreeElement] = xpath_query(
			element=abstract_numbering, query="./w:lvl", nullable=False
		)
		for level_element in levels_elements:
			id: str = str(xpath_query(
				element=level_element, query="./@w:ilvl", singleton=True, nullable=False
			))
			level_parse: dict[str, etreeElement | list[etreeElement]] = self._parse_level_information(
				level=level_element
			)

			levels[id] = Level(
				id=id,
				properties=LevelProperties(elements=level_parse["level_properties"]),
				paragraph_properties=pPr(element=level_parse["pPr"])
				if level_parse["pPr"] is not None else None,
				run_properties=rPr(element=level_parse["rPr"])
				if level_parse["rPr"] is not None else None,
				style=self.style_tree.find(id=str(level_parse["style_id"]))
				if level_parse["style_id"] is not None else None,
				element_skeleton=level_parse["element_skeleton"]
			)
		
		return levels

	
	def _parse_level_information(self, level: etreeElement) -> dict[str, etreeElement | list[etreeElement]]:
		"""_summary_

		:param level: _description_
		:return: _description_
		"""

		return {
			"level_properties": xpath_query(
				element=level,
				query="./*[not(self::w:name or self::w:pPr or self::w:rPr or self::w:pStyle)]",
				nullable=False
			),  # In this case level properties acts like skipped elements
			"pPr": xpath_query(element=level, query="./w:pPr", singleton=True),
			"rPr": xpath_query(element=level, query="./w:rPr", singleton=True),
			"style_id": xpath_query(element=level, query="./w:pStyle/@w:val", singleton=True),
			"element_skeleton": element_skeleton(element=level)
		}

