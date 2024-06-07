from __future__ import annotations

import os
import re
import zipfile
from io import BytesIO

from typing import Optional, Literal

from lxml import etree
from lxml.etree import _Element as etreeElement


class OoxmlPart:
	"""
	Represents an OOXML (Office Open XML) part, which is a component of an OOXML package.
	"""

	name: str
	extension: Literal[".xml", ".rels"]
	element: etreeElement

	def __init__(self, docx_file_content_element: dict) -> None:
		"""
		Initializes an OOXML part with the content of a DOCX file element.

		:param docx_file_content_element: A dictionary containing 'name_tail' and 'content' keys,
		representing the file name and its content.
		:type docx_file_content_element: dict
		"""

		self.name, self.extension = self._get_name_and_extension_from_docx_file_name(
			docx_file_content_element["name_tail"]
		)
		self.element = etree.fromstring(docx_file_content_element["content"])

	@staticmethod
	def _get_name_and_extension_from_docx_file_name(name_tail: str) -> tuple[str, str]:
		"""
		Extracts the name and extension from the DOCX file name.

		:param name_tail: The file name string to extract the name and extension from.
		:type name_tail: str
		:return: A tuple containing the name and extension of the file.
		:rtype: tuple[str, str]
		"""

		regex_result = re.match(r"(.+)(\.[^.]+$)", name_tail)
		return regex_result.groups() if regex_result is not None else ("", name_tail)


class OoxmlPackage:
	"""
	Represents an OOXML (Office Open XML) package, which can contain multiple parts
	and nested packages. It processes the content of a DOCX file to organize and
	manage these parts and packages.
	"""

	name: str
	parts: dict[str, OoxmlPart] = {}
	packages: Optional[dict[str, OoxmlPackage]] = None
	_rels: Optional[OoxmlPackage] = None

	def __init__(self, name: str, docx_file_content: list) -> None:
		"""
		Initializes an OOXML package with a given name and DOCX file content.

		:param name: The name of the OOXML package.
		:type name: str
		:param docx_file_content: The content of the DOCX file represented as a list of dictionaries,
		where each dictionary contains 'name_tail' and 'content' keys.
		:type docx_file_content: list
		"""

		self.name = name
		self._load_package_content(docx_file_content=docx_file_content)

	def _load_package_content(self, docx_file_content: list) -> None:
		"""
		Loads and processes the content of the DOCX file into the package.

		:param docx_file_content: The content of the DOCX file represented as a list of dictionaries,
		where each dictionary contains 'name_tail' and 'content' keys.
		:type docx_file_content: list
		"""

		package_content = self._prepare_package_content(docx_file_content=docx_file_content)
		self._process_package_content(package_content=package_content)

	@staticmethod
	def _prepare_package_content(docx_file_content: list) -> dict:
		"""
		Prepares the package content by organizing DOCX file content into a structured dictionary.

		:param docx_file_content: The content of the DOCX file represented as a list of dictionaries,
		where each dictionary contains 'name_tail' and 'content' keys.
		:type docx_file_content: list
		:return: A dictionary where the keys are the main part names and the values are lists of
		content elements.
		:rtype: dict
		"""

		package_content = {}
		for docx_file_content_element in docx_file_content:
			# Divide the file name by the first '/' character
			f_name_head, f_name_tail = (docx_file_content_element["name_tail"].split("/", maxsplit=1) + [""])[:2]
			package_content_element = {
				"name_tail": f_name_tail if f_name_tail != "" else f_name_head,
				"content": docx_file_content_element["content"]
			}
			if f_name_head in package_content.keys():
				package_content[f_name_head].append(package_content_element)
			else:
				package_content[f_name_head] = [package_content_element]

		return package_content

	def _process_package_content(self, package_content: dict) -> None:
		"""
		Processes the prepared package content, organizing it into parts and nested packages.

		:param package_content: A dictionary where the keys are the main part names and the values
		are lists of content elements.
		:type package_content: dict
		"""

		for f_name, f_content in package_content.items():
			if len(f_content) > 1:
				# Process OoxmlPackage
				match f_name:
					case "_rels":
						self._rels = OoxmlPackage(name=f_name, docx_file_content=f_content)
					case _:
						if self.packages is None:  # Initialize packages dict
							self.packages = {}
						self.packages[f_name] = OoxmlPackage(name=f_name, docx_file_content=f_content)
			else:
				# Process OoxmlPart
				self.parts[f_name] = OoxmlPart(docx_file_content_element=f_content[0])


class OoxmlDocx:
	"""
	A class to represent and process a .docx file as an OOXML (Office Open XML) package.

	This class handles the reading and parsing of a .docx file, organizing its contents
	into appropriate OOXML components.
	"""

	docx_file_path: str

	word: OoxmlPackage
	doc_props: OoxmlPackage
	custom_xml: Optional[OoxmlPackage] = None

	_content_types: Optional[OoxmlPart] = None
	_rels: Optional[OoxmlPackage] = None

	def __init__(self, docx_file_path: str) -> None:
		"""
		Initializes the OoxmlDocx instance with the given .docx file path.

		:param docx_file_path: The file path to the .docx file.
		:type docx_file_path: str
		"""

		self.docx_file_path = docx_file_path
		self._load_docx_file_contents()
		print(self.word)

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
		:rtype: dict
		"""

		docx_file_content = {}
		with open(self.docx_file_path, "rb") as f:
			with zipfile.ZipFile(BytesIO(f.read())) as zip_ref:
				for f_name in zip_ref.namelist():
					if f_name.endswith("xml") or f_name.endswith(".rels"):  # TODO: handle other file extensions
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
		:type docx_file_content: dict
		:raises KeyError: If a match is not found for a root .docx package/part.
		"""

		for f_name, f_content in docx_file_content.items():
			match f_name:
				case "word":
					self.word = OoxmlPackage(name=f_name, docx_file_content=f_content)
				case "docProps":
					self.doc_props = OoxmlPackage(name=f_name, docx_file_content=f_content)
				case "customXml":
					self.custom_xml = OoxmlPackage(name=f_name, docx_file_content=f_content)
				case "_rels":
					print(f_name, "3")
				case "[Content_Types].xml":
					self._content_types = OoxmlPart(docx_file_content_element=f_content[0])
				case _:
					raise KeyError(f"Match not found for root .docx package/part {f_name}.")
