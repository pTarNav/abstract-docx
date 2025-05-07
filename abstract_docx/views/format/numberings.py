from __future__ import annotations
from typing import Optional
from enum import Enum

import re

from num2words import num2words
import roman

from utils.pydantic import ArbitraryBaseModel

import ooxml_docx.structure.numberings as OOXML_NUMBERINGS
from functools import cached_property

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
		
		# Ensure that any desired open and close brackets will be kept when .format() is applied
		v = v.replace("{", "{{")
		v = v.replace("}", "}}")

		# Replace %n with {n-1}
		def _replace(match: re.Match) -> str:
			level = int(match.group(1))
			return "{" + str(level - 1) + "}"

		return cls(re.sub(r"%(\d+)", _replace, v))
	
	def format(self, levels_strings: dict[int, str]) -> str:
		# Ensure that the levels_indexes has at least the highest level pattern
		
		placeholders = [int(idx) for idx in re.findall(r"\{(\d+)\}", self)]
		if not placeholders:
			return str(self)	

		if max(placeholders) not in levels_strings.keys():
			raise KeyError(f"Incomplete level indexes, missing at least {max(placeholders)=}")
		
		return super().format(*list(levels_strings.values()))


def to_letters(n: int) -> str:
	"""Convert a 1-based index to letters (A, B, ..., Z, AA, AB, ...)."""
	result = ""
	while n > 0:
		n, rem = divmod(n - 1, 26)
		char = chr(ord("A") + rem)
		result = char + result
	return result


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
		
		# TODO: for decimalEnclosedParen, make sure to treat marker pattern aswell
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

	def format(self, index: int) -> str:
		"""Return the formatted marker for a given 1-based index."""
		match self:
			case MarkerType.NONE:
				return ""
			case MarkerType.BULLET:
				return "·"
			case MarkerType.DECIMAL:
				return str(index)
			case MarkerType.DECIMAL_LEADING_ZERO:
				return f"{index:02}"
			case MarkerType.DECIMAL_ENCLOSED_CIRCLE:
				# Unicode circled numbers start at ① (U+2460) for 1
				code_point = 0x2460 + index - 1
				try:
					return chr(code_point)
				except ValueError:
					return str(index)
			case MarkerType.CARDINAL:
				return num2words(index, to='cardinal')
			case MarkerType.ORDINAL:
				return num2words(index, to='ordinal')
			case MarkerType.LOWER_LETTER:
				return to_letters(index).lower()
			case MarkerType.UPPER_LETTER:
				return to_letters(index).upper()
			case MarkerType.LOWER_ROMAN:
				return roman.toRoman(index).lower()
			case MarkerType.UPPER_ROMAN:
				return roman.toRoman(index).upper()
	
	def detection_regex(self) -> Optional[str]:
		match self:
			case MarkerType.NONE:
				return None
			case MarkerType.BULLET:
				return r"·"
			case MarkerType.DECIMAL:
				return r"\d+"
			case MarkerType.DECIMAL_LEADING_ZERO:
				return r"[[0\d]|[\d{2,}]]"  # TODO, the regex match grouping here is strange e.g "02" -> detects -> 0 only 
			case MarkerType.DECIMAL_ENCLOSED_CIRCLE:
				return r"[\u2460-\u2473]"
			case MarkerType.CARDINAL | MarkerType.ORDINAL:
				#TODO: this wont cut it
				return r"[A-Za-z]+"
			case MarkerType.LOWER_LETTER:
				return r"[a-z]+"
			case MarkerType.UPPER_LETTER:
				return r"[A-Z]+"
			case MarkerType.LOWER_ROMAN:
				return r"[ivxlcdm]+"
			case MarkerType.UPPER_ROMAN:
				return r"[IVXLCDM]+"


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
	
	def detection_regex(self) -> str:
		match self:
			case Whitespace.NONE:
				return r""
			case Whitespace.SPACE:
				return r" {1,2}"
			case Whitespace.TAB:
				return r"(?:\t| {3,})"


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


class LevelProperties(ArbitraryBaseModel):
	marker_pattern: Optional[MarkerPattern] = None
	marker_type: Optional[MarkerType] = None
	whitespace: Optional[Whitespace] = None
	start: Optional[Start] = None
	restart: Optional[Restart] = None

	@classmethod
	def default(cls) -> LevelProperties:
		return cls(
			marker_patter=MarkerPattern.default(),
			marker_type=MarkerType.default(),
			whitespace=Whitespace.default(),
			start=Start.default(),
			restart=Restart.default()
		)

	@classmethod
	def from_ooxml(cls, level: Optional[OOXML_NUMBERINGS.Level], must_default: bool=False) -> LevelProperties:
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
	def aggregate_ooxml(cls, agg: Optional[LevelProperties], add: Optional[LevelProperties]) -> LevelProperties:
		match agg is not None, add is not None:
			case True, True:
				return cls(
					marker_pattern=add.marker_pattern if add.marker_pattern is not None else agg.marker_pattern,
					marker_type=add.marker_type if add.marker_type is not None else agg.marker_type,
					whitespace=add.whitespace if add.whitespace is not None else agg.whitespace,
					start=add.start if add.start is not None else agg.start,
					restart=add.restart if add.restart is not None else agg.restart
				)
			case True, False:
				return agg
			case False, True:
				return add
			case _:
				# At least one of the level style properties will never be empty.
				# Because it would mean that it is trying to aggregate a level that neither of the numberings have.
				# If this happens something has terribly gone wrong.
				raise ValueError("")

class Level(ArbitraryBaseModel):
	id: int

	properties: LevelProperties
	style: Style


class Numbering(ArbitraryBaseModel):
	id: int

	levels: dict[int, Level]

	parent: Optional[Numbering] = None
	children: Optional[list[Numbering]] = None

	def format(self, level_indexes: dict[int, int]) -> str:
		if not all([lk in self.levels.keys() for lk in level_indexes.keys()]):
			raise KeyError("Unable to map") # TODO
		
		level_strings: dict[int, str] = {}
		for k, v in level_indexes.items():
			level_strings[k] = self.levels[k].properties.marker_type.format(index=v)
		
		return self.levels[max(level_indexes.keys())].properties.marker_pattern.format(levels_strings=level_strings)
	
	@cached_property
	def detection_regexes(self) -> dict[int, Optional[re.Pattern]]:
		level_indexes_regexes: dict[int, re.Pattern] = {}
		level_regexes: dict[int, Optional[re.Pattern]] = {}
		for k, v in self.levels.items():
			level_indexes_regexes[k] = v.properties.marker_type.detection_regex()

			if (
				v.properties.marker_pattern is not None
				 and v.properties.marker_type is not None
				 and v.properties.whitespace is not None
			):
				if v.properties.marker_pattern != "":
					marker_template_escaped = re.escape(v.properties.marker_pattern)
					_marker_templated_escaped = marker_template_escaped
					for _k in range(0, k+1):
						if level_indexes_regexes[_k] is not None:
							marker_template_escaped = marker_template_escaped.replace(r"\{" + str(_k) + r"\}", f"(?:{level_indexes_regexes[_k]})")	

					if marker_template_escaped != _marker_templated_escaped:
						level_regexes[k] = rf"^{marker_template_escaped}{v.properties.whitespace.detection_regex()}"
					else:
						level_regexes[k] = None
				else:
					level_regexes[k] = None
			else:
				raise ValueError("Cannot build detection regex with empty level properties.")

		return level_regexes

	def detect(self, text: "Text") -> dict[str, list[Level]]:  # Type hint as string to avoid circular import hell
		matches: dict[str, list[Level]] = {
			"regex_and_style": [],
			"regex_and_run_style_properties": [],
			"regex_and_paragraph_style_properties": [],
			"regex_only": []
		}
		
		detection_regexes: dict[int, Optional[re.Pattern]] = self.detection_regexes
		for level_id, level in self.levels.items():
			if detection_regexes[level_id] is not None:		
				match = re.match(self.detection_regexes[level_id], text.text)
				if match is not None:
					if level.style == text.style:
						matches["regex_and_style"].append(level)
					else:
						if level.style.properties.run_style_properties == text.style.properties.run_style_properties:
							matches["regex_and_run_style_properties"].append(level)
						elif level.style.properties.paragraph_style_properties == text.style.properties.paragraph_style_properties:
							matches["regex_and_paragraph_style_properties"].append(level)
						else:
							matches["regex_only"].append(level)
		
		return matches
		
		
