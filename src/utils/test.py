import json

from abstract_docx.main import AbstractDocx
from abstract_docx.data_models.document import Block


def _test_output_tree_structure_and_numbering_at_block_level(block: Block, test_block: dict):
	# Check id matches
	assert block.id == test_block["id"], f"Block ID mismatch at block {block.id}: ({block.id=}, {test_block['id']=})"
	
	# Check numbering matches
	block_numbering_str: str | None = (	
		block.format.index.enumeration.format(level_indexes=block.level_indexes)
		if block.format is not None and block.format.index is not None
		else None
	)
	test_block_numbering_str: str | None = test_block.get("numbering_str", None)
	assert block_numbering_str == test_block_numbering_str, f"Numbering string mismatch at block {block.id}: ({block_numbering_str=}, {test_block_numbering_str=})"

	# Check either both or neither have children
	test_block_children: list[dict] | None = test_block.get("children", None)
	assert (block.children is None) == (test_block_children is None), f"Children existence mismatch at block {block.id}: ({block.children is None=}, {test_block_children is None=})"


	if block.children is not None and test_block_children is not None:
		# Check same number of children
		assert len(block.children) == len(test_block_children), f"Children number mismatch at block {block.id}: ({len(block.children)=}, {len(test_block_children)=})"

		# Check recursively for each of the children
		for block_child, test_block_child in zip(block.children,test_block_children):
			_test_output_tree_structure_and_numbering_at_block_level(block=block_child, test_block=test_block_child)

def _test_output_tree_structure_and_numbering(file_path: str, output_json_path: str):
	adoc: AbstractDocx = AbstractDocx.read(file_path=file_path, logging_level="ERROR")
	adoc()
	
	with open(output_json_path, "r", encoding="utf-8") as f:
		test_output_json_root: dict = json.load(f)
	
	_test_output_tree_structure_and_numbering_at_block_level(block=adoc.views.document.root, test_block=test_output_json_root)