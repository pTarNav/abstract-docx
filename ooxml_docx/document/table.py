from __future__ import annotations
from typing import Optional

from rich.tree import Tree
from utils.printing import rich_tree_to_str

from ooxml_docx.ooxml import OoxmlElement
from ooxml_docx.relationships import OoxmlRelationships
from ooxml_docx.structure.properties import TableProperties, TableRowProperties, TableCellProperties, NumberingProperties
from ooxml_docx.structure.styles import TableStyle, OoxmlStyles, OoxmlStyleTypes
from ooxml_docx.structure.numberings import NumberingStyle, Numbering, OoxmlNumberings
from ooxml_docx.document.paragraph import Paragraph


class TableCell(OoxmlElement):
	content: list[Paragraph | Table] = []
	properties: Optional[TableCellProperties] = None

	loc: Optional[tuple[int, int]] = None

	@classmethod
	def parse(
		cls, 
		ooxml_cell: OoxmlElement, 
		styles: OoxmlStyles, 
		numberings: OoxmlNumberings,
		relationships: OoxmlRelationships, 
		loc: Optional[tuple[int, int]] = None
	) -> TableCell:
		"""_summary_

		:param ooxml_cell: _description_
		:return: _description_
		"""
		properties: Optional[OoxmlElement] = ooxml_cell.xpath_query(query="./w:tcPr", singleton=True)

		return cls(
			element=ooxml_cell.element,
			content=cls._parse_content(
				ooxml_cell=ooxml_cell, styles=styles, numberings=numberings, relationships=relationships
			),
			properties=TableCellProperties(ooxml=properties) if properties is not None else None,
			loc=loc
		)
	
	@staticmethod
	def _parse_content(
		ooxml_cell: OoxmlElement, styles: OoxmlStyles, numberings: OoxmlNumberings, relationships: OoxmlRelationships
	) -> list[Paragraph | Table]:
		"""_summary_

		:param ooxml_cell: _description_
		:return: _description_
		"""
		ooxml_content: Optional[list[OoxmlElement]] = ooxml_cell.xpath_query(query="./w:p | ./w:tbl")
		if ooxml_content is None:
			return []
		
		content: list[Paragraph | Table] = []
		for ooxml_element in ooxml_content:
			match ooxml_element.local_name:
				case "p":
					element: Paragraph = Paragraph.parse(
						ooxml_paragraph=ooxml_element, styles=styles, numberings=numberings, relationships=relationships
					)
				case "tbl":
					element: Table = Table.parse(
						ooxml_table=ooxml_element, styles=styles, numberings=numberings, relationships=relationships
					)
				case _:
					raise ValueError("")  # TODO
			content.append(element)
		
		return content

	def __str__(self) -> str:
		return rich_tree_to_str(self._tree_str_())

	def _tree_str_(self) -> Tree:
		tree = Tree("table cell")
		return tree


class TableRow(OoxmlElement):
	cells: list[TableCell] = []
	properties: Optional[TableRowProperties] = None

	loc: Optional[int] = None

	@classmethod
	def parse(
		cls,
		ooxml_row: OoxmlElement,
		styles: OoxmlStyles,
		numberings: OoxmlNumberings,
		relationships: OoxmlRelationships,
		loc: Optional[int] = None
	) -> TableRow:
		"""_summary_

		:param ooxml_row: _description_
		:return: _description_
		"""
		properties: Optional[OoxmlElement] = ooxml_row.xpath_query(query="./w:trPr", singleton=True)
		
		return cls(
			element=ooxml_row.element,
			cells=cls._parse_cells(
				ooxml_row=ooxml_row, styles=styles, numberings=numberings, relationships=relationships, loc=loc
			),
			properties=TableRowProperties(ooxml=properties) if properties is not None else None,
			loc=loc
		)
	
	@staticmethod
	def _parse_cells(
		ooxml_row: OoxmlElement,
		styles: OoxmlStyles,
		numberings: OoxmlNumberings,
		relationships: OoxmlRelationships,
		loc: int
	) -> list[TableCell]:
		"""_summary_

		:param ooxml_row: _description_
		:return: _description_
		"""
		ooxml_cells: Optional[list[OoxmlElement]] = ooxml_row.xpath_query(query="./w:tc")
		if ooxml_cells is None:
			return []
		
		cells: list[TableCell] = []
		for i, ooxml_cell in enumerate(ooxml_cells):
			cells.append(TableCell.parse(
				ooxml_cell=ooxml_cell, styles=styles, numberings=numberings, relationships=relationships, loc=(loc, i)
			))
		
		return cells

	def __str__(self) -> str:
		raise rich_tree_to_str(self._tree_str_())

	def _tree_str_(self) -> Tree:
		tree = Tree("table row")
		return tree


class Table(OoxmlElement):
	rows: list[TableRow] = []

	properties: Optional[TableProperties] = None
	style: Optional[TableStyle] = None

	caption: Optional[str] = None

	numbering: Optional[Numbering] = None
	indentation_level: Optional[int] = None

	@classmethod
	def parse(
		cls, 
		ooxml_table: OoxmlElement, 
		styles: OoxmlStyles,
		numberings: OoxmlNumberings, 
		relationships: OoxmlRelationships
	) -> Table:
		"""_summary_

		:param ooxml_table: _description_
		:return: _description_
		"""
		properties: Optional[OoxmlElement] = ooxml_table.xpath_query(query="./w:tblPr", singleton=True)
		style: Optional[TableStyle] = cls._parse_style(ooxml_table=ooxml_table, styles=styles)

		numbering_parse_result: Optional[tuple[Numbering, int]] = cls._parse_numbering(
			ooxml_table=ooxml_table,
			style=style,  
			numberings=numberings
		)
		
		return cls(
			element=ooxml_table.element,
			rows=cls._parse_rows(ooxml_table=ooxml_table, styles=styles, numberings=numberings, relationships=relationships),
			properties=TableProperties(ooxml=properties) if properties is not None else None,
			style=cls._parse_style(ooxml_table=ooxml_table, styles=styles),
			caption=None, # TODO
			numbering=numbering_parse_result[0] if numbering_parse_result is not None else None,
			indentation_level=numbering_parse_result[1] if numbering_parse_result is not None else None
		)
	
	@staticmethod
	def _parse_rows(
		ooxml_table: OoxmlElement, styles: OoxmlStyles, numberings: OoxmlNumberings, relationships: OoxmlRelationships
	) -> list[TableRow]:
		"""_summary_

		:param ooxml_table: _description_
		:return: _description_
		"""
		ooxml_rows: Optional[list[OoxmlElement]] = ooxml_table.xpath_query(query="./w:tr")
		if ooxml_rows is None:
			return []
		
		rows: list[TableRow] = []
		for i, ooxml_row in enumerate(ooxml_rows):
			rows.append(TableRow.parse(
				ooxml_row=ooxml_row, styles=styles, numberings=numberings, relationships=relationships, loc=i
			))
		
		return rows
	
	@staticmethod
	def _parse_style(ooxml_table: OoxmlElement, styles: OoxmlStyles) -> Optional[TableStyle]:
		"""_summary_

		:param ooxml_table: _description_
		:param styles: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		style_id: Optional[str] = ooxml_table.xpath_query(query="./w:pPr/w:tblStyle/@w:val", singleton=True)
		if style_id is None:
			return None
		style_id = str(style_id)

		table_style_search_result: Optional[TableStyle] = styles.find(id=style_id, type=OoxmlStyleTypes.TABLE)
		if table_style_search_result is not None:
			return table_style_search_result

		raise ValueError(f"Undefined style reference for style id: {style_id}")
	
	@staticmethod
	def _parse_numbering(
			ooxml_table: OoxmlElement, style: Optional[TableStyle], numberings: OoxmlNumberings
		) -> Optional[tuple[Numbering, int]]:

		# ! TODO: more complicated than i thought

		return None

	def __str__(self) -> str:
		return rich_tree_to_str(self._tree_str_())
	
	def _tree_str_(self) -> Tree:
		# TODO
		tree = Tree("table")
		return tree