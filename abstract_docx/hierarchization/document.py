from __future__ import annotations
from typing import Optional
from enum import Enum

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import StylesView, Style, StyleProperties
from abstract_docx.views.format.numberings import NumberingsView
from abstract_docx.views.document import Block, Paragraph

from abstract_docx.normalization import EffectiveStructureFromOoxml

from abstract_docx.hierarchization.format.styles import HierarchicalStylesFromOoxml
from abstract_docx.hierarchization.format.numberings import HierarchicalNumberingsFromOoxml


class HierarchizationConflictResolution(Enum):
	BOUNDED = "bounded"
	UNBOUNDED = "unbounded"

DEFAULT_HIERARCHIZATION_CONFLICT_RESOLUTION: HierarchizationConflictResolution = HierarchizationConflictResolution.UNBOUNDED


class HierarchicalDocumentFromOoxml(ArbitraryBaseModel):
	root: Block
	computed_numbering_level_indexes: dict[int, dict[int, Optional[int]]]

	effective_structure_from_ooxml: EffectiveStructureFromOoxml

	styles_view: StylesView 
	numberings_view: NumberingsView

	hierarchization_conflict_resolution: HierarchizationConflictResolution

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
		hierarchical_numberings_from_ooxml: HierarchicalNumberingsFromOoxml,
		hierarchization_conflict_resolution: HierarchizationConflictResolution=DEFAULT_HIERARCHIZATION_CONFLICT_RESOLUTION
	) -> HierarchicalDocumentFromOoxml:
		styles_view, numberings_view = cls._precompute_format_view(
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			hierarchical_styles_from_ooxml=hierarchical_styles_from_ooxml,
			hierarchical_numberings_from_ooxml=hierarchical_numberings_from_ooxml
		)

		hierarchical_document_from_ooxml: HierarchicalDocumentFromOoxml = cls(
			root=Block(id=-1),
			computed_numbering_level_indexes={},
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			styles_view=styles_view,
			numberings_view=numberings_view,
			hierarchization_conflict_resolution=hierarchization_conflict_resolution
		)
		hierarchical_document_from_ooxml.compute()

		return hierarchical_document_from_ooxml
	
	def _traverse(self, curr_block: Block, prev_block: Block) -> None:
		end_of_recursion: bool = True

		# TODO: implicit_index_matches

		total_priority_difference: int = -1
		if prev_block.id != -1:
			indexes_present: bool = (
				not prev_block.id == -1
				and curr_block.format.index is not None 
				and prev_block.format.index is not None 
			)
			shared_numbering: bool = (
				indexes_present and curr_block.format.index.numbering == prev_block.format.index.numbering
			)

			styles_priority_difference: int = self.styles_view.priority_difference(
				curr_style=curr_block.format.style, prev_style=prev_block.format.style
			)
			if indexes_present and styles_priority_difference == 0:
				styles_priority_difference = self.styles_view.priority_difference(
					curr_style=curr_block.format.index.level.style, prev_style=prev_block.format.index.level.style
				)
			
			numberings_priority_difference: int = self.numberings_view.priority_difference(
				curr_index=curr_block.format.index, prev_index=prev_block.format.index
			)

			if shared_numbering:
				if (
					self.hierarchization_conflict_resolution == HierarchizationConflictResolution.BOUNDED
					and styles_priority_difference != 0 and numberings_priority_difference != 0
					and styles_priority_difference == -numberings_priority_difference
				):
					raise ValueError("") # TODO
				total_priority_difference = numberings_priority_difference
			else:
				total_priority_difference = styles_priority_difference
		
		match total_priority_difference:
			case 0:
				# Shared parent
				prev_block.parent.children.append(curr_block)
				curr_block.parent = prev_block.parent
			case 1:
				# Traverse with parent
				self._traverse(curr_block=curr_block, prev_block=prev_block.parent)
				end_of_recursion = False
			case -1:
				# Child
				if prev_block.children is None:
					prev_block.children = [curr_block]
				else:
					prev_block.children.append(curr_block)
				curr_block.parent = prev_block
		
		# Assign level index
		if curr_block.format.index is not None and end_of_recursion:
			# ! TODO: Maybe its stupid to have to check the level key all the time like this
			indentation_level: Optional[int] = next((ordered_level_id for ordered_level_id, level in curr_block.format.index.enumeration.levels.items() if level.id == curr_block.format.index.level.id), None)
			if indentation_level is None:
				raise ValueError("") # TODO
			
			if self.computed_numbering_level_indexes[curr_block.format.index.numbering.id][indentation_level] is None:
				self.computed_numbering_level_indexes[curr_block.format.index.numbering.id][indentation_level] = (
					self.numberings_view
					.enumerations[curr_block.format.index.enumeration.id].levels[indentation_level].properties.start
				)
			else:
				if (
					prev_block.id != -1 and prev_block.format.index is not None 
					and prev_block.format.index.numbering != curr_block.format.index.numbering 
					and curr_block.format.index.level.properties.override_start != -1
				):  
				# Start override (change of numbering)
					self.computed_numbering_level_indexes[curr_block.format.index.numbering.id][indentation_level] = (
						self.numberings_view
						.enumerations[curr_block.format.index.enumeration.id].levels[indentation_level].properties.start
					)
				else:
					self.computed_numbering_level_indexes[curr_block.format.index.numbering.id][indentation_level] += 1

			# Restart logic
			for level_id in range(
				indentation_level + 1, len(self.computed_numbering_level_indexes[curr_block.format.index.numbering.id].keys())
			):
				match (
					self.numberings_view
					.enumerations[curr_block.format.index.enumeration.id].levels[level_id].properties.restart
				):
					case -1:
						self.computed_numbering_level_indexes[curr_block.format.index.numbering.id][level_id] = (
							self.numberings_view
							.enumerations[curr_block.format.index.enumeration.id].levels[level_id].properties.start - 1
						)
					case 0:
						pass
					case _:
						# TODO implement this if better into the match case, also what happens if for some reason the restart happens when a new instance of a lower level happens
						if (
							self.numberings_view
							.enumerations[curr_block.format.index.enumeration.id].levels[level_id].properties.restart 
							== curr_block.format.index.level.id + 1
						):
							self.computed_numbering_level_indexes[curr_block.format.index.numbering.id][level_id] = (
								self.numberings_view
								.enumerations[curr_block.format.index.enumeration.id].levels[level_id].properties.start - 1
							)

			displayed_level_indexes = {
				k: v for k, v in self.computed_numbering_level_indexes[curr_block.format.index.numbering.id].items()
				if v is not None and k <= indentation_level
			}
			curr_block.level_indexes = displayed_level_indexes

	def compute(self) -> None:
		for numbering in self.numberings_view.numberings.values():
			if len(numbering.enumerations) > 0:
				max_indentation_level: int = max([len(enumeration.levels.keys()) for enumeration in numbering.enumerations.values()])
				self.computed_numbering_level_indexes[numbering.id] = {i: None for i in range(max_indentation_level)}

		prev_block: Block = self.root
		for block in self.effective_structure_from_ooxml.document.effective_document.values():
			if isinstance(block, Paragraph): # TODO: why specify for paras only?
				self._traverse(curr_block=block, prev_block=prev_block)
		
			prev_block: Block = block


