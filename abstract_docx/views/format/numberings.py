from __future__ import annotations
from typing import Optional
from enum import Enum

from colour import Color

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement
import ooxml_docx.structure.properties as OOXML_PROPERTIES

from abstract_docx.views.format.styles import RunStyleProperties, ParagraphStyleProperties

class MarkerPattern(str):

	@classmethod
	def default(cls) -> MarkerType:
		return cls("")  # TODO: investigate further

	@classmethod
	def from_ooxml_val(cls, v: Optional[str], must_default: bool=False) -> Optional[MarkerPattern]:
		if v is None:
			if not must_default:
				return None
			
			return cls.default()
		
		return ""	# TODO: parse %d with regex and prepare accordingly

		

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
	pass


class Restart(int):
	pass


class LevelProperties(ArbitraryBaseModel):
	marker_pattern: Optional[MarkerPattern] = None
	market_type: Optional[MarkerType] = None
	whitespace: Optional[Whitespace] = None
	start: Optional[Start] = None
	restart: Optional[Restart] = None


class NumberingProperties(ArbitraryBaseModel):
	level_properties: LevelProperties

	run_style_properties: RunStyleProperties
	paragraph_style_properties: ParagraphStyleProperties


class Numbering(ArbitraryBaseModel):
	id: int

	parent: Optional[Numbering] = None
	children: Optional[list[Numbering]] = None
	
	properties: NumberingProperties

	