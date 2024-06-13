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

	def __init__(self, docx_file_content_element: dict) -> None:
		"""
		Initializes an OOXML part with the content of a .docx file part.

		:param docx_file_content_element: A dictionary containing 'name_tail' and 'content' keys,
		representing the file name and its content.
		"""
		self.name: str
		self.extension: Literal[".xml", ".rels"]

		self.name, self.extension = self._get_name_and_extension_from_docx_file_name(
			docx_file_content_element["name_tail"]
		)
		self.element: etreeElement = etree.fromstring(docx_file_content_element["content"])

	@staticmethod
	def _get_name_and_extension_from_docx_file_name(name_tail: str) -> tuple[str, str]:
		"""
		Extracts the name and extension from the .docx part file name.

		:param name_tail: The file name string to extract the name and extension from.
		:return: A tuple containing the name and extension of the file.
		"""

		regex_result = re.match(r"(.+)(\.[^.]+$)", name_tail)
		return regex_result.groups() if regex_result is not None else ("", name_tail)

	def __str__(self) -> str:
		s = f"{{ '{self.name}' ({self.extension}) }}:\n"
		s += etree.tostring(self.element, pretty_print=True, encoding="utf8").decode("utf8")
		return s


class OoxmlPackage:
	"""
	Represents an OOXML (Office Open XML) package, which can contain multiple parts
	and nested packages. It processes the content of a .docx file to organize and
	manage these parts and packages.
	"""

	def __init__(self, name: str, docx_file_content: list) -> None:
		"""
		Initializes an OOXML package with a given name and .docx file content.

		:param name: The name of the OOXML package.
		:param docx_file_content: The content of the .docx file represented as a list of dictionaries,
		where each dictionary contains 'name_tail' and 'content' keys.
		"""
		self.name: str
		self.parts: dict[str, OoxmlPart] = {}
		self.packages: Optional[dict[str, OoxmlPackage]] = None
		self._rels: Optional[OoxmlPackage] = None

		self.name = name
		self._load_package_content(docx_file_content=docx_file_content)

	def _load_package_content(self, docx_file_content: list) -> None:
		"""
		Loads and processes the content of the .docx file into the package.

		:param docx_file_content: The content of the .docx file represented as a list of dictionaries,
		where each dictionary contains 'name_tail' and 'content' keys.
		"""

		package_content = self._prepare_package_content(docx_file_content=docx_file_content)
		self._process_package_content(package_content=package_content)

	@staticmethod
	def _prepare_package_content(docx_file_content: list) -> dict:
		"""
		Prepares the package content by organizing .docx file content into a structured dictionary.

		:param docx_file_content: The content of the .docx file represented as a list of dictionaries,
		where each dictionary contains 'name_tail' and 'content' keys.
		:return: A dictionary where the keys are the main part names and the values are lists of
		content elements.
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
		"""

		for f_name, f_content in package_content.items():
			if len(f_content) > 1 or f_name != f_content[0]["name_tail"]:
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

	def __str__(self) -> str:
		return self._custom_str()

	def _custom_str(self, depth: int = 0) -> str:
		s = f"{chr(9)*(depth-1) + ' '*(depth-1) + chr(9492) + '--> ' if depth > 0 else ''}[ '{self.name}' ]: "
		s += f"(n.parts={len(self.parts)}, n.packages={len(self.packages) if self.packages is not None else 0}, "
		s += f"_rels?={'y' if self._rels is not None else 'n'})\n"

		# Sort parts names alphanumerically
		for part in sorted(self.parts.keys(), key=lambda x: (
				re.sub(r'[^a-zA-Z]+', '', x),
				int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 0
		)):
			s += f"{chr(9)*depth + ' '*depth}\u2514--> {{ {part} }}\n"
		if self.packages is not None:
			for package in sorted(self.packages.values(), key=lambda x: x.name):
				s += package._custom_str(depth=depth+1)

		return s


class OoxmlDocx:
	"""
	Represents and process the inner OOXML structure of a .docx file.
	"""

	def __init__(self, docx_file_path: str) -> None:
		"""
		Initializes the OoxmlDocx instance with the given .docx file path.

		:param docx_file_path: The file path to the .docx file.
		"""
		self.docx_file_path: str
		self.word: OoxmlPackage
		self.doc_props: OoxmlPackage
		self.custom_xml: Optional[OoxmlPackage] = None
		self._content_types: Optional[OoxmlPart] = None
		self._rels: Optional[OoxmlPackage] = None

		self.docx_file_path = docx_file_path
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
					self._rels = OoxmlPackage(name=f_name, docx_file_content=f_content)
				case "[Content_Types].xml":
					self._content_types = OoxmlPart(docx_file_content_element=f_content[0])
				case _:
					raise KeyError(f"Match not found for root .docx package/part {f_name}.")

	def __str__(self):
		s = f"{self.docx_file_path}\n"
		s += self.word._custom_str(depth=1)
		s += self.doc_props._custom_str(depth=1)
		if self.custom_xml is not None:
			s += self.custom_xml._custom_str(depth=1)

		return s
