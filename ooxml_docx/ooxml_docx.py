from __future__ import annotations
from typing import Optional, Literal

import zipfile
from io import BytesIO
from pathlib import Path

from ooxml_docx.ooxml import OoxmlPackage, OoxmlPart
from utils.pydantic import ArbitraryBaseModel


class OoxmlDocx(ArbitraryBaseModel):
	"""
	Represents and processes the inner Office Open XML (OOXML) structure of a .docx file.
	"""
	file_path: str
	package: OoxmlPackage

	@classmethod
	def read(cls, file_path: str) -> OoxmlDocx:
		"""
		"""
		contents: dict[str, str] = {}
		with open(file_path, "rb") as f:
			# Read the .docx file as a .zip and crawl through the contents
			with zipfile.ZipFile(BytesIO(f.read())) as zip_ref:
				for f_name in zip_ref.namelist():
					# TODO: handle other file extensions inside the package
					if f_name.endswith("xml") or f_name.endswith(".rels"):
						contents[f_name] = zip_ref.read(f_name)
					
		package = OoxmlPackage.load(name=Path(file_path).stem, contents=contents)

		return cls(file_path=file_path, package=package)
	
	def __str__(self):
		s = f"\U0001F4D1 \033[36m\033[1m'{self.file_path}'\033[0m\n"
		s += self.package._custom_str_(depth=1, last=True)
		return s
