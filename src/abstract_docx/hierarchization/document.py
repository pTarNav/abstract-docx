from __future__ import annotations
from typing import Optional
from enum import Enum

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.data_models.styles import StylesView, Style, StyleProperties
from abstract_docx.data_models.numberings import NumberingsView
from abstract_docx.data_models.document import Block, Paragraph

from abstract_docx.normalization import EffectiveStructureFromOoxml

from abstract_docx.hierarchization.styles import HierarchicalStylesFromOoxml
from abstract_docx.hierarchization.numberings import HierarchicalNumberingsFromOoxml


class HierarchizationConflictResolution(Enum):
	BOUNDED = "bounded"
	UNBOUNDED = "unbounded"

DEFAULT_HIERARCHIZATION_CONFLICT_RESOLUTION: HierarchizationConflictResolution = HierarchizationConflictResolution.UNBOUNDED


class HierarchicalDocumentFromOoxml(ArbitraryBaseModel):
	root: Block

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
			computed_numbering_index_ctr={},
			effective_structure_from_ooxml=effective_structure_from_ooxml,
			styles_view=styles_view,
			numberings_view=numberings_view,
			hierarchization_conflict_resolution=hierarchization_conflict_resolution
		)
		hierarchical_document_from_ooxml.compute()

		return hierarchical_document_from_ooxml
	
	def _traverse(self, curr_block: Block, prev_block: Block) -> None:
		# TODO: implicit_index_matches

		total_priority_difference: int = -1
		if prev_block.id != -1:
			indexes_present: bool = (
				(curr_block.format.index is not None or curr_block.format.implied_index is not None)
				and (prev_block.format.index is not None or prev_block.format.implied_index is not None)
			)
			shared_numbering: bool = (
				indexes_present 
				and (
					curr_block.format.index is None or prev_block.format.index is None
					or (
						curr_block.format.index is not None and prev_block.format.index is not None
						and curr_block.format.index.numbering == prev_block.format.index.numbering
					)
				)
			)

			styles_priority_difference: int = self.styles_view.priority_difference(
				curr_style=curr_block.format.style, prev_style=prev_block.format.style
			)
			if indexes_present and styles_priority_difference == 0:
				styles_priority_difference = self.styles_view.priority_difference(
					curr_style=(
						curr_block.format.index.level.style if curr_block.format.index is not None
						else curr_block.format.implied_index.level.style
					),
					prev_style=(
						prev_block.format.index.level.style if prev_block.format.index is not None
						else prev_block.format.implied_index.level.style
					)
				)

			if shared_numbering:
				numberings_priority_difference: int = self.numberings_view.priority_difference(
					curr_index=(
						curr_block.format.index if curr_block.format.index is not None
						else curr_block.format.implied_index
					),
					prev_index=(
						prev_block.format.index if prev_block.format.index is not None
						else prev_block.format.implied_index
					)
				)
				
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
			case -1:
				# Child
				if prev_block.children is None:
					prev_block.children = [curr_block]
				else:
					prev_block.children.append(curr_block)
				curr_block.parent = prev_block
		
	def compute(self) -> None:
		prev_block: Block = self.root
		for block in self.effective_structure_from_ooxml.document.effective_document.values():
			self._traverse(curr_block=block, prev_block=prev_block)
			prev_block: Block = block


