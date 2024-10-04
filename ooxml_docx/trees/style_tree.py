from __future__ import annotations
from pydantic import Field, model_validator, field_validator, computed_field
from typing import Optional, Literal, Any

from lxml.etree import _Element as etreeElement

from ooxml_docx.trees.common import rPr, pPr, tblPr, tblStylePr, trPr, tcPr, numPr, Style, RunStyle, ParagraphStyle, TableStyle, NumberingStyle
from utils.etree import local_name, element_skeleton, xpath_query
from utils.pydantic import ArbitraryBaseModel


class DocDefaults(Style):
	"""

	:param Style: Inherits attributes from Style.
	"""
	default_paragraph_properties: Optional[pPr] = None
	default_run_properties: Optional[rPr] = None

	@model_validator(mode="before")
	def property_required(cls, values: dict[str, Any]) -> dict[str, Any]:
		if not any(values.get(attr) for attr
			in ("default_paragraph_properties", "default_run_properties")
		):
			raise ValueError("<DocDefaults> must at least include either 'default_paragraph_properties' (<pPr>) or 'default_run_properties' (<rPr>)")
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
	it can be divided into 4 style trees inheriting from style roots of each type:
	->	Run, Paragraph, Table or Numbering
	(Numbering style types are treated in the OoxmlDocxNumberingTree).
	"""
	doc_defaults: Optional[DocDefaults] = None
	latent_styles: Optional[LatentStyles] = None

	# OOXML Styles element root styles.
	# Note that it avoids using a mutable default list which can lead to unintended behavior,
	# using pydantic list field generator instead.
	run_root_styles: list[RunStyle] = Field(default_factory=list)
	paragraph_root_styles: list[ParagraphStyle] = Field(default_factory=list)
	table_root_styles: list[TableStyle] = Field(default_factory=list)
	numbering_root_styles: list[NumberingStyle] = Field(default_factory=list)

	# Save metadata information as well as elements that are not explicitly parsed
	element_skeleton: etreeElement
	skipped_elements: Optional[list[etreeElement]] = None # mainly numbering styles

	@classmethod
	def build(cls, ooxml_styles_part: etreeElement) -> OoxmlDocxStyleTree:
		"""_summary_

		:return: _description_
		"""
		return OoxmlDocxStyleTreeInterface(ooxml_styles_part=ooxml_styles_part).style_tree()

	def find(self, id: str, type: Optional[Literal["run", "paragraph", "table", "numbering"]] = None) -> Optional[Style]:
		"""_summary_

		Because ids are assumed to be unique, this function will return the first match,
		 in the case where no style type is specified it will search in the following order:
		 run > paragraph > table > numbering

		:param id: _description_
		:param type: _description_
		:return: _description_
		"""
		
		search_tree_roots: list[Style] = []
		match type:
			case "run":
				search_tree_roots = self.run_root_styles
			case "paragraph":
				search_tree_roots = self.paragraph_root_styles
			case "table":
				search_tree_roots = self.table_root_styles
			case "numbering":
				search_tree_roots = self.numbering_root_styles
			case _:
				# Append all the style tree roots types into a single one
				search_tree_roots = (
					self.run_root_styles 
					+ self.paragraph_root_styles 
					+ self.table_root_styles 
					+ self.numbering_root_styles
				)
		
		for style in search_tree_roots:
			search_result: Optional[Style] = self._find(id=id, style=style)
			if search_result is not None:
				return search_result
		# No match found
		return None
	
	def _find(self, id: str, style: Style) -> Optional[Style]:
		"""
		Searches the given id inside the given tree and returns the matching style found.
		If no matches where found, returns None.

		:param id: _description_
		:param tree: _description_
		:return: _description_
		"""
		if style.id == id:
			return style
		if style.children is None or len(style.children) == 0:
			return None

		for child_style in style.children:
			search_result: Optional[Style] = self._find(id=id, style=child_style)
			if search_result is not None:
				return search_result

	def __str__(self) -> str:
		s = "\u274B \033[1m'Style Tree'\033[0m ("
		s += f"docDefaults={'y' if self.doc_defaults is not None else 'n'}, "
		s += f"latentStyles={'y' if self.latent_styles is not None else 'n'}"
		s += ")\n"

		# Compute tree string representations of roots
		s += self._run_root_styles_str()
		s += self._paragraph_root_styles_str()
		s += self._table_root_styles_str()
		s += self._numbering_root_styles_str()

		return s
	
	def _run_root_styles_str(self) -> str:
		"""
		:return: _description_
		"""
		s = ""

		if len(self.run_root_styles) > 0:
			other_root_styles_empty = (
				len(self.paragraph_root_styles) == 0 
				and len(self.table_root_styles) == 0
				and len(self.numbering_root_styles) == 0
			)

			# Run root styles header
			arrow = (
				" \u2514\u2500\u2500\u25BA" if other_root_styles_empty
				else " \u251c\u2500\u2500\u25BA"
			)
			s += f"{arrow}\u274B 'Run Style Tree' ("
			s += f"n.roots={len(self.run_root_styles)}"
			s += ")\n"

			# Compute string representation for each run root style
			for i, run_style_root in enumerate(self.run_root_styles):
				s += run_style_root._custom_str_(
					depth=3, last=i==len(self.run_root_styles)-1,
					line_state=[not other_root_styles_empty]
				)
		
		return s
			
	def _paragraph_root_styles_str(self) -> str:
		"""
		:return: _description_
		"""
		s = ""

		if len(self.paragraph_root_styles) > 0:
			other_root_styles_empty = (
				len(self.table_root_styles) == 0 and len(self.numbering_root_styles) == 0
			)

			# Paragraph root styles header
			arrow = (
				" \u2514\u2500\u2500\u25BA" if other_root_styles_empty
				else " \u251c\u2500\u2500\u25BA"
			)
			s += f"{arrow}\u274B 'Paragraph Style Tree' ("
			s += f"n.roots={len(self.paragraph_root_styles)}"
			s += ")\n"
			
			# Compute string representation for each paragraph root style
			for i, paragraph_style_root in enumerate(self.paragraph_root_styles):
				s += paragraph_style_root._custom_str_(
					depth=3, last=i==len(self.paragraph_root_styles)-1,
					line_state=[not other_root_styles_empty]
				)
		
		return s

	def _table_root_styles_str(self) -> str:
		"""
		:return: _description_
		"""
		s = ""

		if len(self.table_root_styles) > 0:
			other_root_styles_empty = len(self.numbering_root_styles) == 0
			

			# Table root styles header
			arrow = (
				" \u2514\u2500\u2500\u25BA" if other_root_styles_empty
				else " \u251c\u2500\u2500\u25BA"
			)
			s += f"{arrow}\u274B 'Table Style Tree' ("
			s += f"n.roots={len(self.table_root_styles)}"
			s += ")\n"

			# Compute string representation for each table root style
			for i, table_style_root in enumerate(self.table_root_styles):
				s += table_style_root._custom_str_(
					depth=2, last=i==len(self.table_root_styles)-1,
					line_state=[not other_root_styles_empty]
				)
		
		return s
	
	def _numbering_root_styles_str(self) -> str:
		"""
		:return: _description_
		"""
		s = ""

		if len(self.numbering_root_styles) > 0:
			# Numbering root styles header
			s += f" \u2514\u2500\u2500\u25BA\u274B 'Numbering Style Tree' ("
			s += f"n.roots={len(self.numbering_root_styles)}"
			s += ")\n"

			# Compute string representation for each run root style
			for i, numbering_style_root in enumerate(self.numbering_root_styles):
				s += numbering_style_root._custom_str_(
					depth=3, last=i==len(self.numbering_root_styles)-1,
					line_state=[False]
				)
		
		return s


class OoxmlDocxStyleTreeInterface(ArbitraryBaseModel):
	"""
	Auxiliary class used to compute the style tree from the OOXML styles part
	"""
	ooxml_styles_part: etreeElement

	def style_tree(self) -> OoxmlDocxStyleTree:
		"""_summary_

		
		"""
		
		doc_defaults: DocDefaults = self._parse_doc_defaults()
		latent_styles: LatentStyles = self._parse_latent_styles()
		run_root_styles, paragraph_root_styles, table_root_styles, numbering_root_styles = self._compute_style_trees()

		return OoxmlDocxStyleTree(
			doc_defaults=doc_defaults,
			latent_styles=latent_styles,
			run_root_styles=run_root_styles,
			paragraph_root_styles=paragraph_root_styles,
			table_root_styles=table_root_styles,
			numbering_root_styles=numbering_root_styles,
			element_skeleton=element_skeleton(self.ooxml_styles_part),
			skipped_elements=xpath_query(
				element=self.ooxml_styles_part,
				query="./*[not(self::w:docDefaults or self::w:latentStyles or (self::w:style and (@type='run' or @type='paragraph' or @type='table')))]"
			)
		)
	
	def _parse_doc_defaults(self) -> Optional[DocDefaults]:
		"""_summary_

		:return: _description_
		"""
		doc_defaults: Optional[etreeElement] = xpath_query(
			element=self.ooxml_styles_part, query="./w:docDefaults", singleton=True
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

		return DocDefaults(
			id="DocDefaultStyle", name="Doc Default Style",
			default_paragraph_properties=pPr(element=default_pPr)
			if default_pPr is not None else None,
			default_run_properties=rPr(element=default_rPr)
			if default_rPr is not None else None,
			element_skeleton=element_skeleton(doc_defaults)
		)
	
	def _parse_latent_styles(self) -> Optional[LatentStyles]:
		"""_summary_

		:return: _description_
		"""
		latent_styles: Optional[etreeElement] = xpath_query(
			element=self.ooxml_styles_part, query="./w:latentStyles", singleton=True
		)
		if latent_styles is None:
			return None

		return LatentStyles(element=latent_styles)

	def _compute_style_trees(self) -> tuple[list[RunStyle], list[ParagraphStyle], list[TableStyle]]:
		"""_summary_

		:return: _description_
		"""

		run_styles: Optional[list[etreeElement]] = xpath_query(
			element=self.ooxml_styles_part, query="./w:style[@w:type='character']"
		)
		run_root_styles = None
		if run_styles is not None:
			run_root_styles = self._compute_style_tree(
				styles=run_styles, styles_type="run"
			)
		
		paragraph_styles: Optional[list[etreeElement]] = xpath_query(
			element=self.ooxml_styles_part, query="./w:style[@w:type='paragraph']"
		)
		paragraph_root_styles = None
		if paragraph_styles is not None:
			paragraph_root_styles = self._compute_style_tree(
				styles=paragraph_styles, styles_type="paragraph"
			)
		
		table_styles: Optional[list[etreeElement]] = xpath_query(
			element=self.ooxml_styles_part, query="./w:style[@w:type='table']"
		)
		table_root_styles = None
		if table_styles is not None:
			table_root_styles = self._compute_style_tree(
				styles=table_styles, styles_type="table"
			)
		
		numbering_styles: Optional[list[etreeElement]] = xpath_query(
			element=self.ooxml_styles_part, query="./w:style[@w:type='numbering']"
		)
		numbering_root_styles = None
		if numbering_styles is not None:
			numbering_root_styles = self._compute_style_tree(
				styles=numbering_styles, styles_type="numbering"
			)

		return run_root_styles, paragraph_root_styles, table_root_styles, numbering_root_styles

	def _compute_style_tree(self, styles: list[etreeElement], styles_type: Literal["run", "paragraph", "table", "numbering"]) -> list[Style]:
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
	
	def _parse_style_information(self, style: etreeElement, styles_type: Literal["run", "paragraph", "table", "numbering"]) -> tuple[Style, str]:
		"""_summary_

		:param style: _description_
		:param styles_type: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		
		# Capture general style attributes and child elements
		id: str = str(xpath_query(
			element=style, query="./@w:styleId", singleton=True, nullable=False
		))
		name: Optional[str] = xpath_query(element=style, query="./w:name/@w:val", singleton=True)
		if name is not None:
			name = str(name)
		parent_id: Optional[str] = xpath_query(
			element=style, query="./w:basedOn/@w:val", singleton=True
		)
		if parent_id is not None:
			parent_id = str(parent_id)

		# Capture style type specific child elements and create correspondent style instance
		_style = None
		match styles_type:
			case "run":
				run_style_parse: dict[str, etreeElement | list[etreeElement]] = self._parse_run_style_information(
					run_style=style
				)
				_style: RunStyle = RunStyle(
					id=id, name=name,
					properties=rPr(element=run_style_parse["rPr"])
					if run_style_parse["rPr"] is not None else None,
					element_skeleton=run_style_parse["element_skeleton"],
					skipped_elements=run_style_parse["skipped_elements"]
				)
			case "paragraph":
				paragraph_style_parse: dict[str, etreeElement | list[etreeElement]] = self._parse_paragraph_style_information(
					paragraph_style=style
				)
				_style: ParagraphStyle = ParagraphStyle(
					id=id, name=name,
					properties=pPr(element=paragraph_style_parse["pPr"])
					if paragraph_style_parse["pPr"] is not None else None,
					run_properties=rPr(element=paragraph_style_parse["rPr"])
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
			case "numbering":
				numbering_style_parse: dict[str, etreeElement | list[etreeElement]] = self._parse_numbering_style_information(
					numbering_style=style
				)
				_style: NumberingStyle = NumberingStyle(
					id=id, name=name,
					properties=numPr(element=numbering_style_parse["numPr"])
					if numbering_style_parse["numPr"] is not None else None,
					element_skeleton=numbering_style_parse["element_skeleton"],
					skipped_elements=numbering_style_parse["skipped_elements"]
				)
			case _:
				raise ValueError(f"'styles_type'={styles_type} can only be string literal ('run', 'paragraph', 'table' or 'numbering)")

		return _style, parent_id	
	
	def _parse_run_style_information(self, run_style: etreeElement) -> dict[str, etreeElement | list[etreeElement]]:
		"""_summary_

		:param run_style: _description_
		:return: _description_
		"""

		return {
			"rPr": xpath_query(element=run_style, query="./w:rPr", singleton=True),
			"element_skeleton": element_skeleton(element=run_style),
			# Capture any other child element
			"skipped_elements": xpath_query(
				element=run_style,
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

	def _parse_numbering_style_information(self, numbering_style: etreeElement) -> dict[str, etreeElement | list[etreeElement]]:
		"""_summary_

		:param numbering_style: _description_
		:return: _description_
		"""

		return {
			"numPr": xpath_query(element=numbering_style, query="./w:pPr/w:numPr", singleton=True),
			"element_skeleton": element_skeleton(element=numbering_style),
			# Capture any other child element
			"skipped_elements": xpath_query(
				element=numbering_style,
				query="./*[not(self::w:name or self::w:basedOn or self::w:pPr/numPr)]"
			)
		}