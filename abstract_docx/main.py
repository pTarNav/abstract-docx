from __future__ import annotations
from typing import Optional
import copy
from itertools import combinations

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx
import ooxml_docx.document as OOXML_DOCUMENT
from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml
from abstract_docx.normalization.format.numberings import EffectiveNumberingsFromOoxml
from abstract_docx.normalization.document import document_normalization
from abstract_docx.views.format.styles import Style, StyleProperties, RunStyleProperties, ParagraphStyleProperties

class AbstractDocx(ArbitraryBaseModel):
	"""

	"""
	file_path: str
	ooxml_docx: OoxmlDocx
	normalized_ooxml_docx: OoxmlDocx  # Initialized as a deep copy of the inputted ooxml_docx

	@classmethod
	def read(cls, file_path: str) -> AbstractDocx:
		ooxml_docx: OoxmlDocx = OoxmlDocx.read(file_path=file_path)

		return cls(file_path=file_path, ooxml_docx=ooxml_docx, normalized_ooxml_docx=copy.deepcopy(ooxml_docx))
	
	
if __name__ == "__main__":
	test_files = ["sample3", "cp2022_10a01", "A6.4-PROC-ACCR-002", "SB004_report"]
	x = AbstractDocx.read(file_path=f"test/{test_files[2]}.docx")
	y = EffectiveStylesFromOoxml.normalization(ooxml_styles=x.normalized_ooxml_docx.structure.styles)
	z = EffectiveNumberingsFromOoxml.normalization(ooxml_numberings=x.ooxml_docx.structure.numberings, effective_styles=y)

	document_normalization(x, y, z)