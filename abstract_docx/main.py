from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx

from abstract_docx.normalization import EffectiveStructureFromOoxml
from abstract_docx.views import AbstractDocxViews
from abstract_docx.views.document import Block, Paragraph
from abstract_docx.views.format import StylesView, FormatsView

from abstract_docx.hierarchization.format.styles import styles_hierarchization
from abstract_docx.hierarchization.document import document_hierarchization


from rich.tree import Tree
from rich.text import Text as RichText
import colorsys
from utils.printing import rich_tree_to_str

class AbstractDocx(ArbitraryBaseModel):
	"""

	"""
	file_path: str
	ooxml_docx: OoxmlDocx

	_effective_structure: Optional[EffectiveStructureFromOoxml] = None
	_views: Optional[AbstractDocxViews] = None

	_document_root: Optional[Block] = None

	@classmethod
	def read(cls, file_path: str) -> AbstractDocx:
		ooxml_docx: OoxmlDocx = OoxmlDocx.read(file_path=file_path)

		return cls(file_path=file_path, ooxml_docx=ooxml_docx)
	
	def normalization(self) -> None:
		self._effective_structure = EffectiveStructureFromOoxml.normalization(ooxml_docx=self.ooxml_docx)

	@property
	def effective_structure(self) -> EffectiveStructureFromOoxml:
		if self._effective_structure is not None:
			return self._effective_structure

		raise ValueError("Please call")
	
	@property
	def views(self) -> EffectiveStructureFromOoxml:
		if self._views is not None:
			return self._views

		raise ValueError("Please call")

	@property
	def document_root(self) -> Block:
		if self._document_root is not None:
			return self._document_root

		raise ValueError("Please call")

	def hierarchization(self) -> Block:
		styles_view: StylesView = styles_hierarchization(effective_styles=self._effective_structure.styles.effective_styles)
		return document_hierarchization(effective_document=self._effective_structure.document.effective_document, formats_view=FormatsView(styles=styles_view, numberings=self._effective_structure.numberings.effective_numberings))

	def __call__(self, *args, **kwds) -> None:
		"""
		In the call function because they can be parametrized
		"""

		self.normalization()
		self._document_root: Block = self.hierarchization()
		
		self.print(document_root=self._document_root)

	def _print_document(self, curr_block: Block, prev_tree_node: Tree, depth: int = 0, metadata: bool = False) -> None:
		
		def node_style(d: int) -> str:
			# evenly space hues around the color wheel
			hue = (d*30 + 180)%360/360.0
			# low-medium saturation, high lightness → pastel
			r, g, b = colorsys.hls_to_rgb(hue, 0.5, 0.5)
			return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
		
		if curr_block.level_indexes is not None:
			curr_block_numbering_str: str = curr_block.format.numbering.format(level_indexes=curr_block.level_indexes)
		else:
			curr_block_numbering_str: str = ""

		if isinstance(curr_block, Paragraph):
			rich_text: RichText = (
				RichText(f'[{curr_block.id}] ', style=node_style(d=depth)) 
				+ RichText(f"{curr_block_numbering_str} ", style="gray70")
				+ RichText(str(curr_block), style="white")
			)
			curr_tree_node = prev_tree_node.add(rich_text)
		else:
			rich_text: RichText = (
				RichText(f'[{curr_block.id}] ', style=node_style(d=depth)) 
				+ RichText(f"{curr_block_numbering_str} ", style="gray70")
			)
			curr_tree_node = prev_tree_node.add(rich_text)
		
		if curr_block.children is not None:
			for child in curr_block.children:
				self._print_document(curr_block=child, prev_tree_node=curr_tree_node, depth=depth+1)

	def print(self, document_root: Block, include_metadata: bool = False) -> None:
		tree_root: Tree = Tree("Document")

		self._print_document(curr_block=document_root, prev_tree_node=tree_root)
		print(rich_tree_to_str(tree_root))
	
	
if __name__ == "__main__":
	test_files = ["sample3", "cp2022_10a01", "A6.4-PROC-ACCR-002", "SB004_report", "cop29_report_Add1"]
	x = AbstractDocx.read(file_path=f"test/{test_files[2]}.docx")
	x()	