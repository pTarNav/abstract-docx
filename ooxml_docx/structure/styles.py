from __future__ import annotations
from typing import Optional, Any
from enum import Enum
from pydantic import model_validator

import re

from utils.pydantic import ArbitraryBaseModel

from rich.tree import Tree
from utils.printing import rich_tree_to_str

from ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from ooxml_docx.structure.properties import (
	RunProperties, ParagraphProperties, 
	TableProperties, TableConditionalProperties, TableRowProperties, TableCellProperties,
	NumberingProperties
)

class Style(OoxmlElement):
	"""
	Representation of an OOXML style element.
	An OOXML style is a named collection of content specific OOXML properties.
	Styles have a hierarchical structure, where one can construct a style (child) from another style (parent),
	 inheriting all the OOXML properties of the parent style.
	"""
	id: str
	name: Optional[str] = None
	parent: Optional[Style] = None
	children: Optional[list[Style]] = None

	@classmethod
	def parse(cls, ooxml_style: OoxmlElement) -> Style:
		"""
		Reads the contents of an OOXML style element.
		:param ooxml_style: Raw OOXML style element.
		:return: Parsed style representation.
		"""
		name: Optional[str] = ooxml_style.xpath_query(query="./w:name/@w:val", singleton=True)

		return cls(
			element=ooxml_style.element,
			id=str(ooxml_style.xpath_query(query="./@w:styleId", singleton=True, nullable=False)),
			name=str(name) if name is not None else None,
		)
	
	def fold(self, agg: list[Style]) -> list[Style]:
		"""_summary_

		:param agg: _description_
		:return: _description_
		"""
		agg.append(self)

		if self.children is not None:
			for child in self.children:
				agg = child.fold(agg=agg)
		
		return agg
	
	def __str__(self) -> str:
		return rich_tree_to_str(self._tree_str_())

	def _tree_str_(self) -> Tree:
		tree = Tree(f"[bold]{self.id}[/bold]: '{self.name if self.name is not None else ''}'")

		if self.children is not None:
			# Sort children names alphanumerically
			sorted_children = sorted(
				self.children, key=lambda x: (
					re.sub(r'[^a-zA-Z]+', '', x.name),
					int(re.search(r'(\d+)', x.name).group(1)) if re.search(r'(\d+)', x.name) else 0
				)
			)
			for children in sorted_children:
				tree.add(children._tree_str_())

		return tree


class DocDefaults(OoxmlElement):
	"""

	"""
	default_paragraph_properties: Optional[ParagraphProperties] = None
	default_run_properties: Optional[RunProperties] = None

	@model_validator(mode="before")
	def Properties_required(cls, values: dict[str, Any]) -> dict[str, Any]:
		if not any(values.get(attr) for attr
			in ("default_paragraph_properties", "default_run_properties")
		):
			raise ValueError((
				"<DocDefaults> must at least include either 'default_paragraph_properties' (<pPr>)"
				" or 'default_run_properties' (<rPr>)"
			))
		return values


class RunStyle(Style):
	"""
	Represents an OOXML run style.
	"""
	properties: Optional[RunProperties] = None

	# This attribute will be filled after the entire style tree is computed
	# (for easier access thanks to the .find() method)
	linked_paragraph_style: Optional[ParagraphStyle] = None  # Assumption: Only one paragraph style can be linked
	
	@classmethod
	def parse(cls, ooxml_style: OoxmlElement) -> RunStyle:
		"""_summary_

		:param ooxml_style: _description_
		:return: _description_
		"""
		ooxml_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./w:rPr", singleton=True)

		return cls(
			**Style.parse(ooxml_style=ooxml_style).model_dump(),
			properties=RunProperties(ooxml=ooxml_properties) if ooxml_properties is not None else None,
		)


class ParagraphStyle(Style):
	"""
	Represents an OOXML paragraph style.
	Which can contain both paragraph and run properties.
	"""
	properties: Optional[ParagraphProperties] = None
	run_properties: Optional[RunProperties] = None

	# These attributes will be filled after the entire style tree is computed
	next_paragraph_style: Optional[ParagraphStyle] = None
	# (for easier access thanks to the .find() method)
	linked_run_style: Optional[RunStyle] = None  # Assumption: Only one run style can be linked

	numbering: Optional["Numbering"] = None  # To avoid circular import hell
	indentation_level: Optional[int] = None

	@classmethod
	def parse(cls, ooxml_style: OoxmlElement) -> ParagraphStyle:
		"""_summary_

		:param ooxml_style: _description_
		:return: _description_
		"""
		ooxml_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./w:pPr", singleton=True)
		ooxml_run_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./w:rPr", singleton=True)

		return cls(
			**Style.parse(ooxml_style=ooxml_style).model_dump(),
			properties=ParagraphProperties(ooxml=ooxml_properties) if ooxml_properties is not None else None,
			run_properties=RunProperties(ooxml=ooxml_run_properties) if ooxml_run_properties is not None else None
		)


class TableStyle(Style):
	"""
	Represents an OOXML table style.
	Which can contain general and conditional table properties, as well as row and cell properties.
	"""
	properties: Optional[TableProperties] = None
	conditional_properties: Optional[TableConditionalProperties] = None
	row_properties: Optional[TableRowProperties] = None
	cell_properties: Optional[TableCellProperties] = None

	@classmethod
	def parse(cls, ooxml_style: OoxmlElement) -> TableStyle:
		"""_summary_

		:param ooxml_style: _description_
		:return: _description_
		"""
		ooxml_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./w:tbPr", singleton=True)
		ooxml_conditional_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./tblStylePr", singleton=True)
		ooxml_row_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./trPr", singleton=True)
		ooxml_cell_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./tcPr", singleton=True)

		return cls(
			**Style.parse(ooxml_style=ooxml_style).model_dump(),
			properties=TableProperties(ooxml=ooxml_properties) if ooxml_properties is not None else None,
			conditional_properties=TableConditionalProperties(
				ooxml=ooxml_conditional_properties
			) if ooxml_conditional_properties is not None else None,
			row_properties=TableRowProperties(ooxml=ooxml_row_properties) if ooxml_row_properties is not None else None,
			cell_properties=TableCellProperties(ooxml=ooxml_cell_properties) if ooxml_cell_properties is not None else None
		)


class _NumberingStyle(Style):
	"""
	Represents an OOXML numbering style.
	Which can contain numbering properties, and be inherited by or inherit abstract numbering definitions properties
	
	Important: Import NumberingStyle from ooxml_docx.numbering as this definition is incomplete!
	"""
	properties: Optional[NumberingProperties] = None

	@classmethod
	def parse(cls, ooxml_style: OoxmlElement) -> _NumberingStyle:
		"""_summary_

		:param ooxml_style: _description_
		:return: _description_
		"""
		# Note that numPr element will alway be wrapped inside a pPr element
		ooxml_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./w:pPr/w:numPr", singleton=True)

		return cls(
			**Style.parse(ooxml_style=ooxml_style).model_dump(),
			properties=NumberingProperties(ooxml=ooxml_properties) if ooxml_properties is not None else None,
		)


class OoxmlStyleTypes(Enum):
	RUN = "character"
	PARAGRAPH = "paragraph"
	TABLE = "table"
	NUMBERING = "numbering"


# Map to obtain the respective style class based on the enumeration
OOXML_STYLE_TYPES_CLASSES: dict[OoxmlStyleTypes, type[Style]] = {
	OoxmlStyleTypes.RUN: RunStyle,
	OoxmlStyleTypes.PARAGRAPH: ParagraphStyle,
	OoxmlStyleTypes.TABLE: TableStyle,
	OoxmlStyleTypes.NUMBERING: _NumberingStyle
}


class OoxmlStylesRoots(ArbitraryBaseModel):
	run: list[RunStyle] = []
	paragraph: list[ParagraphStyle] = []
	table: list[TableStyle] = []
	numbering: list[_NumberingStyle] = []

	@classmethod
	def build(cls, ooxml_styles_part: OoxmlElement) -> OoxmlStylesRoots:
		"""_summary_

		:param ooxml_styles_part: _description_
		:return: _description_
		"""
		return cls(
			run=cls._parse_style_tree(ooxml_styles_part=ooxml_styles_part, style_type=OoxmlStyleTypes.RUN),
			paragraph=cls._parse_style_tree(ooxml_styles_part=ooxml_styles_part, style_type=OoxmlStyleTypes.PARAGRAPH),
			table=cls._parse_style_tree(ooxml_styles_part=ooxml_styles_part, style_type=OoxmlStyleTypes.TABLE),
			numbering=cls._parse_style_tree(ooxml_styles_part=ooxml_styles_part, style_type=OoxmlStyleTypes.NUMBERING)
		)

	@staticmethod
	def _parse_style_tree(ooxml_styles_part: OoxmlPart, style_type: OoxmlStyleTypes) -> list[Style]:
		"""_summary_

		:param ooxml_styles_part: _description_
		:param style_type: _description_
		:raises KeyError: _description_
		:return: _description_
		"""
		filtered_ooxml_styles: Optional[list[OoxmlElement]] = ooxml_styles_part.ooxml.xpath_query(
			query=f"./w:style[@w:type='{style_type.value}']"
		)
		if filtered_ooxml_styles is None:
			return []

		tree_map: dict[str, Style] = {}
		roots: list[Style] = []
		_unconnected: list[tuple[Style, str]] = []  # Style and its parent style id
		for ooxml_style in filtered_ooxml_styles:
			style: Style = OOXML_STYLE_TYPES_CLASSES[style_type].parse(ooxml_style=ooxml_style)
			parent_id: Optional[str] = style.xpath_query(query="./w:basedOn/@w:val", singleton=True)

			# Create style tree hashmap entry
			tree_map[style.id] = style

			if parent_id is None:
				# Style tree root
				roots.append(style)
			else:
				parent_id = str(parent_id)
				if parent_id not in tree_map.keys():
					# Cases where the parent has not been yet initialized in the style tree hashmap
					_unconnected.append((style, parent_id))  
				else:
					# Update inheritance relationship if parent has been initialized
					if tree_map[parent_id].children is None:
						tree_map[parent_id].children = []
					tree_map[parent_id].children.append(style)
					style.parent = tree_map[parent_id]

		# Connect any remaining styles where the child style was initialized before the parent style
		for style, parent_id in _unconnected:
			if parent_id not in tree_map.keys():
				raise KeyError(f"Parent style '{parent_id}' not found in styles")
			# Update inheritance relationship
			if tree_map[parent_id].children is None:
				tree_map[parent_id].children = []
			tree_map[parent_id].children.append(style)
			style.parent = tree_map[parent_id]

		# In the case of paragraph styles, connect the necessary paragraphs indicated by the next attribute
		if style_type is OoxmlStyleTypes.PARAGRAPH:
			for paragraph_style_id, paragraph_style in tree_map.items():
				next_id: Optional[str] = paragraph_style.xpath_query(query="./w:next/@w:val", singleton=True)
				if next_id is not None:
					if next_id not in tree_map.keys():
						raise KeyError(f"Next paragraph style '{next_id}' not found in styles")
					# Update next relationship
					tree_map[paragraph_style_id].next_paragraph_style = tree_map[next_id]

		return roots

	def __str__(self) -> str:
		return rich_tree_to_str(self._tree_str_())

	def _tree_str_(self) -> Tree:
		tree = Tree(":artist_palette: [bold cyan]Styles[/bold cyan]")
		
		run_styles_tree = tree.add("[bold cyan]Run styles[/bold cyan]")
		for i, style in enumerate(self.run):
			run_styles_tree.add(style._tree_str_())

		paragraph_styles_tree = tree.add("[bold cyan]Paragraph styles[/bold cyan]")
		for i, style in enumerate(self.paragraph):
			paragraph_styles_tree.add(style._tree_str_())

		table_styles_tree = tree.add("[bold cyan]Table styles[/bold cyan]")
		for i, style in enumerate(self.table):
			table_styles_tree.add(style._tree_str_())

		numbering_styles_tree = tree.add("[bold cyan]Numbering styles[/bold cyan]")
		for i, style in enumerate(self.numbering):
			numbering_styles_tree.add(style._tree_str_())

		return tree


class OoxmlStyles(ArbitraryBaseModel):
	"""
	Represents the .docx document style tree (which stores information about styles and their hierarchy).
	Which essentially consists in:
		- Default style: Default set of formatting properties,
		 which are inherited by all the paragraphs and runs inside the document.
		If the element is not included in the part, the Word application itself defines it.
		- Latent styles: References to style definitions, mainly used by the Word application to provide information
		 on certain behaviors of styles and the styles section display of the user interface.
		If the element is not included in the part, the Word application itself defines it.
		(Stored as raw OOXML as it is not relevant for the use-case).
		- Styles: Definition of the set of formatting properties as well as metadata information.
		Moreover, each one of the styles defined can be related through an inheritance mechanism.
		Because the style type of both parent and child style must match, it can be divided into 4
	 	style trees inheriting from style roots of each type: Run, Paragraph, Table or Numbering
		(Numbering style types are treated in the OoxmlDocxNumbering section).
	"""
	doc_defaults: Optional[DocDefaults] = None
	latent_styles: Optional[OoxmlElement] = None

	roots: OoxmlStylesRoots

	@classmethod
	def build(cls, ooxml_styles_part: OoxmlPart) -> OoxmlStyles:
		"""_summary_

		:param ooxml_styles_part: _description_
		:return: _description_
		"""
		ooxml_styles: OoxmlStyles = cls(
			doc_defaults=cls._parse_doc_defaults(ooxml_styles_part=ooxml_styles_part),
			latent_styles=ooxml_styles_part.ooxml.xpath_query(query="./w:latentStyles", singleton=True),
			roots=OoxmlStylesRoots.build(ooxml_styles_part=ooxml_styles_part)
		)
		ooxml_styles.link_run_and_paragraph_styles()

		return ooxml_styles
	
	@staticmethod
	def _parse_doc_defaults(ooxml_styles_part: OoxmlPart) -> Optional[DocDefaults]:
		"""_summary_

		:param ooxml_styles_part: _description_
		:return: _description_
		"""
		ooxml_doc_defaults: Optional[OoxmlElement] = ooxml_styles_part.ooxml.xpath_query(query="./w:docDefaults", singleton=True)
		if ooxml_doc_defaults is None:
			return None

		#
		default_pPr: Optional[OoxmlElement] = ooxml_doc_defaults.xpath_query(query="./w:pPrDefault/w:pPr", singleton=True)
		default_rPr: Optional[OoxmlElement] = ooxml_doc_defaults.xpath_query(query="./w:rPrDefault/w:rPr", singleton=True)

		return DocDefaults(
			element=ooxml_doc_defaults.element,
			default_paragraph_properties=ParagraphProperties(ooxml=default_pPr) if default_pPr is not None else None,
			default_run_properties=RunProperties(ooxml=default_rPr) if default_rPr is not None else None
		)
	
	def find(self, id: str, type: Optional[OoxmlStyleTypes] = None) -> Optional[Style]:
		"""
		Helper function for searching a style based on its id and type inside the styles tree roots.

		Because ids are assumed to be unique, this function will return the first match,
		 where in the case where no style type is specified it will search in the following order:
			run > paragraph > table > numbering

		:param id: Id of the style being searched.
		:param type: Style type of the style being searched.
		:return: Result of the search, a single style object or None when no match is found.
		"""
		
		search_space: list[Style] = []
		match type:
			case OoxmlStyleTypes.RUN:
				search_space = self.roots.run
			case OoxmlStyleTypes.PARAGRAPH:
				search_space = self.roots.paragraph
			case OoxmlStyleTypes.TABLE:
				search_space = self.roots.table
			case OoxmlStyleTypes.NUMBERING:
				search_space = self.roots.numbering
			case _:
				# Append all the style tree roots types into a single one
				search_space = self.roots.run + self.roots.paragraph + self.roots.table + self.roots.numbering
		
		for root in search_space:
			search_result: Optional[Style] = self._find(id=id, root=root)
			if search_result is not None:
				return search_result  # Return the first match
		
		# No match found
		return None

	def _find(self, id: str, root: Style) -> Optional[Style]:
		"""
		Searches the given id inside the given tree and returns the matching style found.
		If no matches where found, returns None.

		:param id: Id of the style being searched.
		:param root: Style specific tree root being search on.
		:return: Result of the search, a single style object or None when no match is found.
		"""
		if root.id == id:
			return root
		if root.children is None or len(root.children) == 0:
			return None

		for style in root.children:
			search_result: Optional[Style] = self._find(id=id, root=style)
			if search_result is not None:
				return search_result
		
		return None
	
	def link_run_and_paragraph_styles(self) -> None:
		"""_summary_
		For there to exist a valid linkage the link property must exist in both styles being linked.
		There can only exist one link element to establish a single pairing between a paragraph style and a character style.
		Therefore, chain of linkages are not possible through this mechanism, only by inheritance itself:
			"<w:link> -> <w:basedOn> -> <w:link> -> ..."
		"""
		
		# Fold the tree structures of the paragraph styles roots into a traversable list
		folded_paragraph_styles_tree: list[ParagraphStyle] = []
		for paragraph_style_root in self.roots.paragraph:
			folded_paragraph_styles_tree = paragraph_style_root.fold(agg=folded_paragraph_styles_tree)
		
		for paragraph_style in folded_paragraph_styles_tree:
			linked_run_style_id: Optional[str] = paragraph_style.xpath_query(query="./w:link/@w:val", singleton=True)
			if linked_run_style_id is not None:
				linked_run_style: Optional[RunStyle] = self.find(id=linked_run_style_id, type=OoxmlStyleTypes.RUN)
				if linked_run_style is None:
					raise KeyError(f"Linked run style '{linked_run_style_id}' not found in styles")
				
				# Check that the run style also has a linkage reference to the current paragraph style
				linked_paragraph_style_id: Optional[str] = linked_run_style.xpath_query(query="./w:link/@w:val", singleton=True)
				if linked_paragraph_style_id is not None and linked_paragraph_style_id == paragraph_style.id:
					paragraph_style.linked_run_style = linked_run_style
					linked_run_style.linked_paragraph_style = paragraph_style

	def __str__(self) -> str:
		return self.roots.__str__()
