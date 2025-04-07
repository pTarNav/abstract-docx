from __future__ import annotations

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx
from abstract_docx.normalization.styles_normalization import styles_normalization

class AbstractDocx(ArbitraryBaseModel):
	"""

	"""
	file_path: str
	ooxml_docx: OoxmlDocx

	@classmethod
	def read(cls, file_path: str) -> AbstractDocx:
		ooxml_docx: OoxmlDocx = OoxmlDocx.read(file_path=file_path)

		return cls(file_path=file_path, ooxml_docx=ooxml_docx)
	
	
if __name__ == "__main__":
	x = AbstractDocx.read(file_path="test/cp2022_10a01.docx")
	styles_normalization(ooxml_styles=x.ooxml_docx.structure.styles)