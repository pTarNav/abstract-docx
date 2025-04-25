from __future__ import annotations
from typing import Optional
from enum import Enum

from colour import Color

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement
import ooxml_docx.structure.properties as OOXML_PROPERTIES
import ooxml_docx.structure.numberings as OOXML_NUMBERINGS


from abstract_docx.views.format.styles import Style, RunStyleProperties, ParagraphStyleProperties


class MarkerPattern(str):

	@classmethod
	def default(cls) -> MarkerPattern:
		return cls("")  # TODO: investigate further

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[MarkerPattern]:
		if v is None:
			if not must_default:
				return None
			
			return cls.default()
		
		return cls("")	# TODO: parse %d with regex and prepare accordingly
		

class MarkerType(Enum):
	NONE = "none"
	BULLET = "bullet"
	DECIMAL = "decimal"
	DECIMAL_ENCLOSED_CIRCLE = "decimal_enclosed_circle"
	DECIMAL_LEADING_ZERO = "decimal_leading_zero"
	CARDINAL = "cardinal"
	ORDINAL = "ordinal"
	LOWER_LETTER = "lower_letter"
	UPPER_LETTER = "upper_letter"
	LOWER_ROMAN = "lower_roman"
	UPPER_ROMAN = "upper_roman"

	@classmethod
	def default(cls) -> MarkerType:
		return cls.DECIMAL

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[MarkerType]:
		if not must_default and v is None:
			return None
		
		return {
			"none": cls.NONE,
			"bullet": cls.BULLET,
			"decimal": cls.DECIMAL,
			"decimalEnclosedCircle": cls.DECIMAL_ENCLOSED_CIRCLE,
			"decimalEnclosedFullstop": cls.DECIMAL,
			"decimalEnclosedParen": cls.DECIMAL,
			"decimalZero": cls.DECIMAL_LEADING_ZERO,
			"cardinalText": cls.CARDINAL,
			"ordinalText": cls.ORDINAL,
			"lowerLetter": cls.LOWER_LETTER,
			"upperLetter": cls.UPPER_LETTER,
			"lowerRoman": cls.LOWER_ROMAN,
			"upperRoman": cls.UPPER_ROMAN
		}.get(v, cls.default())


class Whitespace(Enum):
	NONE = "none"
	SPACE = "space"
	TAB = "tab"

	@classmethod
	def default(cls) -> Whitespace:
		return cls.TAB

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[Whitespace]:
		if not must_default and v is None:
			return None
		
		return {
			"nothing": cls.NONE,
			"space": cls.SPACE,
			"tab": cls.TAB,
		}.get(v, cls.default())


class Start(int):
	@classmethod
	def default(cls) -> Start:
		return cls(1)

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[Start]:
		if v is None:
			if not must_default:
				return None
			
			return cls.default()
		
		return cls(int(v))


class Restart(int):
	"""
	Special conditions:
	 - 0: Never restarts.
	 - -1: Restarts with a new instance of the previous level.
	"""
	@classmethod
	def default(cls) -> Restart:
		return cls(-1)

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[Restart]:
		if v is None:
			if not must_default:
				return None
			
			return cls.default()
		
		return cls(int(v))


class LevelStyleProperties(ArbitraryBaseModel):
	marker_pattern: Optional[MarkerPattern] = None
	marker_type: Optional[MarkerType] = None
	whitespace: Optional[Whitespace] = None
	start: Optional[Start] = None
	restart: Optional[Restart] = None

	@classmethod
	def default(cls) -> LevelStyleProperties:
		return cls(
			marker_patter=MarkerPattern.default(),
			marker_type=MarkerType.default(),
			whitespace=Whitespace.default(),
			start=Start.default(),
			restart=Restart.default()
		)

	@classmethod
	def from_ooxml(cls, level: Optional[OOXML_NUMBERINGS.Level], must_default: bool=False) -> LevelStyleProperties:
		# TODO: change level with level properties once we figure a way to make level properties easier to access
		if level is not None:
			return cls(
				marker_pattern=MarkerPattern.from_ooxml_val(
					v=level.xpath_query("./w:lvlText/@w:val", singleton=True), must_default=must_default
				),
				marker_type=MarkerType.from_ooxml_val(
					v=level.xpath_query("./w:numFmt/@w:val", singleton=True), must_default=must_default
				),
				whitespace=Whitespace.from_ooxml_val(
					v=level.xpath_query("./w:suff/@w:val", singleton=True), must_default=must_default
				),
				start=Start.from_ooxml_val(
					v=level.xpath_query("./w:start/@w:val", singleton=True), must_default=must_default
				),
				restart=Restart.from_ooxml_val(
					v=level.xpath_query("./w:lvlRestart/@w:val", singleton=True), must_default=must_default
				)
			)

		if must_default:
			return cls.default()
		
		return cls()

	@classmethod
	def aggregate_ooxml(cls, agg: Optional[LevelStyleProperties], add: Optional[LevelStyleProperties]) -> LevelProperties:
		match agg is not None, add is not None:
			case True, True:
				return cls.default()
			case True, False:
				return agg
			case False, True:
				return add
			case False, False:
				return cls.default() # TODO


class LevelProperties(ArbitraryBaseModel):
	level_style_properties: LevelStyleProperties

	run_style_properties: RunStyleProperties
	paragraph_style_properties: ParagraphStyleProperties

	@classmethod
	def default(cls) -> LevelProperties:
		return cls(
			level_style_properties=LevelStyleProperties.default(),
			run_style_properties=RunStyleProperties.default(),
			paragraph_style_properties=ParagraphStyleProperties.default()
		)

	@classmethod
	def from_ooxml(
		cls, level: Optional[OOXML_NUMBERINGS.Level], must_default: bool=False
	) -> LevelProperties:
		if level is not None:
			return cls(
				level_style_properties=LevelStyleProperties.from_ooxml(level=level, must_default=must_default),
				run_style_properties=RunStyleProperties.from_ooxml(
					run_properties=level.run_properties, must_default=must_default
				),
				paragraph_style_properties=ParagraphStyleProperties.from_ooxml(
					paragraph_properties=level.paragraph_properties, must_default=must_default
				)
			)

		if must_default:
			return cls.default()
		
		return cls()
	
	@classmethod
	def aggregate_ooxml(cls, agg: Optional[LevelProperties], add: Optional[LevelProperties], default_style: Style) -> LevelProperties:
		return cls(
			level_style_properties=LevelStyleProperties.aggregate_ooxml(
				agg=agg.level_style_properties if agg is not None else None,
				add=add.level_style_properties if add is not None else None
			),
			run_style_properties=RunStyleProperties.aggregate_ooxml(
				agg=agg.run_style_properties if agg is not None else default_style.properties.run_style_properties,
				add=add.run_style_properties if add is not None else default_style.properties.run_style_properties,
				default=default_style.properties.run_style_properties
			),
			paragraph_style_properties=ParagraphStyleProperties.aggregate_ooxml(
				agg=agg.paragraph_style_properties if agg is not None else default_style.properties.paragraph_style_properties,
				add=add.paragraph_style_properties if add is not None else default_style.properties.paragraph_style_properties,
			)
		)


class Numbering(ArbitraryBaseModel):
	id: int

	levels: dict[int, LevelProperties]

	parent: Optional[Numbering] = None
	children: Optional[list[Numbering]] = None
