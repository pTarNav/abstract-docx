from abstract_docx.normalization.document import EffectiveDocumentFromOoxml
from abstract_docx.views.format import StylesView
from abstract_docx.views.document import Paragraph, Block
from abstract_docx.views.format.styles import Style

from rich.tree import Tree
from utils.printing import rich_tree_to_str

PALETTE = ["bright_black", "cyan", "green", "yellow", "red", "magenta"]

def print_computed_tree(prev_tree_node: Tree, curr_block: Block, depth: int = 0):
	
	print(depth)
	if isinstance(curr_block, Paragraph):
		curr_tree_node: Tree = prev_tree_node.add(f"{curr_block.id} {curr_block}", style=PALETTE[depth % len(PALETTE)])
	else:
		curr_tree_node = prev_tree_node

	if curr_block.children is not None:
		for child in curr_block.children:
			print_computed_tree(prev_tree_node=curr_tree_node, curr_block=child, depth=depth+1)


def traverse(curr_block: Block, prev_block: Block, _computed_priority_levels: dict[int, int]):
	curr_priority_level: int = _computed_priority_levels[curr_block.id]
	prev_priority_level: int = _computed_priority_levels[prev_block.id]
	
	shared_numbering: bool = (
		not (prev_block.id == -1 or curr_block.id == -1)
		and curr_block.format.numbering is not None 
		and prev_block.format.numbering is not None 
		and curr_block.format.numbering == prev_block.format.numbering
	)

	if shared_numbering:
		curr_numbering_level: int = curr_block.format.level.id
		prev_numbering_level: int = prev_block.format.level.id

	if curr_priority_level == prev_priority_level:
		if shared_numbering and curr_numbering_level != prev_numbering_level:
			if curr_numbering_level > prev_numbering_level:
				if prev_block.children is None:
					prev_block.children = [curr_block]
				else:
					prev_block.children.append(curr_block)
				curr_block.parent = prev_block
			elif curr_numbering_level < prev_numbering_level:
				prev_block.parent.children.append(curr_block)
				curr_block.parent = prev_block.parent
		else:
			prev_block.parent.children.append(curr_block)
			curr_block.parent = prev_block.parent
	else:
		if curr_priority_level > prev_priority_level:
			if prev_block.children is None:
				prev_block.children = [curr_block]
			else:
				prev_block.children.append(curr_block)
			curr_block.parent = prev_block
		elif curr_priority_level < prev_priority_level:
			traverse(curr_block=curr_block, prev_block=prev_block.parent, _computed_priority_levels=_computed_priority_levels)

def document_hierarchization(effective_document: EffectiveDocumentFromOoxml, styles_view: StylesView):
	
	styles_view_priorities: dict[int, list[Style]] = styles_view.priorities.items()

	document_root: Block = Block(id=-1)

	_computed_priority_levels: dict[int, int] = {-1: -1}

	prev_block = document_root
	for block in effective_document.values():
		if isinstance(block, Paragraph):
			# TODO: maybe priority level should be part of the style attributes (instead of parent child relationship)
			for priority_level, styles_in_priority_level in styles_view_priorities:
				if block.format.style in styles_in_priority_level:
					_computed_priority_levels[block.id] = priority_level
					break
			traverse(curr_block=block, prev_block=prev_block, _computed_priority_levels=_computed_priority_levels)
		
		prev_block: Block = block

	tree_root: Tree = Tree("Document")
	print_computed_tree(prev_tree_node=tree_root, curr_block=document_root)
	print(rich_tree_to_str(tree=tree_root))
