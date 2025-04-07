from __future__ import annotations

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.docx import OoxmlDocx


class AbstractDocx(ArbitraryBaseModel):
	"""

	"""
	file_path: str
	ooxml_docx: OoxmlDocx

	@classmethod
	def read(cls, file_path: str) -> AbstractDocx:
		ooxml_docx: OoxmlDocx = OoxmlDocx.read(file_path=file_path)
		ooxml_docx.build()

		return cls(file_path=file_path, ooxml_docx=ooxml_docx)
	
	
if __name__ == "__main__":
	x = AbstractDocx.read(file_path="test/cp2022_10a01.docx")
