from __future__ import annotations
from typing import Optional, Literal

import zipfile
from io import BytesIO

from ooxml_docx.ooxml import OoxmlPackage, OoxmlPart


class OoxmlDocxTree:
	def __init__(self) -> None:
		pass


class OoxmlDocx:
	"""
	Represents and process the inner OOXML structure of a .docx file.
	"""

	def __init__(self, docx_file_path: str) -> None:
		"""
		Initializes the OoxmlDocx instance with the given .docx file path.

		:param docx_file_path: The file path to the .docx file.
		"""
		self.docx_file_path = docx_file_path
		self.word: OoxmlPackage
		self.doc_props: OoxmlPackage
		self.custom_xml: Optional[OoxmlPackage] = None
		self._content_types: Optional[OoxmlPart] = None
		self._rels: Optional[OoxmlPackage] = None

		self._load_docx_file_contents()

	def _load_docx_file_contents(self) -> None:
		"""
		Reads the .docx file as a zip file in memory, loading each content into its
		corresponding OoxmlDocx content.
		"""

		docx_file_content = self._prepare_docx_file_content()
		self._process_docx_file_content(docx_file_content=docx_file_content)

	def _prepare_docx_file_content(self) -> dict:
		"""
		Prepares the .docx file content by reading the file and extracting XML and relationship files.

		:return: A dictionary representing the file content organized by the main parts of the .docx file.
		"""

		docx_file_content = {}
		with open(self.docx_file_path, "rb") as f:
			with zipfile.ZipFile(BytesIO(f.read())) as zip_ref:
				for f_name in zip_ref.namelist():
					# TODO: handle other file extensions inside the package
					if f_name.endswith("xml") or f_name.endswith(".rels"):
						# Divide the file name by the first '/' character
						f_name_head, f_name_tail = (f_name.split("/", maxsplit=1) + [""])[:2]
						docx_file_content_element = {
							"name_tail": f_name_tail if f_name_tail != "" else f_name_head,
							"content": zip_ref.read(f_name)
						}

						if f_name_head in docx_file_content.keys():
							docx_file_content[f_name_head].append(docx_file_content_element)
						else:
							docx_file_content[f_name_head] = [docx_file_content_element]

		return docx_file_content

	def _process_docx_file_content(self, docx_file_content: dict) -> None:
		"""
		Processes the prepared .docx file content, assigning it to the appropriate attributes.

		:param docx_file_content: The dictionary representing the file content organized by the main parts of the .docx file.
		:raises KeyError: If a match is not found for a root .docx package/part.
		"""

		for f_name, f_content in docx_file_content.items():
			match f_name:
				case "word":
					self.word = OoxmlPackage(name=f_name, ooxml_file_content=f_content)
				case "docProps":
					self.doc_props = OoxmlPackage(name=f_name, ooxml_file_content=f_content)
				case "customXml":
					self.custom_xml = OoxmlPackage(name=f_name, ooxml_file_content=f_content)
				case "_rels":
					self._rels = OoxmlPackage(name=f_name, ooxml_file_content=f_content)
				case "[Content_Types].xml":
					self._content_types = OoxmlPart(ooxml_file_content_element=f_content[0])
				case _:
					raise KeyError(f"Match not found for root .docx package/part {f_name}.")

	def __str__(self):
		s = f"\U0001F4D1 \033[36m\033[1m'{self.docx_file_path}'\033[0m\n"

		s += self.word._custom_str(depth=1)
		s += self.doc_props._custom_str(depth=1, last=self.custom_xml is None)
		if self.custom_xml is not None:
			s += self.custom_xml._custom_str(depth=1, last=True)

		return s
