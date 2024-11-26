from __future__ import annotations
from typing import Optional
from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement
from ooxml_docx.properties import rPr, pPr
from ooxml_docx.styles import ParagraphStyle, NumberingStyle

class LevelProperties(ArbitraryBaseModel):
	"""_summary_

	"""
	# In this case there is no parent element that wraps the level properties
	elements: list[OoxmlElement] = []


class Level(OoxmlElement):
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


class AbstractNumbering(OoxmlElement):
	"""_summary_

	"""
	id: int
	name: Optional[str] = None
	numberings: Optional[list[Numbering]] = None
	levels: dict[int, Level] = {}
	
	style: Optional["NumberingStyle"] = None  # numStyleLink
	style_children: Optional[list[NumberingStyle]] = None  # styleLink


class NumberingStyle(NumberingStyle):

	parent_abstract_numbering: Optional[AbstractNumbering] = None
	children_abstract_numbering: Optional[list[AbstractNumbering]] = None


class Numbering(OoxmlElement):
	"""
	"""
	id: int
	abstract_numbering: AbstractNumbering
