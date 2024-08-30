from __future__ import annotations
from pydantic import BaseModel, Field, model_validator, field_validator, computed_field
from typing import Optional, Literal, Any
import re

# LXML
from lxml import etree
from lxml.etree import _Element as etreeElement


from ooxml_docx.ooxml import OoxmlPart
from utils.etree_element_aux import print_etree, local_name, element_skeleton, xpath_query


class ArbitraryBaseModel(BaseModel):
	"""
	Auxiliary BaseModel class to avoid serialization error with etreeElement attributes.
	:param BaseModel: pydantic BaseModel
	"""

	class Config:
		arbitrary_types_allowed = True


class StyleProperties(ArbitraryBaseModel):
	"""
	Represents a .docx style properties element.
	"""
	element: etreeElement

	def __str__(self):
		etree.indent(tree=self.element, space="\t")
		return etree.tostring(self.element, pretty_print=True, encoding="utf8").decode("utf8")


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
		return self._custom_str()

	def _custom_str(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
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
		s = f"{arrow}\U0001F33F '{self.id}' ("

		if isinstance(self, CharacterStyle):
			s += self._character_style_header_str()
		if isinstance(self, ParagraphStyle):
			s += self._paragraph_style_header_str()
		if isinstance(self, TableStyle):
			s += self._table_style_header_str()

		s += ")\n"

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
				s += child._custom_str(
					depth=depth+1, last=i==len(sorted_children)-1,
					line_state=line_state[:]  # Pass-by-value
				)
		
		return s

	def _character_style_header_str(self) -> str:
		"""_summary_
		:return: _description_
		"""

		s = "type='character', "
		s += f"name='{self.name}', " if self.name is not None else ""
		s += f"n.children={len(self.children) if self.children is not None else 0}, "
		s += f"<rPr>?={'y' if self.properties is not None else 'n'}"

		return s
	
	def _paragraph_style_header_str(self) -> str:
		"""_summary_
		:return: _description_
		"""

		s = "type='paragraph', "
		s += f"name='{self.name}', " if self.name is not None else ""
		s += f"n.children={len(self.children) if self.children is not None else 0}, "
		s += f"<pPr>?={'y' if self.properties is not None else 'n'}, "
		s += f"<rPr>?={'y' if self.character_properties is not None else 'n'}"

		return s
	
	def _table_style_header_str(self) -> str:
		"""_summary_
		:return: _description_
		"""

		s = "type='table', "
		s += f"name='{self.name}', " if self.name is not None else ""
		s += f"n.children={len(self.children) if self.children is not None else 0}, "
		s += f"<tblPr>?={'y' if self.properties is not None else 'n'}, "
		s += f"<tblStylePr>?={'y' if self.conditional_properties is not None else 'n'}, "
		s += f"<trPr>?={'y' if self.row_properties is not None else 'n'}, "
		s += f"<tcPr>?={'y' if self.cell_properties is not None else 'n'}"

		return s

class rPr(StyleProperties):
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "rPr":
			raise ValueError("<rPr> requires OOXML <w:rPr> element")
		return value


class CharacterStyle(Style):
	"""
	Represents a .docx character style.
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[rPr] = None


class pPr(StyleProperties):
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "pPr":
			raise ValueError("<pPr> requires OOXML <w:pPr> element")
		return value


class ParagraphStyle(Style):
	"""
	Represents a .docx paragraph style. Which can contain both paragraph and character properties.
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[pPr] = None
	character_properties: Optional[rPr] = None


class tblPr(StyleProperties):
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "tblPr":
			raise ValueError("<tblPr> requires OOXML <w:tblPr> element")
		return value


class tblStylePr(StyleProperties):
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "tblStylePr":
			raise ValueError("<tblStylePr> requires OOXML <w:tblStylePr> element")
		return value


class trPr(StyleProperties):
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "trPr":
			raise ValueError("<trPr> requires OOXML <w:trPr> element")
		return value


class tcPr(StyleProperties):
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "tcPr":
			raise ValueError("<tcPr> requires OOXML <w:tcPr> element")
		return value


class TableStyle(Style):
	"""
	Represents a .docx paragraph style.
	Which can contain general and conditional table properties, as well as row and cell properties.
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[tblPr] = None
	conditional_properties: Optional[tblStylePr] = None
	row_properties: Optional[trPr] = None
	cell_properties: Optional[tcPr] = None


class DefaultStyle(Style):
	"""

	:param Style: Inherits attributes from Style.
	"""
	default_paragraph_properties: Optional[pPr] = None
	default_character_properties: Optional[rPr] = None

	@model_validator(mode="before")
	def property_required(cls, values: dict[str, Any]) -> dict[str, Any]:
		if not any(values.get(attr) for attr
			in ("default_paragraph_properties", "default_character_properties")
		):
			raise ValueError("<DefaultStyle> must at least include either 'default_paragraph_properties' (<pPr>) or 'default_character_properties' (<rPr>)")
		return values

class LatentStyles(ArbitraryBaseModel):
	"""
	Represent a .docx <w:latentStyles> element.
	Which is stored as the raw OOXML element.
	"""
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "latentStyles":
			raise ValueError("<LatentStyles> requires OOXML <w:latentStyles> element")
		return value


class OoxmlDocxStyleTree(ArbitraryBaseModel):
	"""
	Represents the .docx document style tree (which stores information about style hierarchy).
	Which essentially consists in:
	- Default style: Default set of formatting properties,
	which are inherited by all the paragraphs and runs inside the document.
	If the element is not included in the part, the Word application itself defines it.
	- Latent styles: References to style definitions,
	mainly used by the Word application to provide information
	on certain behaviors of styles and the styles section display of the user interface.
	If the element is not included in the part, the Word application itself defines it.
	- Styles: Definition of the set of formatting properties as well as metadata information.
	Moreover, each one of the styles defined can be related through an inheritance mechanism.
	Because the style type of both parent and child style must match,
	it can be divided into 3 style trees inheriting from style roots of each type:
	->	CharacterStyleRoots, ParagraphStyleRoots or TableStyleRoots
	(Numbering style types are treated in the OoxmlDocxNumberingTree).
	"""
	default_style: Optional[DefaultStyle] = None
	latent_styles: Optional[LatentStyles] = None

	# OOXML Styles element root styles.
	# Note that it avoids using a mutable default list which can lead to unintended behavior,
	# using pydantic list field generator instead.
	character_root_styles: list[CharacterStyle] = Field(default_factory=list)
	paragraph_root_styles: list[ParagraphStyle] = Field(default_factory=list)
	table_root_styles: list[TableStyle] = Field(default_factory=list)

	# Save metadata information as well as elements that are not explicitly parsed
	element_skeleton: etreeElement
	skipped_elements: Optional[list[etreeElement]] = None # mainly numbering styles

	def __str__(self) -> str:
		s = "\U0001F333 'Style Tree' ("
		s += f"docDefaults={'y' if self.default_style is not None else 'n'}, "
		s += f"latentStyles={'y' if self.latent_styles is not None else 'n'}"
		s += ")\n"
		
		if len(self.character_root_styles) > 0:
			# Character root styles header
			empty_paragraph_and_table_root_styles = (
				(len(self.paragraph_root_styles) == 0) and (len(self.table_root_styles) == 0)
			)

			arrow = (" \u2514\u2500\u2500\u25BA" if empty_paragraph_and_table_root_styles else " \u251c\u2500\u2500\u25BA")
			s += f"{arrow}\U0001F331 'Character Style Tree' ("
			s += f"n.roots={len(self.character_root_styles)}"
			s += ")\n"

			# Compute string representation for each character root style
			for i, character_style_root in enumerate(self.character_root_styles):
				s += character_style_root._custom_str(
					depth=3, last=i==len(self.character_root_styles)-1,
					line_state=[not empty_paragraph_and_table_root_styles]
				)
		
		if len(self.paragraph_root_styles) > 0:
			# Paragraph root styles header
			empty_table_root_styles = len(self.table_root_styles) == 0

			arrow = (" \u2514\u2500\u2500\u25BA" if empty_table_root_styles else " \u251c\u2500\u2500\u25BA")
			s += f"{arrow}\U0001F331 'Paragraph Style Tree' ("
			s += f"n.roots={len(self.paragraph_root_styles)}"
			s += ")\n"
			
			# Compute string representation for each paragraph root style
			for i, paragraph_style_root in enumerate(self.paragraph_root_styles):
				s += paragraph_style_root._custom_str(
					depth=3, last=i==len(self.paragraph_root_styles)-1,
					line_state=[not empty_table_root_styles]
				)

		if len(self.table_root_styles) > 0:
			# Table root styles header

			s += " \u2514\u2500\u2500\u25BA\U0001F331 'Table Style Tree' ("
			s += f"n.roots={len(self.table_root_styles)}"
			s += ")\n"

			# Compute string representation for each table root style
			for i, table_style_root in enumerate(self.table_root_styles):
				s += table_style_root._custom_str(
					depth=2, last=i==len(self.table_root_styles)-1, line_state=[False]
				)
		
		return s


class OoxmlDocxStyleTreeInterface(ArbitraryBaseModel):
	"""
	"""
	ooxml_styles_part_element: etreeElement

	@computed_field
	@property
	def style_tree(self) -> OoxmlDocxStyleTree:
		"""_summary_

		
		"""
		
		default_style: DefaultStyle = self._parse_doc_defaults()
		latent_styles: LatentStyles = self._parse_latent_styles()
		character_root_styles, paragraph_root_styles, table_root_styles = self._compute_style_trees()

		return OoxmlDocxStyleTree(
			default_style=default_style,
			latent_styles=latent_styles,
			character_root_styles=character_root_styles,
			paragraph_root_styles=paragraph_root_styles,
			table_root_styles=table_root_styles,
			element_skeleton=element_skeleton(self.ooxml_styles_part_element),
			skipped_elements=xpath_query(
				element=self.ooxml_styles_part_element,
				query="./*[not(self::w:docDefaults or self::w:latentStyles or (self::w:style and (@type='character' or @type='paragraph' or @type='table')))]"
			)
		)
	
	def _parse_doc_defaults(self) -> Optional[DefaultStyle]:
		"""_summary_

		:return: _description_
		"""
		doc_defaults: Optional[etreeElement] = xpath_query(
			element=self.ooxml_styles_part_element, query="./w:docDefaults", singleton=True
		)
		if doc_defaults is None:
			return None
		
		#
		default_pPr: Optional[etreeElement] = xpath_query(
			element=doc_defaults, query="./w:pPrDefault/w:pPr", singleton=True
		)
		default_rPr: Optional[etreeElement] = xpath_query(
			element=doc_defaults, query="./w:rPrDefault/w:rPr", singleton=True
		)

		return DefaultStyle(
			id="DocDefaultStyle", name="Doc Default Style",
			default_paragraph_properties=pPr(element=default_pPr)
			if default_pPr is not None else None,
			default_character_properties=rPr(element=default_rPr)
			if default_rPr is not None else None,
			element_skeleton=element_skeleton(doc_defaults)
		)
	
	def _parse_latent_styles(self) -> Optional[LatentStyles]:
		"""_summary_

		:return: _description_
		"""
		latent_styles: Optional[etreeElement] = xpath_query(
			element=self.ooxml_styles_part_element, query="./w:latentStyles", singleton=True
		)
		if latent_styles is None:
			return None

		return LatentStyles(element=latent_styles)

	def _compute_style_trees(self) -> tuple[list[CharacterStyle], list[ParagraphStyle], list[TableStyle]]:
		"""_summary_

		:return: _description_
		"""

		character_styles: Optional[list[etreeElement]] = xpath_query(
			element=self.ooxml_styles_part_element, query="./w:style[@w:type='character']"
		)
		if character_styles is not None:
			character_root_styles = self._compute_style_tree(
				styles=character_styles, styles_type="character"
			)
		
		paragraph_styles: Optional[list[etreeElement]] = xpath_query(
			element=self.ooxml_styles_part_element, query="./w:style[@w:type='paragraph']"
		)
		if paragraph_styles is not None:
			paragraph_root_styles = self._compute_style_tree(
				styles=paragraph_styles, styles_type="paragraph"
			)
		
		table_styles: Optional[list[etreeElement]] = xpath_query(
			element=self.ooxml_styles_part_element, query="./w:style[@w:type='table']"
		)
		if table_styles is not None:
			table_root_styles = self._compute_style_tree(
				styles=table_styles, styles_type="table"
			)
		
		return character_root_styles, paragraph_root_styles, table_root_styles

	def _compute_style_tree(self, styles: list[etreeElement], styles_type: Literal["character", "paragraph", "table"]) -> list[Style]:
		"""_summary_

		:param styles: _description_
		:return: _description_
		"""
		style_tree_hashmap: dict[str, Style] = {}
		style_tree_roots: list[Style] = []
		_unconnected_styles: list[tuple[Style, str]] = []
		for style in styles:
			# tuple[Style, str]
			_style, parent_id = self._parse_style_information(style=style, styles_type=styles_type)
			
			# Create style tree hashmap entry
			style_tree_hashmap[_style.id] = _style
			
			if parent_id is None:
				# Append to root if parent is None
				style_tree_roots.append(_style)
			else:
				if parent_id not in style_tree_hashmap.keys():
					# To connect nodes after parent has been initialized
					_unconnected_styles.append((_style, parent_id))  
				else:
					# Update inheritance relationship
					if style_tree_hashmap[parent_id].children is None:
						style_tree_hashmap[parent_id].children = []
					style_tree_hashmap[parent_id].children.append(_style)
					_style.parent = style_tree_hashmap[parent_id]
		
		# Connect any remaining styles where
		# the child style was initialized before the parent style
		for style, parent_id in _unconnected_styles:
			if parent_id not in style_tree_hashmap.keys():
				raise KeyError(f"Parent style '{parent_id}' not found in styles")
			# Update inheritance relationship
			if style_tree_hashmap[parent_id].children is None:
						style_tree_hashmap[parent_id].children = []
			style_tree_hashmap[parent_id].children.append(style)
			style.parent = style_tree_hashmap[parent_id]
		
		return style_tree_roots
	
	def _parse_style_information(self, style: etreeElement, styles_type: Literal["character", "paragraph", "table"]) -> tuple[Style, str]:
	
		# Capture general style attributes and child elements
		id: str = xpath_query(element=style, query="./@w:styleId", singleton=True, nullable=False)
		name: Optional[str] = xpath_query(
			element=style, query="./w:name/@w:val", singleton=True, nullable=False
		)
		parent_id: Optional[str] = xpath_query(element=style, query="./w:basedOn/@w:val", singleton=True)

		# Capture style type specific child elements and create correspondent style instance
		_style = None
		match styles_type:
			case "character":
				character_style_parse: dict[str, etreeElement | list[etreeElement]] = self._parse_character_style_information(
					character_style=style
				)
				_style: CharacterStyle = CharacterStyle(
					id=id, name=name,
					properties=rPr(element=character_style_parse["rPr"])
					if character_style_parse["rPr"] is not None else None,
					element_skeleton=character_style_parse["element_skeleton"],
					skipped_elements=character_style_parse["skipped_elements"]
				)
			case "paragraph":
				paragraph_style_parse: dict[str, etreeElement | list[etreeElement]] = self._parse_paragraph_style_information(
					paragraph_style=style
				)
				_style: ParagraphStyle = ParagraphStyle(
					id=id, name=name,
					properties=pPr(element=paragraph_style_parse["pPr"])
					if paragraph_style_parse["pPr"] is not None else None,
					character_properties=rPr(element=paragraph_style_parse["rPr"])
					if paragraph_style_parse["rPr"] is not None else None,
					element_skeleton=paragraph_style_parse["element_skeleton"],
					skipped_elements=paragraph_style_parse["skipped_elements"]
				)
			case "table":
				table_style_parse: dict[str, etreeElement | list[etreeElement]] = self._parse_table_style_information(
					table_style=style
				)
				_style: TableStyle = TableStyle(
					id=id, name=name,
					properties=tblPr(element=table_style_parse["tblPr"])
					if table_style_parse["tblPr"] is not None else None,
					conditional_properties=tblStylePr(element=table_style_parse["tblStylePr"])
					if table_style_parse["tblStylePr"] is not None else None,
					row_properties=trPr(element=table_style_parse["trPr"])
					if table_style_parse["trPr"] is not None else None,
					cell_properties=tcPr(element=table_style_parse["tcPr"])
					if table_style_parse["tcPr"] is not None else None,
					element_skeleton=table_style_parse["element_skeleton"],
					skipped_elements=table_style_parse["skipped_elements"]
				)
			case _:
				raise ValueError(f"'styles_type'={styles_type} can only be string literal ('character', 'paragraph' or 'table')")

		return _style, parent_id	
	
	def _parse_character_style_information(self, character_style: etreeElement) -> dict[str, etreeElement | list[etreeElement]]:
		"""_summary_

		:param character_style: _description_
		:return: _description_
		"""

		return {
			"rPr": xpath_query(element=character_style, query="./w:rPr", singleton=True),
			"element_skeleton": element_skeleton(element=character_style),
			# Capture any other child element
			"skipped_elements": xpath_query(
				element=character_style,
				query="./*[not(self::w:name or self::w:basedOn or self::w:rPr)]"
			)
		}
	
	def _parse_paragraph_style_information(self, paragraph_style: etreeElement) -> dict[str, etreeElement | list[etreeElement]]:
		"""_summary_

		:param paragraph_style: _description_
		:return: _description_
		"""

		return {
			"pPr": xpath_query(element=paragraph_style, query="./w:pPr", singleton=True),
			"rPr": xpath_query(element=paragraph_style, query="./w:rPr", singleton=True),
			"element_skeleton": element_skeleton(element=paragraph_style),
			# Capture any other child element
			"skipped_elements": xpath_query(
				element=paragraph_style,
				query="./*[not(self::w:name or self::w:basedOn or self::w:pPr or self::w:rPr)]"
			)
		}
	
	def _parse_table_style_information(self, table_style: etreeElement) -> dict[str, etreeElement | list[etreeElement]]:
		"""_summary_

		:param table_style: _description_
		:return: _description_
		"""

		return {
			"tblPr": xpath_query(element=table_style, query="./w:tblPr", singleton=True),
			"tblStylePr": xpath_query(element=table_style, query="./w:tblStylePr", singleton=True),
			"trPr": xpath_query(element=table_style, query="./w:trPr", singleton=True),
			"tcPr": xpath_query(element=table_style, query="./w:tcPr", singleton=True),
			"element_skeleton": element_skeleton(element=table_style),
			# Capture any other child element
			"skipped_elements": xpath_query(
				element=table_style,
				query="./*[not(self::w:name or self::w:basedOn or self::w:tblPr or self::w:tblStylePr or self::w:trPr or self::w:tcPr)]"
			)
		}
