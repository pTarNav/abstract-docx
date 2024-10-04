from __future__ import annotations
from pydantic import Field
from typing import Optional, Literal, Any

from lxml import etree
from lxml.etree import _Element as etreeElement

from utils.etree import local_name
from utils.pydantic import ArbitraryBaseModel


class StyleProperty(ArbitraryBaseModel):
	"""
	Represents a .docx style properties element.
	"""
	element: etreeElement
	ooxml_tag: str

	def __init__(self, **data):
		super().__init__(**data)
		self.validate_tag()

	def validate_tag(self):
		if local_name(self.element) != self.ooxml_tag:
			raise ValueError(f"<{self.__class__.__name__}> requires OOXML <w:{self.ooxml_tag}> element")

	def __str__(self):
		etree.indent(tree=self.element, space="\t")
		return etree.tostring(self.element, pretty_print=True, encoding="utf8").decode("utf8")


class rPr(StyleProperty):
	ooxml_tag: str = "rPr"


class pPr(StyleProperty):
	ooxml_tag: str = "pPr"


class tblPr(StyleProperty):
	ooxml_tag: str = "tblPr"


class tblStylePr(StyleProperty):
	ooxml_tag: str = "tblStylePr"


class trPr(StyleProperty):
	ooxml_tag: str = "trPr"


class tcPr(StyleProperty):
	ooxml_tag: str = "tcPr"


class numPr(StyleProperty):
	ooxml_tag: str = "numPr"


class Style(ArbitraryBaseModel):
	"""
	Represents a .docx style element.
	"""
	id: str
	name: Optional[str] = None
	parent: Optional[Style] = None
	children: Optional[list[Style]] = None

	#
	element_skeleton: etreeElement
	skipped_elements: Optional[list[etreeElement]] = None

	def __str__(self) -> str:
		return self._custom_str_()

	def _custom_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		"""
		Computes string representation of a .docx style.

		:param depth: Indentation depth integer, defaults to 0.
		:param last: Style is the last one from the parent children list, defaults to False.
		:param line_state: List of booleans indicating whether to include vertical connection
		 for each previous indentation depth,
		 defaults to None to avoid mutable list initialization unexpected behavior.
		:return: Style string representation.
		"""
		if line_state is None:
			line_state = []
		
		# Compute string representation of style header
		prefix = " " if depth > 0 else ""
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)
		s = f"{arrow}\u2756 '{self.id}' ("

		if isinstance(self, RunStyle):
			s += self._run_style_header_str()
		if isinstance(self, ParagraphStyle):
			s += self._paragraph_style_header_str()
		if isinstance(self, TableStyle):
			s += self._table_style_header_str()
		if isinstance(self, NumberingStyle):
			s += self._numbering_style_header_str()

		# Update the line state for the current depth
		if depth > 0:
			if depth >= len(line_state):
				line_state.append(not last)
			else:
				line_state[depth] = not last

		# Compute string representation of child styles
		if self.children is not None:
			prefix = " "
			for level_state in line_state:
				prefix += "\u2502    " if level_state else "     "
			# Sort child styles ids
			sorted_children = self.children
			for i, child in enumerate(sorted_children):
				arrow = prefix + (
					"\u2514\u2500\u2500\u25BA" if i == len(sorted_children)-1 
					else "\u251c\u2500\u2500\u25BA"
				)
				s += child._custom_str_(
					depth=depth+1, last=i==len(sorted_children)-1,
					line_state=line_state[:]  # Pass-by-value
				)
		
		return s

	def _run_style_header_str(self) -> str:
		"""_summary_
		:return: _description_
		"""

		s = "type='character', "
		s += f"name='{self.name}', " if self.name is not None else ""
		s += f"n.children={len(self.children) if self.children is not None else 0}"
		s += ", <rPr>" if self.properties is not None else ""
		s += ")\n"

		return s
	
	def _paragraph_style_header_str(self) -> str:
		"""_summary_
		:return: _description_
		"""

		s = "type='paragraph', "
		s += f"name='{self.name}', " if self.name is not None else ""
		s += f"n.children={len(self.children) if self.children is not None else 0}"
		s += ", <pPr>" if self.properties is not None else ""
		s += ", <rPr>" if self.properties is not None else ""
		s += ")\n"

		return s
	
	def _table_style_header_str(self) -> str:
		"""_summary_
		:return: _description_
		"""

		s = "type='table', "
		s += f"name='{self.name}', " if self.name is not None else ""
		s += f"n.children={len(self.children) if self.children is not None else 0}"
		s += ", <tblPr>" if self.properties is not None else ""
		s += ", <tblStylePr>" if self.conditional_properties is not None else ""
		s += ", <trPr>" if self.row_properties is not None else ""
		s += ", <tcPr>" if self.cell_properties is not None else ""
		s += ")\n"

		return s
	
	def _numbering_style_header_str(self) -> str:
		"""_summary_
		:return: _description_
		"""

		s = "type='numbering', "
		s += f"name='{self.name}', " if self.name is not None else ""
		s += f"n.children={len(self.children) if self.children is not None else 0}"
		s += ", <numPr>" if self.properties is not None else ""
		s += ")\n"

		return s


class RunStyle(Style):
	"""
	Represents a .docx run style.
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[rPr] = None


class ParagraphStyle(Style):
	"""
	Represents a .docx paragraph style. Which can contain both paragraph and run properties.
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[pPr] = None
	run_properties: Optional[rPr] = None


class TableStyle(Style):
	"""
	Represents a .docx table style.
	Which can contain general and conditional table properties, as well as row and cell properties.
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[tblPr] = None
	conditional_properties: Optional[tblStylePr] = None
	row_properties: Optional[trPr] = None
	cell_properties: Optional[tcPr] = None


class NumberingStyle(Style):
	"""
	Represents a .docx numbering style. Which can contain numbering properties,
	 and be inherited by or inherit abstract numbering definitions properties
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[numPr] = None

	parent_abstract_numbering: Optional[AbstractNumbering] = None
	children_abstract_numbering: Optional[list[AbstractNumbering]] = None


class LevelProperties(ArbitraryBaseModel):
	"""_summary_

	"""
	# In this case there is no parent element that wraps the level properties
	elements: list[etreeElement]


class Level(ArbitraryBaseModel):
	"""_summary_

	"""
	id: int
	# Note that abstract numbering is optional in order to facilitate the construction
	# however, it should not be empty and always associated to an abstract numbering definition.
	abstract_numbering: Optional[AbstractNumbering] = None
	properties: Optional[LevelProperties] = None
	paragraph_properties: Optional[pPr] = None
	run_properties: Optional[rPr] = None
	style: Optional[NumberingStyle | ParagraphStyle] = None

	element_skeleton: etreeElement
	skipped_elements: Optional[list[etreeElement]] = None


class AbstractNumbering(ArbitraryBaseModel):
	"""_summary_

	"""
	id: int
	name: Optional[str] = None
	numberings: Optional[list[Numbering]] = None
	# Note that it avoids using a mutable default list which can lead to unintended behavior,
	# using pydantic list field generator instead.
	levels: dict[int, Level] = Field(default_factory=dict)
	
	style: Optional[NumberingStyle] = None  # numStyleLink
	style_children: Optional[list[NumberingStyle]] = None  # styleLink

	element_skeleton: etreeElement
	skipped_elements: Optional[list[etreeElement]] = None


class Numbering(ArbitraryBaseModel):
	"""
	"""
	id: int
	abstract_numbering: AbstractNumbering

	element_skeleton: etreeElement
	skipped_elements: Optional[list[etreeElement]] = None
