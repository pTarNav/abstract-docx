from abstract_docx.normalization.format.numberings import EffectiveNumberingsFromOoxml
from abstract_docx.views.format import NumberingsView, StylesView

def numberings_hierarchization(effective_numberings: EffectiveNumberingsFromOoxml, styles_view: StylesView) -> NumberingsView:



	return NumberingsView.load(
		numberings=effective_numberings.effective_numberings,
		enumerations=effective_numberings.effective_enumerations,
		levels=effective_numberings.effective_levels,
		ordered_levels=[]
	)