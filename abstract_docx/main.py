from __future__ import annotations
from typing import Optional
import copy
from itertools import combinations

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx
import ooxml_docx.document as OOXML_DOCUMENT
from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml
from abstract_docx.normalization.format.numberings import EffectiveNumberingsFromOoxml
from abstract_docx.normalization.document import EffectiveDocumentFromOoxml
from abstract_docx.views.format.styles import Style, StyleProperties, RunStyleProperties, ParagraphStyleProperties
from abstract_docx.views.format.numberings import Numbering

from abstract_docx.normalization import EffectiveStructureFromOoxml

class AbstractDocx(ArbitraryBaseModel):
	"""

	"""
	file_path: str
	ooxml_docx: OoxmlDocx

	_effective: EffectiveStructureFromOoxml

	@classmethod
	def read(cls, file_path: str) -> AbstractDocx:
		ooxml_docx: OoxmlDocx = OoxmlDocx.read(file_path=file_path)
		_effective: EffectiveStructureFromOoxml = EffectiveStructureFromOoxml.normalization(ooxml_docx=ooxml_docx)

		return cls(file_path=file_path, ooxml_docx=ooxml_docx, _effective=_effective)
	
	
	
	
if __name__ == "__main__":
	test_files = ["sample3", "cp2022_10a01", "A6.4-PROC-ACCR-002", "SB004_report"]
	x = AbstractDocx.read(file_path=f"test/{test_files[1]}.docx")
	