from __future__ import annotations
from typing import Optional, Any
from enum import Enum

from colour import Color

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement
import ooxml_docx.structure.properties as OOXML_PROPERTIES
from ooxml_docx.structure.styles import OoxmlStyles


class FontSize(float):
	@classmethod
	def default(cls) -> FontSize:
		return cls(22.0)

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[FontSize]:
		if v is None:
			if not must_default:
				return None
			
			return cls.default()

		return cls(float(v))
	

class FontColor(Color):
	@classmethod
	def default(cls) -> FontColor:
		return cls("#000000")

	@classmethod
	def from_ooxml_val(cls, v:Optional[str], must_default: bool=False) -> Optional[FontColor]:
		if v is None:
			if must_default:
				return cls.default()
			return None

		val = v.strip().lower()
		if val == "auto":
			return cls.default() if must_default else None

		hex_str = f"#{v.strip()}"

		return cls(hex_str)


class FontScript(Enum):
	"""
	Defaults to normal
	"""
	NORMAL = "normal"
	SUPERSCRIPT = "superscript"
	SUBSCRIPT = "subscript"

	@classmethod
	def default(cls) -> FontScript:
		return cls.NORMAL

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[FontScript]:
		"""
		Converts the OOXML attribute value to the corresponding Script enum.
		"""
		if not must_default and v is None:
			return None
		
		return {
			"baseline": cls.NORMAL,
			"superscript": cls.SUPERSCRIPT,
			"subscript": cls.SUBSCRIPT,
		}.get(v, cls.default())


class ToggleProperty(int):  # Subclass of int, because python will not let me do a subclass of bool for some ungodly reason
	def __new__(cls, value):
		# Normalize the value: any truthy value becomes 1, falsey becomes 0.
		normalized_value = 1 if value else 0
		return super().__new__(cls, normalized_value)
	def __str__(self):
		# Print as a boolean string for clarity.
		return "True" if self else "False"
	def __repr__(self):
		# Print as a boolean string for clarity.
		return "True" if self else "False"
	
	@classmethod
	def default(cls) -> ToggleProperty:
		return cls(False)
	
	@staticmethod
	def _from_existing_ooxml_val_str(v: str) -> bool:
		match str(v).lower():
			case "1":
				return True
			case "true":
				return True
			case _:
				return False

	@classmethod
	def from_ooxml(cls, el: Optional[OoxmlElement], must_default: bool=False) -> Optional[ToggleProperty]:
		if el is None:
			if not must_default:
				return None
			
			return cls.default()

		v: Optional[str] = el.xpath_query(query="./@w:val", singleton=True)

		# If the element exists, but no val is specified it just means that is an implicit True
		if v is None:
			return cls(True)

		return cls(cls._from_existing_ooxml_val_str(v=v))


class Bold(ToggleProperty):
	pass


class Italic(ToggleProperty):
	pass


class Underline(ToggleProperty):
	# Even though it is not a toggle property, we will treat it as such because of the tool intended use
	
	@staticmethod
	def _from_existing_ooxml_val_str(v: str) -> bool:
		"""
		Override ToggleProperty class, since it is not actually an ooxml toggle property, the logic is a little bit different.
		"""
		match str(v).lower():
			case "none":
				return False
			case _:
				return True


class RunStyleProperties(ArbitraryBaseModel):
	font_size: Optional[FontSize] = None
	font_color: Optional[FontColor] = None
	font_script: Optional[FontScript] = None
	bold: Optional[ToggleProperty] = None
	italic: Optional[ToggleProperty] = None
	underline: Optional[Underline] = None  

	@classmethod
	def default(cls) -> RunStyleProperties:
		
		return cls(
			font_size=FontSize.default(),
			font_color=FontColor.default(),
			font_script=FontScript.default(),
			bold=Bold.default(),
			italic=Italic.default(),
			underline=Underline.default()
		)
	
	@classmethod
	def from_ooxml(
		cls, run_properties: Optional[OOXML_PROPERTIES.RunProperties], must_default: bool=False
	) -> RunStyleProperties:
		if run_properties is not None:
			return cls(
				font_size=FontSize.from_ooxml_val(
					v=run_properties.xpath_query(query="./w:sz/@w:val", singleton=True), must_default=must_default
				),
				font_script=FontScript.from_ooxml_val(
					v=run_properties.xpath_query(query="./w:vertAlign/@w:val", singleton=True), must_default=must_default
				),
				font_color=FontColor.from_ooxml_val(
					v=run_properties.xpath_query(query="./w:color/@w:val", singleton=True), must_default=must_default
				),
				bold=Bold.from_ooxml(
					el=run_properties.xpath_query(query="./w:b", singleton=True), must_default=must_default
				),
				italic=Italic.from_ooxml(
					el=run_properties.xpath_query(query="./w:i", singleton=True), must_default=must_default
				),				
				underline=Underline.from_ooxml(
					el=run_properties.xpath_query(query="./w:u", singleton=True), must_default=must_default
				)
			)

		if must_default:
			return cls.default()
		
		return cls()

	@classmethod
	def aggregate_ooxml(
		cls, agg: RunStyleProperties, add: RunStyleProperties, default: RunStyleProperties
	) -> RunStyleProperties:
		return cls(
			font_size=add.font_size if add.font_size is not None else agg.font_size,
			font_color=add.font_color if add.font_color is not None else agg.font_color,
			font_script=add.font_script if add.font_script is not None else agg.font_script,
			# ! TODO: Add table style possible toggle properties into the xor gate
			# bool(add.) is used because it could be None, which are interpreted as False
			bold=default.bold or Bold(bool(add.bold) ^ agg.bold),
			italic=default.italic or Italic(bool(add.italic) ^ agg.italic),
			underline=default.underline or Underline(bool(add.underline) ^ agg.underline)
		)
	
	def patch(self, other: RunStyleProperties) -> None:
		if other.font_size is not None:
			self.font_size = other.font_size
		if other.font_color is not None:
			self.font_color = other.font_color
		if other.font_script is not None:
			self.font_script = other.font_script
		if other.bold is not None:
			self.bold = other.bold
		if other.italic is not None:
			self.italic = other.italic
		if other.underline is not None:
			self.underline = other.underline

class Justification(Enum):
	"""
	Defaults to start.
	"""
	START = "start"			# |The quick brown fox.                |
	CENTER = "center"		# |        The quick brown fox.        |
	END = "end"				# |                The quick brown fox.|
	JUSTIFIED = "justified"	# |The      quick       brown      fox.|

	@classmethod
	def default(cls) -> Justification:
		return cls.START

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[Justification]:
		"""
		Convert the OOXML attribute value to the corresponding Justification enum.
		"""
		if not must_default and v is None:
			return None

		return {
			"start": cls.START,
			"left": cls.START,
			"end": cls.END,
			"right": cls.END,
			"center": cls.CENTER,
			"both": cls.JUSTIFIED,
			"distribute": cls.JUSTIFIED  # Even though it is supposed to be it's own type...
		}.get(v, cls.default())


class IndentationValue(float):
	@classmethod
	def default(cls) -> IndentationValue:
		return cls(0.0)

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[IndentationValue]:
		if v is None:
			if not must_default:
				return None
			
			return cls.default()

		return cls(float(v))


class Indentation(ArbitraryBaseModel):
	"""
	|			|<--first-->Lorem|		   |
	|<--start-->|ipsum dolor, sit|<--end-->|
	|			|amet.           |		   |
	"""
	start: Optional[IndentationValue] = None
	end: Optional[IndentationValue] = None
	first: Optional[IndentationValue] = None

	@classmethod
	def default(cls) -> Indentation:
		return cls(start=IndentationValue.default(), end=IndentationValue.default(), first=IndentationValue.default())

	@classmethod
	def from_ooxml(cls, el: Optional[OoxmlElement], must_default: bool=False) -> Optional[Indentation]:
		"""

		"""
		if el is not None:			
			first: Optional[float] = IndentationValue.from_ooxml_val(v=el.xpath_query(query="./@w:hanging", singleton=True))
			if first is None:
				first = IndentationValue.from_ooxml_val(
					v=el.xpath_query(query="./@w:firstLine", singleton=True), must_default=must_default
				)
			else:
				first = IndentationValue(-first)

			return cls(
				start=IndentationValue.from_ooxml_val(
					v=el.xpath_query(query="./@w:start|./@w:left", singleton=True), must_default=must_default
				),
				end=IndentationValue.from_ooxml_val(
					v=el.xpath_query(query="./@w:end|./@w:right", singleton=True), must_default=must_default
				),
				first=first
			)

		if must_default:
			return cls.default()
			
		return cls()


class ParagraphStyleProperties(ArbitraryBaseModel):
	justification: Optional[Justification] = None
	indentation: Indentation = Indentation()

	@classmethod
	def default(cls) -> RunStyleProperties:
		return cls(justification=Justification.default(), indentation=Indentation().default())
	
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
					el=paragraph_properties.xpath_query(query="./w:ind", singleton=True), must_default=must_default
				)
			)
	
		if must_default:
			return cls.default()
		
		return cls()
	
	@classmethod
	def aggregate_ooxml(cls, agg: ParagraphStyleProperties, add: ParagraphStyleProperties) -> ParagraphStyleProperties:
		return cls(
			justification=add.justification if add.justification is not None else agg.justification,
			indentation=Indentation(
				start=add.indentation.start if add.indentation.start is not None else agg.indentation.start,
				end=add.indentation.end if add.indentation.end is not None else agg.indentation.end,
				first=add.indentation.first if add.indentation.first is not None else agg.indentation.first
			)
		)

class LineSize(float):
	pass

class LineColor(Color):
	pass

class LineStyle(Enum):
	# TODO: Make it more flexible
	NONE = "none"
	SINGLE = "single"
	DOUBLE = "double"
	TRIPLE = "triple"
	DASHED = "dashed"
	DOTTED = "dotted"
	DOTTED_AND_DASHED = "dotted_and_dashed"
	WAVE = "wave"
	THIN = "thin"
	THICK = "thick"

class Border(ArbitraryBaseModel):
	line_size: LineSize
	line_color: LineColor
	line_style: LineStyle

class TableBorders(ArbitraryBaseModel):
	top: Optional[Border] = None
	bottom: Optional[Border] = None
	start: Optional[Border] = None
	end: Optional[Border] = None
	inside_horizontal: Optional[Border] = None
	inside_vertical: Optional[Border] = None

class CellShade(Color):
	pass

class TableStyleProperties(ArbitraryBaseModel):
	# TODO: Conditional formatting
	borders: TableBorders
	cell_shade: CellShade

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
	! TODO: Paragraph properties can also contain run properties, need to take this into account
	"""
	run_style_properties: RunStyleProperties
	paragraph_style_properties: ParagraphStyleProperties

	table_style_properties: Optional[TableStyleProperties] = None

	@classmethod
	def from_ooxml(
		cls,
		run_properties: Optional[OOXML_PROPERTIES.RunProperties]=None,
		paragraph_properties: Optional[OOXML_PROPERTIES.ParagraphProperties]=None,
		must_default: bool=False
	) -> StyleProperties:
		return cls(
			run_style_properties=RunStyleProperties.from_ooxml(
				run_properties=run_properties, must_default=must_default
			),
			paragraph_style_properties=ParagraphStyleProperties.from_ooxml(
				paragraph_properties=paragraph_properties, must_default=must_default
			)
		)

	@classmethod
	def aggregate_ooxml(cls, agg: StyleProperties, add: StyleProperties, default: StyleProperties) -> StyleProperties:
		return cls(
			run_style_properties=RunStyleProperties.aggregate_ooxml(
				agg=agg.run_style_properties, add=add.run_style_properties, default=default.run_style_properties
			),
			paragraph_style_properties=ParagraphStyleProperties.aggregate_ooxml(
				agg=agg.paragraph_style_properties, add=add.paragraph_style_properties
			)
		)


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

	def __eq__(self, v: Any) -> bool:
		if isinstance(v, Style):
			return self.properties == v.properties
		
		raise ValueError("") # TODO


class StylesView(ArbitraryBaseModel):
	styles: dict[str, Style]
	priority_keys: dict[int, list[str]]

	@classmethod
	def load(cls, styles: dict[str, Style], priority_ordered_styles: list[list[Style]]) -> StylesView:
		return cls(
			styles=styles,
			priority_keys={
				priority: [style.id for style in styles_in_priority]
				for priority, styles_in_priority in enumerate(priority_ordered_styles)
			}
		)

	@property
	def priorities(self) -> dict[int, list[Style]]:
		return {
			priority: [self.styles[style_id] for style_id in styles_keys]
			for priority, styles_keys in self.priority_keys.items()
		}
	
	def _find_priority(self, style: Style) -> int:
		# TODO make it cleaner
		for priority, style_ids_in_priority in self.priority_keys.items():
			if style.id in style_ids_in_priority:
				return priority
		
		raise KeyError("") # TODO
	
	def priority_difference(self, curr_style: Style, prev_style: Style) -> int:
		match self._find_priority(style=curr_style) - self._find_priority(style=prev_style):
			case 0:
				return 0
			case diff_priority if diff_priority < 0:
				return 1
			case diff_priority if diff_priority > 0:
				return -1

