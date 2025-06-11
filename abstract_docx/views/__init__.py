from __future__ import annotations

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format import FormatView
from abstract_docx.views.document import DocumentView

# from abstract_docx.normalization import EffectiveStructureFromOoxml
# from abstract_docx.hierarchization import HierarchicalStructureFromOoxml


class AbstractDocxViews(ArbitraryBaseModel):
	format: FormatView
	document: DocumentView

	@classmethod
	def load(
		cls,
		effective_structure: "EffectiveStructureFromOoxml",
		hierarchical_structure: "HierarchicalStructureFromOoxml"
	) -> AbstractDocxViews:
		return cls(
			format=FormatView.load(
				effective_structure=effective_structure,
				hierarchical_structure=hierarchical_structure
			),
			document=DocumentView.load(
				blocks=effective_structure.document.effective_document,
				root=hierarchical_structure.document.root
			)
		)