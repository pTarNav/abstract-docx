from __future__ import annotations

from abstract_docx.utils.pydantic import ArbitraryBaseModel

from abstract_docx.core.data_models.styles import StylesView
from abstract_docx.core.data_models.numberings import NumberingsView
from abstract_docx.core.data_models.document import DocumentView


# from abstract_docx.core.normalization import EffectiveStructureFromOoxml
# from abstract_docx.core.hierarchization import HierarchicalStructureFromOoxml


class FormatView(ArbitraryBaseModel):
	styles: StylesView
	numberings: NumberingsView


class Views(ArbitraryBaseModel):
	format: FormatView
	document: DocumentView

	@classmethod
	def load(
		cls, effective_structure: "EffectiveStructureFromOoxml", hierarchical_structure: "HierarchicalStructureFromOoxml"
	) -> Views:
		return cls(
			format=FormatView(
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
			),
			document=DocumentView(
				blocks=effective_structure.document.effective_document,
				root=hierarchical_structure.document.root
			)
		)