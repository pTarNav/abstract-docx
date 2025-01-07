from __future__ import annotations
import os
from io import BytesIO
import zipfile

from utils.pydantic import ArbitraryBaseModel
from ooxml_docx.ooxml import OoxmlPackage


class OoxmlDocx(ArbitraryBaseModel):
	"""
	Represents and processes the inner Office Open XML (OOXML) structure of a .docx file.
	"""
	file_path: str
	ooxml: OoxmlPackage

	@classmethod
	def read(cls, file_path: str) -> OoxmlDocx:
		"""
		An .docx file can be essentially understood as a compressed folder with an specific file tree structure.
		In order to actually read the contents of the document, first convert the file into a .zip folder.
		This is actually done inside a memory buffer, so no need to actually save the actual compressed folder.
		Then the contents of the document are saved into memory by crawling the file tree structure.
		"""
		contents: dict[str, str] = {}
		with open(file_path, "rb") as f:
			# Read the .docx file as a .zip and crawl through the contents
			with zipfile.ZipFile(BytesIO(f.read())) as zip_ref:
				for f_name in zip_ref.namelist():
					# TODO: handle other file extensions inside the package
					if f_name.endswith(".xml") or f_name.endswith(".rels"):
						contents[f_name] = zip_ref.read(f_name)
		
		return cls(file_path=file_path, ooxml=OoxmlPackage.load(name=os.path.splitext(file_path)[0], content=contents))
	
	def __str__(self):
		s = f"\U0001F4D1 \033[36m\033[1m'{self.file_path}'\033[0m\n"
		s += f"{self.ooxml.__str__()}"
		return s
