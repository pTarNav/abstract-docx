from __future__ import annotations
from typing import Optional

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx

from abstract_docx.normalization import EffectiveStructureFromOoxml
from abstract_docx.views import AbstractDocxViews
from abstract_docx.views.document import Paragraph

from abstract_docx.hierarchization.format.styles import styles_hierarchization

class AbstractDocx(ArbitraryBaseModel):
	"""

	"""
	file_path: str
	ooxml_docx: OoxmlDocx

	_effective_structure: Optional[EffectiveStructureFromOoxml] = None
	_views: Optional[AbstractDocxViews] = None

	@classmethod
	def read(cls, file_path: str) -> AbstractDocx:
		ooxml_docx: OoxmlDocx = OoxmlDocx.read(file_path=file_path)

		return cls(file_path=file_path, ooxml_docx=ooxml_docx)
	
	def normalization(self) -> None:
		self._effective_structure = EffectiveStructureFromOoxml.normalization(ooxml_docx=self.ooxml_docx)

	@property
	def effective_structure(self) -> EffectiveStructureFromOoxml:
		if self._effective_structure is not None:
			return self._effective_structure

		raise ValueError("Please call")
	
	@property
	def views(self) -> EffectiveStructureFromOoxml:
		if self._views is not None:
			return self._views

		raise ValueError("Please call")

	def hierarchization(self) -> None:
		order_styles = styles_hierarchization(effective_styles=self._effective_structure.styles.effective_styles)

		for p in self._effective_structure.document.effective_document.values():
			if isinstance(p, Paragraph):
				for i, pl in enumerate(order_styles):
					if p.format.style in pl:
						print(f"[{i} {p.format.style.id}]")
						print("##"*i, p)
						break

	def __call__(self, *args, **kwds) -> None:
		"""
		In the call function because they can be parametrized
		"""

		self.normalization()
		self.hierarchization()
	
	
if __name__ == "__main__":
	test_files = ["sample3", "cp2022_10a01", "A6.4-PROC-ACCR-002", "SB004_report"]
	x = AbstractDocx.read(file_path=f"test/{test_files[3]}.docx")
	x()	