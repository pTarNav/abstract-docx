from __future__ import annotations
from typing import Optional, Any
from enum import Enum
from pydantic import model_validator
from utils.pydantic import ArbitraryBaseModel

import re

from ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from ooxml_docx.structure.properties import rPr, pPr, tblPr, tblStylePr, trPr, tcPr, numPr


class Style(OoxmlElement):
	"""_summary_

	:return: _description_
	"""
	id: str
	name: Optional[str] = None
	parent: Optional[Style] = None
	children: Optional[list[Style]] = None

	@classmethod
	def parse(cls, ooxml_style: OoxmlElement) -> Style:
		"""_summary_

		:param ooxml_style: _description_
		:return: _description_
		"""
		name: Optional[str] = ooxml_style.xpath_query(query="./w:name/@w:val", singleton=True)

		return cls(
			element=ooxml_style.element,
			id=str(ooxml_style.xpath_query(query="./@w:styleId", singleton=True, nullable=False)),
			name=str(name) if name is not None else None,
		)
	
	def __str__(self) -> str:
		return self._tree_str_()
	
	def _tree_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		"""
		Computes string representation of a style.

		:param depth: Indentation depth integer, defaults to 0.
		:param last: Package is the last one from the parent packages list, defaults to False.
		:param line_state: List of booleans indicating whether to include vertical connection for each previous indentation depth,
			defaults to None to avoid mutable list initialization unexpected behavior.
		:return: Package string representation.
		"""
		if line_state is None:
			line_state = []
		
		# Compute string representation of package header
		prefix = " " if depth > 0 else ""
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)
		s = f"{arrow} \033[1m{self.id}\033[0m: '{self.name if self.name is not None else ''}'\n"

		# Update the line state for the current depth
		if depth > 0:
			if depth >= len(line_state):
				line_state.append(not last)
			else:
				line_state[depth] = not last

		if self.children is not None:
			# Sort children names alphanumerically
			sorted_children = sorted(self.children, key=lambda x: (
					re.sub(r'[^a-zA-Z]+', '', x.name),
					int(re.search(r'(\d+)', x.name).group(1)) if re.search(r'(\d+)', x.name) else 0
			))

			for i, style in enumerate(sorted_children):
				s += style._tree_str_(
					depth=depth+1, last=i==len(self.children)-1, line_state=line_state[:]  # Pass-by-value
				)
		
		return s


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
			raise ValueError((
				"<DocDefaults> must at least include either 'default_paragraph_properties' (<pPr>)"
				" or 'default_run_properties' (<rPr>)"
			))
		return values


class RunStyle(Style):
	"""
	Represents a .docx run style.
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[rPr] = None

	@classmethod
	def parse(cls, ooxml_style: OoxmlElement) -> RunStyle:
		"""_summary_

		:param ooxml_style: _description_
		:return: _description_
		"""
		ooxml_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./w:rPr", singleton=True)

		return cls(
			**Style.parse(ooxml_style=ooxml_style).model_dump(),
			properties=rPr(ooxml=ooxml_properties) if ooxml_properties is not None else None,
		)


class ParagraphStyle(Style):
	"""
	Represents a .docx paragraph style. Which can contain both paragraph and run properties.
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[pPr] = None
	run_properties: Optional[rPr] = None

	@classmethod
	def parse(cls, ooxml_style: OoxmlElement) -> ParagraphStyle:
		"""_summary_

		:param ooxml_style: _description_
		:return: _description_
		"""
		ooxml_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./w:pPr", singleton=True)
		ooxml_run_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./rPr", singleton=True)

		return cls(
			**Style.parse(ooxml_style=ooxml_style).model_dump(),
			properties=pPr(ooxml=ooxml_properties) if ooxml_properties is not None else None,
			run_properties=rPr(ooxml=ooxml_run_properties) if ooxml_run_properties is not None else None
		)


class TableStyle(Style):
	"""
	Represents a .docx table style.
	Which can contain general and conditional table properties, as well as row and cell properties.
	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[tblPr] = None
	conditional_properties: Optional[tblStylePr] = None
	row_properties: Optional[trPr] = None
	cell_properties: Optional[tcPr] = None

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
			properties=tblPr(ooxml=ooxml_properties) if ooxml_properties is not None else None,
			conditional_properties=tblStylePr(
				ooxml=ooxml_conditional_properties
			) if ooxml_conditional_properties is not None else None,
			row_properties=trPr(ooxml=ooxml_row_properties) if ooxml_row_properties is not None else None,
			cell_properties=trPr(ooxml=ooxml_cell_properties) if ooxml_cell_properties is not None else None
		)


class NumberingStyle(Style):
	"""
	Represents a .docx numbering style.
	Which can contain numbering properties, and be inherited by or inherit abstract numbering definitions properties
	
	Important: Import NumberingStyle from ooxml_docx.numbering as this definition is incomplete!

	:param Style: Inherits attributes from Style.
	"""
	properties: Optional[numPr] = None

	@classmethod
	def parse(cls, ooxml_style: OoxmlElement) -> NumberingStyle:
		"""_summary_

		:param ooxml_style: _description_
		:return: _description_
		"""
		# Note that numPr element will alway be wrapped inside a pPr element
		ooxml_properties: Optional[OoxmlElement] = ooxml_style.xpath_query(query="./w:pPr/w:numPr", singleton=True)

		return cls(
			**Style.parse(ooxml_style=ooxml_style).model_dump(),
			properties=numPr(ooxml=ooxml_properties) if ooxml_properties is not None else None,
		)


class OoxmlStyleTypes(Enum):
	RUN = "character"
	PARAGRAPH = "paragraph"
	TABLE = "table"
	NUMBERING = "numbering"


OOXML_STYLE_TYPES_CLASSES: dict[OoxmlStyleTypes, type[Style]] = {
	OoxmlStyleTypes.RUN: RunStyle,
	OoxmlStyleTypes.PARAGRAPH: ParagraphStyle,
	OoxmlStyleTypes.TABLE: TableStyle,
	OoxmlStyleTypes.NUMBERING: NumberingStyle
}


class OoxmlStylesRoots(ArbitraryBaseModel):
	run: list[RunStyle] = []
	paragraph: list[ParagraphStyle] = []
	table: list[TableStyle] = []
	numbering: list[NumberingStyle] = []

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

		tree_hashmap: dict[str, Style] = {}
		roots: list[Style] = []
		_unconnected: list[tuple[Style, str]] = []  # Style and its parent style id
		for ooxml_style in filtered_ooxml_styles:
			style: Style = OOXML_STYLE_TYPES_CLASSES[style_type].parse(ooxml_style=ooxml_style)
			parent_id: Optional[str] = style.xpath_query(query="./w:basedOn/@w:val", singleton=True)

			# Create style tree hashmap entry
			tree_hashmap[style.id] = style

			if parent_id is None:
				# Style tree root
				roots.append(style)
			else:
				parent_id = str(parent_id)
				if parent_id not in tree_hashmap.keys():
					# Cases where the parent has not been yet initialized in the style tree hashmap
					_unconnected.append((style, parent_id))  
				else:
					# Update inheritance relationship if parent has been initialized
					if tree_hashmap[parent_id].children is None:
						tree_hashmap[parent_id].children = []
					tree_hashmap[parent_id].children.append(style)
					style.parent = tree_hashmap[parent_id]

		# Connect any remaining styles where the child style was initialized before the parent style
		for style, parent_id in _unconnected:
			if parent_id not in tree_hashmap.keys():
				raise KeyError(f"Parent style '{parent_id}' not found in styles")
			# Update inheritance relationship
			if tree_hashmap[parent_id].children is None:
				tree_hashmap[parent_id].children = []
			tree_hashmap[parent_id].children.append(style)
			style.parent = tree_hashmap[parent_id]
		
		return roots

	def __str__(self) -> str:
		s = "\033[36m\033[1mRun styles\033[0m\n"
		for i, style in enumerate(self.run):
			s += style._tree_str_(depth=1, last=i==len(self.run)-1)
		s += "\033[36m\033[1mParagraph styles\033[0m\n"
		for i, style in enumerate(self.paragraph):
			s += style._tree_str_(depth=1, last=i==len(self.paragraph)-1)
		s += "\033[36m\033[1mTable styles\033[0m\n"
		for i, style in enumerate(self.table):
			s += style._tree_str_(depth=1, last=i==len(self.table)-1)
		s += "\033[36m\033[1mNumbering styles\033[0m\n"
		for i, style in enumerate(self.numbering):
			s += style._tree_str_(depth=1, last=i==len(self.numbering)-1)
		return s


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
		return cls(
			doc_defaults=cls._parse_doc_defaults(ooxml_styles_part=ooxml_styles_part),
			latent_styles=ooxml_styles_part.ooxml.xpath_query(query="./w:latentStyles", singleton=True),
			roots=OoxmlStylesRoots.build(ooxml_styles_part=ooxml_styles_part)
		)
	
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
			id="__DocDefaults__",
			default_paragraph_properties=pPr(ooxml=default_pPr) if default_pPr is not None else None,
			default_run_properties=rPr(ooxml=default_rPr) if default_rPr is not None else None
		)
	
	def find(self, id: str, type: Optional[OoxmlStyleTypes] = None) -> Optional[Style]:
		"""_summary_

		Because ids are assumed to be unique, this function will return the first match,
		 where in the case where no style type is specified it will search in the following order:
			run > paragraph > table > numbering

		:param id: _description_
		:param type: _description_
		:return: _description_
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
				return search_result
		
		# No match found
		return None

	def _find(self, id: str, root: Style) -> Optional[Style]:
		"""
		Searches the given id inside the given tree and returns the matching style found.
		If no matches where found, returns None.

		:param id: _description_
		:param root: _description_
		:return: _description_
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

	def __str__(self) -> str:
		return self.roots.__str__()
