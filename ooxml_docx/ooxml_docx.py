from __future__ import annotations
from typing import Optional, Literal

import zipfile
from io import BytesIO
from pathlib import Path

from ooxml_docx.ooxml import OoxmlPackage
from ooxml_docx.trees.style_tree import OoxmlDocxStyleTree
from utils.pydantic import ArbitraryBaseModel


class OoxmlDocx(ArbitraryBaseModel):
	"""
	Represents and processes the inner Office Open XML (OOXML) structure of a .docx file.
	"""
	file_path: str
	ooxml: OoxmlPackage
	style_tree: OoxmlDocxStyleTree

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
					
		ooxml = OoxmlPackage.load(name=Path(file_path).stem, contents=contents)
		
		#
		style_tree = OoxmlDocxStyleTree.build(
			ooxml_styles_part=ooxml.packages["word"].parts["styles.xml"].element
		)

		return cls(file_path=file_path, ooxml=ooxml, style_tree=style_tree)
	
	def __str__(self):
		s = f"\U0001F4D1 \033[36m\033[1m'{self.file_path}'\033[0m\n"
		s += f"\n{self.ooxml._custom_str_()}"
		s += f"\n{self.style_tree.__str__()}"
		return s
