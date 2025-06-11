from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import StylesView
from abstract_docx.views.format.numberings import NumberingsView
from abstract_docx.views.document import Block

from abstract_docx.normalization import EffectiveStructureFromOoxml

from abstract_docx.hierarchization.format.styles import HierarchicalStylesFromOoxml
from abstract_docx.hierarchization.format.numberings import HierarchicalNumberingsFromOoxml


class HierarchicalDocumentFromOoxml(ArbitraryBaseModel):
	root: Block

	effective_structure_from_ooxml: EffectiveStructureFromOoxml

	styles_view: StylesView 
	numberings_view: NumberingsView

	@staticmethod
	def _precompute_format_view(
		effective_structure_from_ooxml: EffectiveStructureFromOoxml,
		hierarchical_styles_from_ooxml: HierarchicalStylesFromOoxml,
		hierarchical_numberings_from_ooxml: HierarchicalNumberingsFromOoxml
	) -> tuple[StylesView, NumberingsView]:
		return (
			StylesView.load(
				styles=effective_structure_from_ooxml.styles.effective_styles,
				priority_ordered_styles=hierarchical_styles_from_ooxml.priority_ordered_styles
			),
			NumberingsView.load(
				numberings=effective_structure_from_ooxml.numberings.effective_numberings,
				enumerations=effective_structure_from_ooxml.numberings.effective_enumerations,
				levels=effective_structure_from_ooxml.numberings.effective_levels,
				priority_ordered_levels=hierarchical_numberings_from_ooxml.priority_ordered_levels
			)
		)

	@classmethod
	def hierarchization(
		cls,
		effective_structure_from_ooxml: EffectiveStructureFromOoxml,
		hierarchical_styles_from_ooxml: HierarchicalStylesFromOoxml,
		hierarchical_numberings_from_ooxml: HierarchicalNumberingsFromOoxml
	) -> HierarchicalDocumentFromOoxml:
		styles_view, numberings_view = cls._precompute_format_view(
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			hierarchical_styles_from_ooxml=hierarchical_styles_from_ooxml,
			hierarchical_numberings_from_ooxml=hierarchical_numberings_from_ooxml
		)

		hierarchical_document_from_ooxml: HierarchicalDocumentFromOoxml = cls(
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			styles_view=styles_view,
			numberings_view=numberings_view
		)
		hierarchical_document_from_ooxml.compute()
	
	def traverse(self, curr_block: Block, prev_block: Block) -> None:
		end_of_recursion: bool = True

		curr_style_priority: int = self.styles_view.find_priority(style=curr_block.format.style)
		prev_style_priority: int = self.styles_view.find_priority(style=prev_block.format.style)
	
		shared_numbering: bool = (
			not prev_block.id == -1
			and curr_block.format.index is not None 
			and prev_block.format.index is not None 
			and curr_block.format.index.numbering == prev_block.format.index.numbering
		)

		# (I know this could be optimized into an if tree with only 3 outcomes, but this is more readable... :D)
		if shared_numbering:
			# TODO: Actually provide the numbering priority level /current is very suboptimal
			curr_level_priority: int = next(ordered_level_id for ordered_level_id, level in curr_block.format.index.enumeration.levels.items() if level.id == curr_block.format.index.level.id)
			prev_level_priority: int = next(ordered_level_id for ordered_level_id, level in prev_block.format.index.enumeration.levels.items() if level.id == prev_block.format.index.level.id)

			if prev_level_priority == curr_level_priority:
				# shared parent
				prev_block.parent.children.append(curr_block)
				curr_block.parent = prev_block.parent
			else:
				if prev_level_priority > curr_level_priority and prev_style_priority >= curr_style_priority:
					# traverse
					traverse(curr_block=curr_block, prev_block=prev_block.parent)
					end_of_recursion = False
				elif prev_level_priority < curr_level_priority and prev_style_priority <= curr_style_priority:
					# child
					if prev_block.children is None:
						prev_block.children = [curr_block]
					else:
						prev_block.children.append(curr_block)
					curr_block.parent = prev_block
				else:
					match hierarchization_conflict_resolution:
						case HierarchizationConflictResolutionParameter.BOUNDED:
							raise ValueError("") # TODO
						case HierarchizationConflictResolutionParameter.UNBOUNDED:
							if (
								prev_numbering_priority_level < curr_numbering_priority_level
								and prev_style_priority_level > curr_style_priority_level
							):
								# child
								if prev_block.children is None:
									prev_block.children = [curr_block]
								else:
									prev_block.children.append(curr_block)
								curr_block.parent = prev_block
							elif (
								prev_numbering_priority_level < curr_numbering_priority_level
								and prev_style_priority_level > curr_style_priority_level	
							):
								# traverse
								traverse(curr_block=curr_block, prev_block=prev_block.parent, _computed_style_priority_levels=_computed_style_priority_levels, _computed_numbering_level_indexes=_computed_numbering_level_indexes, formats_view=formats_view)
								end_of_recursion = False
		else:
			match self.styles_view.priority_difference(curr_style=curr_block.format.style, prev_style=prev_block.format.style):
				case 0:
					# Shared parent
					prev_block.parent.children.append(curr_block)
					curr_block.parent = prev_block.parent
				case diff_style_priority if diff_style_priority > 0:
					# Child
					if prev_block.children is None:
						prev_block.children = [curr_block]
					else:
						prev_block.children.append(curr_block)
					curr_block.parent = prev_block
				case diff_style_priority if diff_style_priority < 0:
					# Traverse
					traverse(curr_block=curr_block, prev_block=prev_block.parent)
					end_of_recursion = False
		
		# Assign level index
		if curr_block.format.index is not None and end_of_recursion:
			pass

	def compute(self) -> None:
		root: Block = Block(id=-1)

		prev_block: Block = root
		for block in self.effective_structure_from_ooxml.document.effective_document.values():
			if isinstance(block, Paragraph): # TODO: why specify for paras only?
				traverse(curr_block=block, prev_block=prev_block)
		
			prev_block: Block = block


from enum import Enum
from abstract_docx.normalization.document import EffectiveDocumentFromOoxml
from abstract_docx.views.format import FormatView
from abstract_docx.views.document import Paragraph, Block
from abstract_docx.views.format.styles import Style

class HierarchizationConflictResolutionParameter(Enum):
	BOUNDED = "bounded"
	UNBOUNDED = "unbounded"

hierarchization_conflict_resolution = HierarchizationConflictResolutionParameter.UNBOUNDED

def traverse(curr_block: Block, prev_block: Block, _computed_style_priority_levels: dict[int, int], _computed_numbering_level_indexes: dict[int, dict[int, int]], formats_view: FormatView):
	end_of_recursion: bool = True

	# A higher priority level actually indicates lower hierarchy
	curr_style_priority_level: int = _computed_style_priority_levels[curr_block.id]
	prev_style_priority_level: int = _computed_style_priority_levels[prev_block.id]

	shared_numbering: bool = (
		not prev_block.id == -1
		and curr_block.format.index is not None 
		and prev_block.format.index is not None 
		and curr_block.format.index.numbering == prev_block.format.index.numbering
	)
	
	# (I know this could be optimized into an if tree with only 3 outcomes, but this is more readable... :D)
	if shared_numbering:
		# TODO: Actually provide the numbering priority level /current is very suboptimal
		curr_numbering_priority_level: int = next(ordered_level_id for ordered_level_id, level in curr_block.format.index.enumeration.levels.items() if level.id == curr_block.format.index.level.id)
		prev_numbering_priority_level: int = next(ordered_level_id for ordered_level_id, level in prev_block.format.index.enumeration.levels.items() if level.id == prev_block.format.index.level.id)

		if prev_numbering_priority_level == curr_numbering_priority_level:
			# shared parent
			prev_block.parent.children.append(curr_block)
			curr_block.parent = prev_block.parent
		else:
			if (
				prev_numbering_priority_level > curr_numbering_priority_level
				and prev_style_priority_level >= curr_style_priority_level
			):
				# traverse
				traverse(curr_block=curr_block, prev_block=prev_block.parent, _computed_style_priority_levels=_computed_style_priority_levels, _computed_numbering_level_indexes=_computed_numbering_level_indexes, formats_view=formats_view)
				end_of_recursion = False
			elif (
				prev_numbering_priority_level < curr_numbering_priority_level
				and prev_style_priority_level <= curr_style_priority_level
			):
				# child
				if prev_block.children is None:
					prev_block.children = [curr_block]
				else:
					prev_block.children.append(curr_block)
				curr_block.parent = prev_block
			else:
				match hierarchization_conflict_resolution:
					case HierarchizationConflictResolutionParameter.BOUNDED:
						raise ValueError("") # TODO
					case HierarchizationConflictResolutionParameter.UNBOUNDED:
						if (
							prev_numbering_priority_level < curr_numbering_priority_level
							and prev_style_priority_level > curr_style_priority_level
						):
							# child
							if prev_block.children is None:
								prev_block.children = [curr_block]
							else:
								prev_block.children.append(curr_block)
							curr_block.parent = prev_block
						elif (
							prev_numbering_priority_level < curr_numbering_priority_level
							and prev_style_priority_level > curr_style_priority_level	
						):
							# traverse
							traverse(curr_block=curr_block, prev_block=prev_block.parent, _computed_style_priority_levels=_computed_style_priority_levels, _computed_numbering_level_indexes=_computed_numbering_level_indexes, formats_view=formats_view)
							end_of_recursion = False
	else:
		if prev_style_priority_level == curr_style_priority_level:
			# shared parent
			prev_block.parent.children.append(curr_block)
			curr_block.parent = prev_block.parent
		else:
			if prev_style_priority_level > curr_style_priority_level:
				# traverse
				traverse(curr_block=curr_block, prev_block=prev_block.parent, _computed_style_priority_levels=_computed_style_priority_levels, _computed_numbering_level_indexes=_computed_numbering_level_indexes, formats_view=formats_view)
				end_of_recursion = False
			elif prev_style_priority_level < curr_style_priority_level:
				# child
				if prev_block.children is None:
					prev_block.children = [curr_block]
				else:
					prev_block.children.append(curr_block)
				curr_block.parent = prev_block
	
	# Assign level index
	if curr_block.format.index is not None and end_of_recursion:
		indentation_level: Optional[int] = next((ordered_level_id for ordered_level_id, level in curr_block.format.index.enumeration.levels.items() if level.id == curr_block.format.index.level.id), None)
		if indentation_level is None:
			raise ValueError("") # TODO
		
		if _computed_numbering_level_indexes[curr_block.format.index.numbering.id][indentation_level] is None:
			_computed_numbering_level_indexes[curr_block.format.index.numbering.id][indentation_level] = formats_view.numberings.enumerations[curr_block.format.index.enumeration.id].levels[indentation_level].properties.start
		else:
			if prev_block.id != -1 and prev_block.format.index is not None and prev_block.format.index.numbering != curr_block.format.index.numbering and curr_block.format.index.level.properties.override_start != -1:  # Start override (change of numbering)
				_computed_numbering_level_indexes[curr_block.format.index.numbering.id][indentation_level] = formats_view.numberings.enumerations[curr_block.format.index.enumeration.id].levels[indentation_level].properties.start
			else:
				_computed_numbering_level_indexes[curr_block.format.index.numbering.id][indentation_level] += 1

		# Restart logic
		for level_id in range(indentation_level + 1, len(_computed_numbering_level_indexes[curr_block.format.index.numbering.id].keys())):
			match formats_view.numberings.enumerations[curr_block.format.index.enumeration.id].levels[level_id].properties.restart:
				case -1:
					_computed_numbering_level_indexes[curr_block.format.index.numbering.id][level_id] = formats_view.numberings.enumerations[curr_block.format.index.enumeration.id].levels[level_id].properties.start - 1
				case 0:
					pass
				case _:
					# TODO implement this if better into the match case, also what happens if for some reason the restart happens when a new instance of a lower level happens
					if formats_view.numberings.enumerations[curr_block.format.index.enumeration.id].levels[level_id].properties.restart == curr_block.format.index.level.id + 1:
						_computed_numbering_level_indexes[curr_block.format.index.numbering.id][level_id] = formats_view.numberings.enumerations[curr_block.format.index.enumeration.id].levels[level_id].properties.start - 1

		displayed_level_indexes = {k: v for k, v in _computed_numbering_level_indexes[curr_block.format.index.numbering.id].items() if v is not None and k <= indentation_level}
		curr_block.level_indexes = displayed_level_indexes

def document_hierarchization(effective_document: EffectiveDocumentFromOoxml, formats_view: FormatView) -> Block:
	
	styles_view_priorities: dict[int, list[Style]] = formats_view.styles.priorities.items()

	document_root: Block = Block(id=-1)

	_computed_priority_levels: dict[int, int] = {-1: -1}

	_computed_numbering_level_indexes: dict[int, dict[int, Optional[int]]] = {}
	for numbering in formats_view.numberings.numberings.values():
		if len(numbering.enumerations) > 0:
			max_indentation_level: int = max([len(enumeration.levels.keys()) for enumeration in numbering.enumerations.values()])
			_computed_numbering_level_indexes[numbering.id] = {i: None for i in range(max_indentation_level)}


	prev_block: Block = document_root
	for block in effective_document.effective_document.values():
		if isinstance(block, Paragraph):
			# TODO: maybe priority level should be part of the style attributes (instead of parent child relationship)
			for priority_level, styles_in_priority_level in styles_view_priorities:
				if block.format.style in styles_in_priority_level:
					_computed_priority_levels[block.id] = priority_level
					break
			traverse(curr_block=block, prev_block=prev_block, _computed_style_priority_levels=_computed_priority_levels, _computed_numbering_level_indexes=_computed_numbering_level_indexes, formats_view=formats_view)
		
		prev_block: Block = block

	return document_root

