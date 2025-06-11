from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import StylesView, Style
from abstract_docx.views.format.numberings import NumberingsView, Index

from abstract_docx.normalization import EffectiveStructureFromOoxml
from abstract_docx.hierarchization import HierarchicalStructureFromOoxml


class Format(ArbitraryBaseModel):
	style: Style
	index: Optional[Index] = None


class FormatView(ArbitraryBaseModel):
	styles: StylesView
	numberings: NumberingsView

	@classmethod
	def load(
		cls,
		effective_structure: EffectiveStructureFromOoxml,
		hierarchical_structure: HierarchicalStructureFromOoxml
	) -> FormatView:
		return cls(
			styles=StylesView.load(
				styles=effective_structure.styles.effective_styles,
				priority_ordered_styles=hierarchical_structure.styles.priority_ordered_styles
			),
			numberings=NumberingsView.load(
				numberings=effective_structure.numberings.effective_numberings,
				enumerations=effective_structure.numberings.effective_enumerations,
				levels=effective_structure.numberings.effective_levels,
				priority_ordered_levels=hierarchical_structure.numberings.priority_ordered_levels
			)
		)
