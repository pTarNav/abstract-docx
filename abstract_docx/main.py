from __future__ import annotations
from typing import Optional
import copy

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx
from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml
from abstract_docx.normalization.format.numberings import numberings_normalization

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
	x = AbstractDocx.read(file_path="test/cp2022_10a01.docx")
	y = EffectiveStylesFromOoxml.normalization(ooxml_styles=x.normalized_ooxml_docx.structure.styles)
	numberings_normalization(ooxml_numberings=x.ooxml_docx.structure.numberings)