from __future__ import annotations
from typing import Optional
from enum import Enum

from colour import Color

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement


class Script(Enum):
	"""
	Defaults to normal
	"""
	normal = None
	superscript = "SUPERSCRIPT"
	subscript = "SUBSCRIPT"

	@classmethod
	def default(cls) -> Script:
		return cls.normal

	@classmethod
	def from_ooxml_val(cls, v: Optional[str]) -> Script:
		"""
		Convert the OOXML attribute value to the corresponding Script enum.
		"""
		return {
			"baseline": cls.normal,
			"superscript": cls.superscript,
			"subscript": cls.subscript,
		}.get(v, cls.default())


class RunSpecificStyleProperties(ArbitraryBaseModel):
	font_size: float
	color: Color
	bold: bool
	italic: bool
	underline: bool
	script: Script

	@classmethod
	def default(cls) -> RunSpecificStyleProperties:
		# TODO: investigate further about default font size
		return cls(
			font_size=1.0, color=Color(color="black"), bold=False, italic=False, underline=False, script=Script.default()
		)


class Indentation(ArbitraryBaseModel):
	"""
	|			|<--first-->Aaaaa|		   |
	|<--start-->|aaaaaaaaaaaaaaaa|<--end-->|
	|			|aaaaaaaaaa.     |		   |
	"""
	start: float = 0.0
	end: float = 0.0
	first: float = 0.0

	@classmethod
	def from_ooxml(cls, element: Optional[OoxmlElement]) -> Indentation:
		"""
		Convert the OOXML attribute value to the corresponding Justification enum.
		"""
		start: Optional[float] = element.xpath_query(query="./@w:start|./@w:left", singleton=True)
		end: Optional[float] = element.xpath_query(query="./@w:end|./@w:right", singleton=True)
		
		first: Optional[float] = element.xpath_query(query="./@w:hanging", singleton=True)
		if first is not None:
			first: Optional[float] = element.xpath_query(query="./@w:firstLine", singleton=True)
		else:
			first = -float(first)

		return cls(
			start=float(start) if start is not None else 0.0,
			end=float(end) if end is not None else 0.0,
			first=float(first) if first is not None else 0.0
		)


class Justification(Enum):
	"""
	Defaults to start.
	"""
	start = "START"			# |The quick brown fox.                |
	center = "CENTER"		# |        The quick brown fox.        |
	end = "END"				# |                The quick brown fox.|
	justified = "JUSTIFIED"	# |The      quick       brown      fox.|

	@classmethod
	def default(cls) -> Justification:
		return cls.start

	@classmethod
	def from_ooxml_val(cls, v: Optional[str]) -> Justification:
		"""
		Convert the OOXML attribute value to the corresponding Justification enum.
		"""
		return {
			"start": cls.start,
			"left": cls.start,
			"end": cls.end,
			"right": cls.end,
			"center": cls.center,
			"both": cls.justified,
			"distribute": cls.justified  # Even though it is supposed to be it's own type...
		}.get(v, cls.default())

class ParagraphSpecificStyleProperties(ArbitraryBaseModel):
	justification: Justification
	indentation: Indentation

	@classmethod
	def default(cls) -> RunSpecificStyleProperties:
		return cls(justification=Justification.default(), indentation=Indentation())

class TableSpecificStyleProperties(ArbitraryBaseModel):
	todo: str

class StyleProperties(ArbitraryBaseModel):
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
	run_properties: RunSpecificStyleProperties
	paragraph_properties: ParagraphSpecificStyleProperties

	table_properties: Optional[TableSpecificStyleProperties] = None


class Style(ArbitraryBaseModel):
	"""
	To simplify style management and processing, generalizes the concept of a style given to a block,
	Gathering all the relevant properties from the different OOXML style types that have an effect from a block viewpoint,
	both at a paragraph and character level properties (<w:pPr> and <w:rPr>).
	"""
	id: str
	
	parent: Optional[Style] = None
	children: Optional[list[Style]] = None

	properties: StyleProperties


class Numbering(ArbitraryBaseModel):
	idk: str


class Format(ArbitraryBaseModel):
	style: Style
	numbering: Numbering