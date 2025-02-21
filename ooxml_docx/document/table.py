from __future__ import annotations
from typing import Optional

from ooxml_docx.ooxml import OoxmlElement
from ooxml_docx.relationships import OoxmlRelationships
from ooxml_docx.structure.properties import TableProperties, TableRowProperties, TableCellProperties
from ooxml_docx.structure.styles import TableStyle, OoxmlStyles, OoxmlStyleTypes
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
			content=cls._parse_content(ooxml_cell=ooxml_cell, styles=styles, relationships=relationships),
			properties=TableCellProperties(ooxml=properties) if properties is not None else None,
			loc=loc
		)
	
	@staticmethod
	def _parse_content(
		ooxml_cell: OoxmlElement, styles: OoxmlStyles,relationships: OoxmlRelationships
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
						ooxml_paragraph=ooxml_element, styles=styles, relationships=relationships
					)
				case "tbl":
					element: Table = Table.parse(
						ooxml_table=ooxml_element, styles=styles, relationships=relationships
					)
				case _:
					raise ValueError("")  # TODO
			content.append(element)
		
		return content

	def __str__(self) -> str:
		return ""

	def _tree_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		line_state = line_state if line_state is not None else []
		
		# Compute string representation of cell header
		prefix = " " if depth > 0 else ""
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)
		s = f"{arrow} \033[1mCell\033[0m: {self.loc}\n"

		# Update the line state for the current depth
		if depth > 0:
			if depth >= len(line_state):
				line_state.append(not last)
			else:
				line_state[depth] = not last

		# Compute string representation of content
		for i, element in enumerate(self.content):
			s += element._tree_str_(depth=depth+1, last=i==len(self.content)-1, line_state=line_state[:])  # Pass-by-value

		return s	

class TableRow(OoxmlElement):
	cells: list[TableCell] = []
	properties: Optional[TableRowProperties] = None

	loc: Optional[int] = None

	@classmethod
	def parse(
		cls, ooxml_row: OoxmlElement, styles: OoxmlStyles, relationships: OoxmlRelationships, loc: Optional[int] = None
	) -> TableRow:
		"""_summary_

		:param ooxml_row: _description_
		:return: _description_
		"""
		properties: Optional[OoxmlElement] = ooxml_row.xpath_query(query="./w:trPr", singleton=True)
		
		return cls(
			element=ooxml_row.element,
			cells=cls._parse_cells(ooxml_row=ooxml_row, styles=styles, relationships=relationships, loc=loc),
			properties=TableRowProperties(ooxml=properties) if properties is not None else None,
			loc=loc
		)
	
	@staticmethod
	def _parse_cells(
		ooxml_row: OoxmlElement, styles: OoxmlStyles, relationships: OoxmlRelationships, loc: int
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
			cells.append(TableCell.parse(ooxml_cell=ooxml_cell, styles=styles, relationships=relationships, loc=(loc, i)))
		
		return cells

	def __str__(self) -> str:
		raise NotImplementedError("")

	def _tree_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		line_state = line_state if line_state is not None else []
		
		# Compute string representation of row header
		prefix = " " if depth > 0 else ""
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)
		s = f"{arrow} \033[1mRow\033[0m: {self.loc}\n"

		# Update the line state for the current depth
		if depth > 0:
			if depth >= len(line_state):
				line_state.append(not last)
			else:
				line_state[depth] = not last

		# Compute string representation of cells
		for i, cell in enumerate(self.cells):
			s += cell._tree_str_(depth=depth+1, last=i==len(self.cells)-1, line_state=line_state[:])  # Pass-by-value

		return s


class Table(OoxmlElement):
	rows: list[TableRow] = []

	properties: Optional[TableProperties] = None
	style: Optional[TableStyle] = None

	caption: Optional[str] = None

	@classmethod
	def parse(cls, ooxml_table: OoxmlElement, styles: OoxmlStyles, relationships: OoxmlRelationships) -> Table:
		"""_summary_

		:param ooxml_table: _description_
		:return: _description_
		"""
		properties: Optional[OoxmlElement] = ooxml_table.xpath_query(query="./w:tblPr", singleton=True)
		
		return cls(
			element=ooxml_table.element,
			rows=cls._parse_rows(ooxml_table=ooxml_table, styles=styles, relationships=relationships),
			properties=TableProperties(ooxml=properties) if properties is not None else None,
			style=cls._parse_style(ooxml_table=ooxml_table, styles=styles),
			caption=None
		)
	
	@staticmethod
	def _parse_rows(ooxml_table: OoxmlElement, styles: OoxmlStyles, relationships: OoxmlRelationships) -> list[TableRow]:
		"""_summary_

		:param ooxml_table: _description_
		:return: _description_
		"""
		ooxml_rows: Optional[list[OoxmlElement]] = ooxml_table.xpath_query(query="./w:tr")
		if ooxml_rows is None:
			return []
		
		rows: list[TableRow] = []
		for i, ooxml_row in enumerate(ooxml_rows):
			rows.append(TableRow.parse(ooxml_row=ooxml_row, styles=styles, relationships=relationships, loc=i))
		
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

	def __str__(self) -> str:
		return ""
	
	def _tree_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		if line_state is None:
			line_state = []
		
		# Compute string representation of table header
		prefix = " " if depth > 0 else ""
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)
		s = f"{arrow} \033[1mTable\033[0m"
		if self.caption is not None:
			s += f" '{self.caption}'"
		s += "\n"

		# Update the line state for the current depth
		if depth > 0:
			if depth >= len(line_state):
				line_state.append(not last)
			else:
				line_state[depth] = not last

		# Compute string representation of rows
		for i, row in enumerate(self.rows):
			s += row._tree_str_(depth=depth+1, last=i==len(self.rows)-1, line_state=line_state[:])  # Pass-by-value

		return s
