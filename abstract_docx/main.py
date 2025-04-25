from __future__ import annotations
from typing import Optional
import copy

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx
from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml
from abstract_docx.normalization.format.numberings import EffectiveNumberingsFromOoxml

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
	x = AbstractDocx.read(file_path=f"test/{test_files[1]}.docx")
	y = EffectiveStylesFromOoxml.normalization(ooxml_styles=x.normalized_ooxml_docx.structure.styles)
	z = EffectiveNumberingsFromOoxml.normalization(ooxml_numberings=x.ooxml_docx.structure.numberings, effective_styles=y)

	for k, v in z.effective_numberings.items():
		print("#"*21, k, "#"*21)
		for lk, lv in v.levels.items():
			print("=>", lk)
			print(lv)