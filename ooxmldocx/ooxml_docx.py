from __future__ import annotations

import os
import re
import zipfile
from io import BytesIO

from typing import Optional, Literal

from lxml import etree
from lxml.etree import _Element as etreeElement


class OoxmlPart:
	name: str
	extension: Literal[".xml", ".rels"]
	element: etreeElement

	def __init__(self, docx_file_content_element: dict) -> None:
		"""

		:param docx_file_content_element:
		"""

		self.name, self.extension = self._get_name_and_extension_from_docx_file_name(
			docx_file_content_element["name_tail"]
		)
		self.element = etree.fromstring(docx_file_content_element["content"].encode("utf-8"))
		print(self.element.tag)

	@staticmethod
	def _get_name_and_extension_from_docx_file_name(name_tail: str) -> tuple[str, str]:
		"""

		:param name_tail:
		:return name, extension:
		"""

		regex_result = re.match(r"(.+)(\.[^.]+$)", name_tail)
		return regex_result.groups() if regex_result is not None else ("", name_tail)


class OoxmlPackage:
	name: str
	parts: dict[str, OoxmlPart]
	packages: Optional[OoxmlPackage] = None
	_rels: Optional[OoxmlPackage] = None

	def __init__(self, docx_file_content: list) -> None:
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
	_rels: OoxmlPackage

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

		docx_file_content_top = {}
		with open(self.docx_file_path, "rb") as f:
			with zipfile.ZipFile(BytesIO(f.read())) as zip_ref:
				for f_name in zip_ref.namelist():
					if f_name.endswith("xml") or f_name.endswith(".rels"):  # TODO: handle other file extensions
						# Divide the file name by the first '/' character
						f_name_head, f_name_tail = (f_name.split("/", maxsplit=1) + [""])[:2]
						docx_file_content_element = {
								"name_tail": f_name_tail if f_name_tail != "" else f_name_head,
								"content": zip_ref.read(f_name).decode("utf-8")
							}
						if f_name_head in docx_file_content_top.keys():
							docx_file_content_top[f_name_head].append(docx_file_content_element)
						else:
							docx_file_content_top[f_name_head] = [docx_file_content_element]

		# Handle next steps outside the opened .docx file
		for f_name, f_content in docx_file_content_top.items():
			match f_name:
				case "word":
					print(f_name, "0")
				case "docProps":
					print(f_name, "1")
				case "customXml":
					print(f_name, "2")
				case "_rels":
					print(f_name, "3")
				case "[Content_Types].xml":
					self._content_types = OoxmlPart(docx_file_content_element=f_content[0])
				case _:
					raise KeyError()
