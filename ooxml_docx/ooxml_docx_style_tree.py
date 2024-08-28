from __future__ import annotations
from pydantic import BaseModel, Field, model_validator, field_validator, computed_field
from typing import Optional, Literal, Any

# LXML
from lxml import etree
from lxml.etree import _Element as etreeElement


from ooxml_docx.ooxml import OoxmlPart
from utils.etree_element_aux import print_etree, local_name, element_skeleton, xpath_query


class ArbitraryBaseModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True


class Style(ArbitraryBaseModel):
	"""
	Represents a .docx style element
	"""
	id: str
	name: Optional[str] = None
	parent: Optional[Style] = None
	children: Optional[list[Style]] = None

	#
	element_skeleton: etreeElement
	skipped_elements: Optional[list[etreeElement]] = None


class rPr(ArbitraryBaseModel):
	element: Optional[etreeElement]

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

	@model_validator(mode="before")
	def property_required(cls, values: dict[str, Any]) -> dict[str, Any]:
		if values.get("properties") is None:
			print(
				"<CharacterStyle> does not include 'properties' (<rPr>)",
			)
		return values


class pPr(ArbitraryBaseModel):
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

	@model_validator(mode="before")
	def property_required(cls, values: dict[str, Any]) -> dict[str, Any]:
		if not any(values.get(attr) is not None for attr 
			in ("properties", "character_properties")
		):
			print(
				"<ParagraphStyle> does not include neither 'properties' (<pPr>) nor 'character_properties' (<rPr>)",
			)
		return values


class tblPr(ArbitraryBaseModel):
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "tblPr":
			raise ValueError("<tblPr> requires OOXML <w:tblPr> element")
		return value


class tblStylePr(ArbitraryBaseModel):
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "tblStylePr":
			raise ValueError("<tblStylePr> requires OOXML <w:tblStylePr> element")
		return value


class trPr(ArbitraryBaseModel):
	element: etreeElement

	@field_validator('element')
	def check_tag(cls, value: Any) -> Any:
		if local_name(element=value) != "trPr":
			raise ValueError("<trPr> requires OOXML <w:trPr> element")
		return value


class tcPr(ArbitraryBaseModel):
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

	@model_validator(mode="before")
	def property_required(cls, values: dict[str, Any]) -> dict[str, Any]:
		if not any(values.get(attr) is not None for attr 
			in ("properties", "conditional_properties", "row_properties", "cell_properties")
		):
			print(
				"<TableStyle> does not include neither 'properties', 'conditional_properties', 'row_properties' nor 'cell_properties'"
			)
		return values


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
	character_root_style: list[CharacterStyle] = Field(default_factory=list)
	paragraph_root_style: list[ParagraphStyle] = Field(default_factory=list)
	table_root_style: list[TableStyle] = Field(default_factory=list)

	# Save metadata information as well as elements that are not explicitly parsed
	element_skeleton: etreeElement
	skipped_elements: list[etreeElement] = Field(default_factory=list) # mainly numbering styles


class OoxmlDocxStyleTreeInterface(ArbitraryBaseModel):
	"""
	"""
	ooxml_styles_part_element: etreeElement

	@computed_field
	@property
	def style_tree(self) -> OoxmlDocxStyleTree:
		"""_summary_

		
		"""
		print("docDefaults")
		print(self._parse_doc_defaults())

		print("latentStyles")
		print(self._parse_latent_styles())

		print("styles")
		print(self._compute_style_trees())

		return OoxmlDocxStyleTree(
			element_skeleton=element_skeleton(self.ooxml_styles_part_element)
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
			character_style_roots = self._compute_style_tree(
				styles=character_styles, styles_type="character"
			)
		
		paragraph_styles: Optional[list[etreeElement]] = xpath_query(
			element=self.ooxml_styles_part_element, query="./w:style[@w:type='paragraph']"
		)
		if paragraph_styles is not None:
			paragraph_style_roots = self._compute_style_tree(
				styles=paragraph_styles, styles_type="paragraph"
			)
		
		table_styles: Optional[list[etreeElement]] = xpath_query(
			element=self.ooxml_styles_part_element, query="./w:style[@w:type='table']"
		)
		if table_styles is not None:
			table_style_roots = self._compute_style_tree(
				styles=table_styles, styles_type="table"
			)
		
		return None, None, None

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

if __name__ == "__main__":
	from ooxml_docx.ooxml_docx import OoxmlDocx
	a = OoxmlDocx(docx_file_path="test/cp2022_10a01.docx")
	x = OoxmlDocxStyleTreeInterface(ooxml_styles_part_element=a.word.parts["styles.xml"].element)
	x.style_tree