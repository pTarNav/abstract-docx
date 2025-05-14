from abstract_docx.normalization.document import EffectiveDocumentFromOoxml
from abstract_docx.views.format import FormatsView
from abstract_docx.views.document import Paragraph, Block
from abstract_docx.views.format.styles import Style

from typing import Optional


def traverse(curr_block: Block, prev_block: Block, _computed_priority_levels: dict[int, int], _computed_numbering_level_indexes: dict[int, dict[int, int]], formats_view: FormatsView):
	curr_priority_level: int = _computed_priority_levels[curr_block.id]
	prev_priority_level: int = _computed_priority_levels[prev_block.id]
	
	shared_numbering: bool = (
		not prev_block.id == -1
		and curr_block.format.numbering is not None 
		and prev_block.format.numbering is not None 
		and curr_block.format.numbering == prev_block.format.numbering
	)

	if shared_numbering:
		curr_numbering_level: int = curr_block.format.level.id
		prev_numbering_level: int = prev_block.format.level.id
	
	end_of_recursion: bool = True

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
			traverse(curr_block=curr_block, prev_block=prev_block.parent, _computed_priority_levels=_computed_priority_levels, _computed_numbering_level_indexes=_computed_numbering_level_indexes, formats_view=formats_view)
			end_of_recursion = False
	
	# Assign level index
	if curr_block.format.numbering is not None and end_of_recursion:
		_computed_numbering_level_indexes[curr_block.format.numbering.id][curr_block.format.level.id] += 1

		# Restart logic
		for level_id in range(curr_block.format.level.id + 1, len(_computed_numbering_level_indexes[curr_block.format.numbering.id].keys())):
			match formats_view.numberings[curr_block.format.numbering.id].levels[level_id].properties.restart:
				case -1:
					_computed_numbering_level_indexes[curr_block.format.numbering.id][level_id] = formats_view.numberings[curr_block.format.numbering.id].levels[level_id].properties.start - 1
				case 0:
					pass
				case _:
					# TODO implement this if better into the match case, also what happens if for some reason the restart happens when a new instance of a lower level happens
					if formats_view.numberings[curr_block.format.numbering.id].levels[level_id].properties.restart == curr_block.format.level.id + 1:
						_computed_numbering_level_indexes[curr_block.format.numbering.id][level_id] = formats_view.numberings[curr_block.format.numbering.id].levels[level_id].properties.start - 1

		# print()
		# print(_computed_numbering_level_indexes[curr_block.format.numbering.id])
		displayed_level_indexes = {k: v for k, v in _computed_numbering_level_indexes[curr_block.format.numbering.id].items() if v is not None and k <= curr_block.format.level.id}
		# print("displayed numbering\t", curr_block.format.numbering.format(displayed_level_indexes), f"[{curr_block.id}][{curr_block.format.numbering.id}][{curr_block.format.level.id}]")
		curr_block.level_indexes = displayed_level_indexes


def document_hierarchization(effective_document: EffectiveDocumentFromOoxml, formats_view: FormatsView) -> Block:
	
	styles_view_priorities: dict[int, list[Style]] = formats_view.styles.priorities.items()

	document_root: Block = Block(id=-1)

	_computed_priority_levels: dict[int, int] = {-1: -1}

	_computed_numbering_level_indexes: dict[int, dict[int, Optional[int]]] = {
		numbering.id: {level.id: level.properties.start-1 for level in numbering.levels.values()} for numbering in formats_view.numberings.values()
	}

	prev_block: Block = document_root
	for block in effective_document.values():
		if isinstance(block, Paragraph):
			# TODO: maybe priority level should be part of the style attributes (instead of parent child relationship)
			for priority_level, styles_in_priority_level in styles_view_priorities:
				if block.format.style in styles_in_priority_level:
					_computed_priority_levels[block.id] = priority_level
					break
			traverse(curr_block=block, prev_block=prev_block, _computed_priority_levels=_computed_priority_levels, _computed_numbering_level_indexes=_computed_numbering_level_indexes, formats_view=formats_view)
		
		prev_block: Block = block

	return document_root

