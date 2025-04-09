from __future__ import annotations
from typing import Optional
from enum import Enum

from colour import Color

from utils.pydantic import ArbitraryBaseModel


class Indentation(ArbitraryBaseModel):
	"""
	|			|<--first-->aaaaa|		   |
	|<--start-->|aaaaaaaaaaaaaaaa|<--end-->|
	|			|aaaaaaaaaa.     |		   |
	"""
	start: float
	end: float
	first: float


class Justification(Enum):
	start = "START"				# |The quick brown fox.                |
	center = "CENTER"			# |        The quick brown fox.        |
	end = "END"					# |                The quick brown fox.|
	both = "BOTH"				# |The      quick       brown      fox.|
	distribute = "DISTRIBUTE"	# |T h e  q u i c k  b r o w n  f o x .|


class Script(Enum):
	normal = None
	superscript = "SUPERSCRIPT"
	subscript = "SUBSCRIPT"


class VisualProperties(ArbitraryBaseModel):
	"""
	The relevant formatting properties are:
	 - font_size:
	 - color:
	 - bold:
	 - italic:
	 - underline:
	 - script:
	 - justification:
	 - indentation:
	TODO: Expand properties
	"""

	font_size: int
	color: Color
	bold: bool
	italic: bool
	underline: bool # TODO: Complicate this with the types of underlines docx provides
	script: Script
	justification: Justification
	indentation: Indentation


class Style(ArbitraryBaseModel):
	"""
	To simplify style management and processing, generalizes the concept of a style given to a paragraph,
	Gathering all the relevant properties from the different OOXML style types that have an effect from a paragraph viewpoint,
	both at a paragraph and character level properties (<w:pPr> and <w:rPr>).
	"""
	id: str
	
	parent: Optional[Style] = None
	children: Optional[list[Style]] = None


class Numbering(ArbitraryBaseModel):
	idk: str


class Format(ArbitraryBaseModel):
	style: Style
	numbering: Numbering