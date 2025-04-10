from __future__ import annotations
from typing import Optional
from enum import Enum

from colour import Color

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement
import ooxml_docx.structure.properties as OOXML_PROPERTIES

class FontSize(float):
	@classmethod
	def default(cls) -> FontSize:
		# TODO: investigate further about default font size
		return 1.0

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[FontSize]:
		if v is None:
			if not must_default:
				return None
			
			return cls.default()

		return float(v)


class FontColor(Color):
	@classmethod
	def default(cls) -> FontColor:
		return Color(color="black")


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
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[Script]:
		"""
		Convert the OOXML attribute value to the corresponding Script enum.
		"""
		if not must_default and v is None:
			return None
		
		return {
			"baseline": cls.normal,
			"superscript": cls.superscript,
			"subscript": cls.subscript,
		}.get(v, cls.default())


def toggle_str_to_bool(s: Optional[str]) -> bool:
	if s is None:
		return True
	
	match s.lower():
		case "1":
			return True
		case "true":
			return True
		case _:
			return False


class RunStyleProperties(ArbitraryBaseModel):
	font_size: Optional[FontSize] = None
	font_color: Optional[FontColor] = None
	bold: Optional[bool] = None
	italic: Optional[bool] = None
	underline: Optional[bool] = None
	script: Optional[Script] = None

	@classmethod
	def default(cls) -> RunStyleProperties:
		
		return cls(
			font_size=FontSize.default(),
			color=FontColor.default(),
			bold=False,
			italic=False,
			underline=False,
			script=Script.default()
		)
	
	@classmethod
	def from_ooxml(
		cls, run_properties: Optional[OOXML_PROPERTIES.RunProperties], must_default: bool=False
	) -> RunStyleProperties:
		if run_properties is not None:	
			# TODO clean this toggle shit, where: it can either be true, false or none
			bold_element: Optional[OoxmlElement] = run_properties.xpath_query(query="./w:b", singleton=True)
			italic_element: Optional[OoxmlElement] = run_properties.xpath_query(query="./w:i", singleton=True)
			underline_element: Optional[OoxmlElement] = run_properties.xpath_query(query="./w:u", singleton=True)

			underline_element.xpath_query(query="./@w:val", singleton=True) # TODO capture false when val is "none"

			return cls(
				font_size=FontSize.from_ooxml_val(
					v=run_properties.xpath_query(query="./w:sz/@w:val", singleton=True), must_default=must_default
				),
				color=Color("black"),  # TODO: actually implement color parsing
				bold=toggle_str_to_bool(bold_element.xpath_query(query="./@w:val", singleton=True)) if bold_element is not None else None,
				italic=toggle_str_to_bool(italic_element.xpath_query(query="./@w:val", singleton=True)) if italic_element is not None else None,
				# Even though it is not a toggle property, we will treat it as such because of the tool intended use
				underline=toggle_str_to_bool(),
				script=Script.from_ooxml_val(
					v=run_properties.xpath_query(query="./w:vertAlign/@w:val", singleton=True), must_default=must_default
				)
			)

		if must_default:
			return cls.default()
		
		return cls()


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
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[Justification]:
		"""
		Convert the OOXML attribute value to the corresponding Justification enum.
		"""
		if not must_default and v is None:
			return None

		return {
			"start": cls.start,
			"left": cls.start,
			"end": cls.end,
			"right": cls.end,
			"center": cls.center,
			"both": cls.justified,
			"distribute": cls.justified  # Even though it is supposed to be it's own type...
		}.get(v, cls.default())


class IndentationValue(float):
	@classmethod
	def default(cls) -> IndentationValue:
		return 0.0

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[IndentationValue]:
		if v is None:
			if not must_default:
				return None
			
			return cls.default()

		return float(v)


class Indentation(ArbitraryBaseModel):
	"""
	|			|<--first-->Aaaaa|		   |
	|<--start-->|aaaaaaaaaaaaaaaa|<--end-->|
	|			|aaaaaaaaaa.     |		   |
	"""
	start: Optional[IndentationValue] = None
	end: Optional[IndentationValue] = None
	first: Optional[IndentationValue] = None

	@classmethod
	def from_ooxml(cls, el: Optional[OoxmlElement], must_default: bool=False) -> Optional[Indentation]:
		"""

		"""
		if not must_default and el is None:
			return None
		
		first: Optional[float] = IndentationValue(v=el.xpath_query(query="./@w:hanging", singleton=True))
		if first is None:
			first = IndentationValue(v=el.xpath_query(query="./@w:firstLine", singleton=True), must_default=must_default)
		else:
			first = -first

		return cls(
			start=IndentationValue.from_ooxml_val(
				v=el.xpath_query(query="./@w:start|./@w:left", singleton=True), must_default=must_default
			),
			end=IndentationValue.from_ooxml_val(
				v=el.xpath_query(query="./@w:end|./@w:right", singleton=True), must_default=must_default
			),
			first=first
		)


class ParagraphStyleProperties(ArbitraryBaseModel):
	justification: Optional[Justification] = None
	indentation: Optional[Indentation] = None

	@classmethod
	def default(cls) -> RunStyleProperties:
		return cls(justification=Justification.default(), indentation=Indentation())
	
	@classmethod
	def from_ooxml(
		cls, paragraph_properties: Optional[OOXML_PROPERTIES.ParagraphProperties], must_default: bool=False
	) -> ParagraphStyleProperties:
		if paragraph_properties is not None:
			return cls(
				justification=Justification.from_ooxml_val(
					v=paragraph_properties.xpath_query(query="./w:jc/@w:val", singleton=True), must_default=must_default
				),
				indentation=Indentation.from_ooxml(
					element=paragraph_properties.xpath_query(query="./w:ind", singleton=True), must_default=must_default
				)
			)
	
		if must_default:
			return cls.default()
		
		return cls()


class TableStyleProperties(ArbitraryBaseModel):
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
	run_style_properties: RunStyleProperties
	paragraph_style_properties: ParagraphStyleProperties

	table_style_properties: Optional[TableStyleProperties] = None

	@classmethod
	def from_ooxml(cls, el: )


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