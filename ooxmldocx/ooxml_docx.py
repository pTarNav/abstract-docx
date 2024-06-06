from __future__ import annotations

import os
import zipfile
from io import BytesIO

from typing import Optional

from lxml import etree
from lxml.etree import _Element as etreeElement


class OoxmlPart:
	name: str
	element: etreeElement


class OoxmlPackage:
	name: str
	parts: dict[str, OoxmlPart]
	packages: Optional[OoxmlPackage] = None
	_rels: Optional[OoxmlPackage] = None

	def __init__(self, docx_file_content: dict) -> None:
		"""

		:param docx_file_content:
		"""

		pass


class OoxmlDocx:
	docx_file_path: str

	word: OoxmlPackage
	doc_props: OoxmlPackage
	custom_xml: Optional[OoxmlPackage] = None

	_content_types: Optional[OoxmlPart] = None
	_rels: Optional[OoxmlPackage] = None

	def __init__(self, docx_file_path: str) -> None:
		"""

		:param docx_file_path:
		"""

		self.docx_file_path = docx_file_path
		self._load_docx_file_contents()

	def _load_docx_file_contents(self) -> None:
		"""
		Read the .docx file as a zip file in memory, loading each content into its correspondent ooxml docx content
		"""

		docx_file_content = {}
		with open(self.docx_file_path, "rb") as f:
			with zipfile.ZipFile(BytesIO(f.read())) as zip_ref:

				for f_name in zip_ref.namelist():
					if f_name.endswith("xml") or f_name.endswith(".rels"):  # TODO: handle other file extensions
						# Divide the file name by the first / character (handle cases where
						f_name_head, f_name_tail = (f_name.split("/", 1) + [""])[:2]
						docx_file_content[f_name_head] = {
							"name_tail": f_name_tail,
							"content": zip_ref.read(f_name).decode("utf-8")
						}

		# Handle next steps outside the opened .docx file
		pass