from __future__ import annotations
from typing import Optional

from rich.tree import Tree
from utils.rich_tree import rich_tree_to_str

from ooxml_docx.ooxml import OoxmlElement, OoxmlPart
from ooxml_docx.relationships import OoxmlRelationships
from ooxml_docx.structure.styles import OoxmlStyles
from ooxml_docx.structure.numberings import OoxmlNumberings
from ooxml_docx.document.paragraph import Paragraph
from ooxml_docx.document.table import Table


class OoxmlDocument(OoxmlElement):
	body: list[Paragraph | Table] = []

	@classmethod
	def build(
			cls,
			ooxml_document_part: OoxmlPart,
			styles: OoxmlStyles, 
			numberings: OoxmlNumberings,
			relationships: OoxmlRelationships
		) -> OoxmlDocument:
		"""_summary_

		:param ooxml_document_part: _description_
		:return: _description_
		"""

		return cls(
			element=ooxml_document_part.ooxml.element,
			body=cls._parse_body(
				ooxml_document_part=ooxml_document_part, styles=styles, numberings=numberings, relationships=relationships
			)
		)
	
	@staticmethod
	def _parse_body(
			ooxml_document_part: OoxmlPart,
			styles: OoxmlStyles,
			numberings: OoxmlNumberings,
			relationships: OoxmlRelationships
		) -> list[Paragraph | Table]:
		"""_summary_

		:param ooxml_document_part: _description_
		:return: _description_
		"""
		ooxml_body: Optional[OoxmlElement] = ooxml_document_part.ooxml.xpath_query(query="./w:body", singleton=True)
		if ooxml_body is None:
			# The body OOXML element should still be found inside the document no matter the actual content written
			raise ValueError("No <w:body> OOXML element found inside the document.")

		ooxml_content: Optional[list[OoxmlElement]] = ooxml_body.xpath_query(
			query="./*[not(self::w:bookmarkStart or self::w:bookmarkEnd)]"
		)
		if ooxml_content is None:
			# From the perspective of the use-case it does not make much sense to be able to have an empty document,
			# however, it is still good to be able to pass an empty document through the pipeline,
			# because it allows the user to parse the other kinds of docx data through this tool
			# "E.g. User wants to check and normalize the style hierarchy"
			# Raises a warning instead of an error and proceed
			print("\033[33mWarning: No textual content detected inside the document...\033[0m")
			return []

		content: list[Paragraph | Table] = []
		for ooxml_element in ooxml_content:
			match ooxml_element.local_name:
				case "p":
					element: Paragraph = Paragraph.parse(
						ooxml_paragraph=ooxml_element, styles=styles, numberings=numberings, relationships=relationships
					)
				case "tbl":
					element: Table = Table.parse(ooxml_table=ooxml_element, styles=styles, relationships=relationships)
				case _:
					# ! TODO: remove continue
					continue
					raise ValueError(f"Unexpected OOXML element: <w:{ooxml_element.local_name}>")
			content.append(element)
			
		return content

	def __str__(self) -> str:
		return rich_tree_to_str(self._tree_str_())

	def _tree_str_(self) -> Tree:
		tree = Tree("[bold cyan]:input_letters: Body[/bold cyan]")
		for i, content in enumerate(self.body):
			tree.add(content._tree_str_())
		
		return tree