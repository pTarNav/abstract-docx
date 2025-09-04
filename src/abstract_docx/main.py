from __future__ import annotations
from typing import Optional
import json

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx

from abstract_docx.normalization import EffectiveStructureFromOoxml
from abstract_docx.hierarchization import HierarchicalStructureFromOoxml

from abstract_docx.data_models import Views
from abstract_docx.data_models.document import Block, Paragraph, Table

from rich.tree import Tree
from rich.table import Table as RichTable
from rich.text import Text as RichText
from rich.console import Group as RichGroup
import colorsys
from utils.printing import rich_tree_to_str

import dill as pickle
from utils.pickle import register_picklers
register_picklers()

import logging
from colorlog import ColoredFormatter
logger = logging.getLogger(__name__)


class AbstractDocx(ArbitraryBaseModel):
	"""

	"""
	file_path: str
	ooxml_docx: OoxmlDocx

	_effective_structure: Optional[EffectiveStructureFromOoxml] = None
	_hierarchical_structure: Optional[HierarchicalStructureFromOoxml] = None
	_views: Optional[Views] = None

	@staticmethod
	def _setup_logger(logging_level: str) -> None:
		logging.basicConfig(level = logging._nameToLevel.get(logging_level.upper()))
		formatter = ColoredFormatter(
			"%(log_color)s[%(asctime)s - %(name)s] %(levelname)s: %(message)s",
			datefmt="%Y-%m-%d %H:%M:%S",
		)
		# Swap out the handler’s formatter for the colored one
		for handler in logging.root.handlers:
			handler.setFormatter(formatter)

	@classmethod
	def read(cls, file_path: str, logging_level: str = "DEBUG") -> AbstractDocx:
		cls._setup_logger(logging_level=logging_level)

		ooxml_docx: OoxmlDocx = OoxmlDocx.read(file_path=file_path)

		return cls(file_path=file_path, ooxml_docx=ooxml_docx)
	
	# @property
	# def effective_structure(self) -> EffectiveStructureFromOoxml:
	# 	if self._effective_structure is not None:
	# 		return self._effective_structure

	# 	raise ValueError("Please call")
	
	# @property
	# def hierarchical_structure(self) -> HierarchicalStructureFromOoxml:
	# 	if self._hierarchical_structure is not None:
	# 		return self._hierarchical_structure

	# 	raise ValueError("Please call")
	
	@property
	def views(self) -> Views:
		if self._views is not None:
			return self._views

		raise ValueError("Please call")

	def __call__(self, *args, **kwds) -> None:
		"""
		TODO: Parameterization
		"""

		self._effective_structure: EffectiveStructureFromOoxml = EffectiveStructureFromOoxml.normalization(
			ooxml_docx=self.ooxml_docx
		)
		self._hierarchical_structure: HierarchicalStructureFromOoxml = HierarchicalStructureFromOoxml.hierarchization(
			effective_structure_from_ooxml=self._effective_structure
		)
		
		self._views: Views = Views.load(
			effective_structure=self._effective_structure, hierarchical_structure=self._hierarchical_structure
		)		

	def _print_document(self, curr_block: Block, prev_tree_node: Tree, depth: int = 0, include_metadata: bool = False) -> None:
		
		def node_style(d: int) -> str:
			# evenly space hues around the color wheel
			hue = (d*30 + 180)%360/360.0
			# low-medium saturation, high lightness → pastel
			r, g, b = colorsys.hls_to_rgb(hue, 0.5, 0.5)
			return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
		
		if curr_block.format is not None and curr_block.format.is_numbered:
			curr_block_numbering_str: str = repr(curr_block.format.index_str)
		else:
			curr_block_numbering_str: str = ""

		if isinstance(curr_block, Paragraph):
			rich_text: RichText = (
				RichText(f"[{curr_block.id}] ", style=node_style(d=depth)) 
				+ RichText(f"{curr_block_numbering_str} ", style="gray70")
				+ RichText(str(curr_block), style="white")
			)
			curr_tree_node = prev_tree_node.add(rich_text)

			if include_metadata:
				curr_tree_node.add(f"Style ID: {curr_block.format.style.id if curr_block.format is not None else '-'}")
				# curr_tree_node.add(f"Numbering ID: {curr_block.format.index.numbering.id if curr_block.format is not None and curr_block.format.index is not None else '-'}")
				# curr_tree_node.add(f"Enumeration ID: {curr_block.format.index.enumeration.id if curr_block.format is not None and curr_block.format.index is not None else '-'}")
				# curr_tree_node.add(f"Level ID: {curr_block.format.index.level.id if curr_block.format is not None and curr_block.format.index is not None else '-'}")
				# curr_tree_node.add(f"Level indexes: {curr_block.format.index.index_ctr if curr_block.format is not None and curr_block.format.index is not None else '-'}")
		elif isinstance(curr_block, Table):
			rich_table: RichTable = RichTable(show_header=False, show_lines=True)
			for _ in range(len(curr_block.rows[0].cells)):
				rich_table.add_column(no_wrap=True, max_width=64)

			for row in curr_block.rows:
				rich_table.add_row(*[RichText(str(cell_content), style="white") for cell_content in row.cells])

			rich_text_group: RichGroup = RichGroup(
				RichText(f'[{curr_block.id}] ', style=node_style(d=depth)),
				RichText(f"{curr_block_numbering_str} ", style="gray70"),
				rich_table
			)
			curr_tree_node = prev_tree_node.add(rich_text_group)

			if include_metadata:
				curr_tree_node.add(f"Style ID: {curr_block.format.style.id if curr_block.format is not None else '-'}")
				curr_tree_node.add(f"Numbering ID: {curr_block.format.index.numbering.id if curr_block.format is not None and curr_block.format.index is not None else '-'}")
				curr_tree_node.add(f"Enumeration ID: {curr_block.format.index.enumeration.id if curr_block.format is not None and curr_block.format.index is not None else '-'}")
				curr_tree_node.add(f"Level ID: {curr_block.format.index.level.id if curr_block.format is not None and curr_block.format.index is not None else '-'}")
				curr_tree_node.add(f"Level indexes: {curr_block.format.index.index_ctr if curr_block.format is not None and curr_block.format.index is not None else '-'}")
		else:
			rich_text: RichText = (
				RichText(f'[{curr_block.id}] ', style=node_style(d=depth)) 
				+ RichText(f"{curr_block_numbering_str} ", style="gray70")
			)
			curr_tree_node = prev_tree_node.add(rich_text)
		
		if curr_block.children is not None:
			for child in curr_block.children:
				self._print_document(curr_block=child, prev_tree_node=curr_tree_node, depth=depth+1, include_metadata=include_metadata)

	def print(self, file_path: Optional[str] = None, include_metadata: bool = False, collapse_tables: bool = False) -> None:
		tree_root: Tree = Tree("Document")

		self._print_document(curr_block=self.views.document.root, prev_tree_node=tree_root, include_metadata=include_metadata)
		if file_path is not None:
			with open(file_path, "w+", encoding="utf-8") as f:
				print(rich_tree_to_str(tree_root), file=f)
		else:
			print(rich_tree_to_str(tree_root))
	
	def _to_text(self, block: Block, depth: int=0) -> str:
		s = "\t"*depth
		if block.format.is_numbered:
			s += block.format.index_str
		if isinstance(block, Paragraph):
			s += str(block).strip()
		elif isinstance(block, Table):
			s += ("\n" + "\t"*depth).join([l for l in str(block).split("@NEWLINE@")])
		else:
			s += "@WORK_IN_PROGRESS@"
		s += "\n"
		
		if block.children is not None:
			for child in block.children:
				s += self._to_text(block=child, depth=depth+1)
		
		return s

	def to_txt(self, output_file_path: Optional[str]=None) -> None:
		s: str = ""
		for root in self.views.document.root.children:
			s += self._to_text(block=root)
		
		output_file_path: str = f"{self.file_path}.txt" if output_file_path is None else output_file_path
		with open(output_file_path, "w+", encoding="utf-8") as f:
			f.write(s)

	def _to_json(self, block: Block) -> dict:
		data: dict = {"id": block.id}

		if block.format.index.index_ctr is not None:
			data["numbering_str"] = block.format.index.enumeration.format(index_ctr=block.format.index.index_ctr)
		
		if isinstance(block, Paragraph) or isinstance(block, Table):
			data["text"] = str(block)
		else:
			data["text"] = "@WORK_IN_PROGRESS@"

		if block.children is not None:
			data["children"] = []
			for child in block.children:
				data["children"].append(self._to_json(block=child))
		
		return data

	def to_json(self) -> None:
		root_data: dict = {"id": -1, "text": "__ROOT__", "children": []}
		for child in self.views.document.root.children:
			root_data["children"].append(self._to_json(block=child))

		json_data = json.dumps(root_data, indent=4)

		with open(f"{self.file_path}.json", "w+", encoding="utf-8") as f:
			f.write(json_data)

	def to_pickle(self) -> bytes:
		return pickle.dumps(self)
	
	@classmethod
	def from_pickle(cls, b: bytes) -> AbstractDocx:
		return pickle.loads(b)
