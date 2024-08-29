from __future__ import annotations
from typing import Optional, Literal

import re

# LXML
from lxml import etree
from lxml.etree import _Element as etreeElement

class OoxmlPart:
	"""
	Represents an OOXML (Office Open XML) part, which is a component of an OOXML package.
	"""

	def __init__(self, ooxml_file_content_element: dict) -> None:
		"""
		Initializes an OOXML part with the content of a OOXML file part.

		:param ooxml_file_content_element: A dictionary containing 'name_tail' and 'content' keys,
		representing the file name and its content.
		"""
		self.name: str
		self.extension: Literal[".xml", ".rels"]

		self.name, self.extension = self._get_name_and_extension_from_part_file_name(
			ooxml_file_content_element["name_tail"]
		)
		self.element: etreeElement = etree.fromstring(ooxml_file_content_element["content"])

	@staticmethod
	def _get_name_and_extension_from_part_file_name(name_tail: str) -> tuple[str, str]:
		"""
		Extracts the name and extension from the OOXML part file name.

		:param name_tail: The file name string to extract the name and extension from.
		:return: A tuple containing the name and extension of the file.
		"""

		regex_result = re.match(r"(.+)(\.[^.]+$)", name_tail)  #
		return regex_result.groups() if regex_result is not None else ("", name_tail)

	def __str__(self) -> str:
		s = f"\U0001F4C4 '{self.name}{self.extension}'\n"
		etree.indent(tree=self.element, space="\t")
		s += etree.tostring(self.element, pretty_print=True, encoding="utf8").decode("utf8")
		return s


class OoxmlPackage:
	"""
	Represents an OOXML (Office Open XML) package, which can contain multiple parts
	and nested packages. It processes the content of a OOXML file to organize and
	manage these parts and packages.
	"""

	def __init__(self, name: str, ooxml_file_content: list) -> None:
		"""
		Initializes an OOXML package with a given name and OOXML file content.

		:param name: The name of the OOXML package.
		:param ooxml_file_content: The content of the OOXML file represented as a list of dictionaries,
		where each dictionary contains 'name_tail' and 'content' keys.
		"""
		self.name = name
		self.parts: dict[str, OoxmlPart] = {}
		self.packages: Optional[dict[str, OoxmlPackage]] = None
		self._rels: Optional[OoxmlPackage] = None

		self._load_package_content(ooxml_file_content=ooxml_file_content)

	def _load_package_content(self, ooxml_file_content: list) -> None:
		"""
		Loads and processes the content of the OOXML file into the package.

		:param ooxml_file_content: The content of the OOXML file represented as a list of dictionaries,
		where each dictionary contains 'name_tail' and 'content' keys.
		"""

		package_content = self._prepare_package_content(ooxml_file_content=ooxml_file_content)
		self._process_package_content(package_content=package_content)

	@staticmethod
	def _prepare_package_content(ooxml_file_content: list) -> dict:
		"""
		Prepares the package content by organizing OOXML file content into a structured dictionary.

		:param ooxml_file_content: The content of the OOXML file represented as a list of dictionaries,
		where each dictionary contains 'name_tail' and 'content' keys.
		:return: A dictionary where the keys are the main part names and the values are lists of
		content elements.
		"""

		package_content = {}
		for ooxml_file_content_element in ooxml_file_content:
			# Divide the file name by the first '/' character
			f_name_head, f_name_tail = (ooxml_file_content_element["name_tail"].split("/", maxsplit=1) + [""])[:2]
			package_content_element = {
				"name_tail": f_name_tail if f_name_tail != "" else f_name_head,
				"content": ooxml_file_content_element["content"]
			}

			#
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
						self._rels = OoxmlPackage(name=f_name, ooxml_file_content=f_content)
					case _:
						if self.packages is None:  # Initialize packages dict
							self.packages = {}
						self.packages[f_name] = OoxmlPackage(name=f_name, ooxml_file_content=f_content)
			else:
				# Process OoxmlPart
				self.parts[f_name] = OoxmlPart(ooxml_file_content_element=f_content[0])

	def __str__(self) -> str:
		return self._custom_str()

	def _custom_str(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		"""_summary_

		:param depth: _description_, defaults to 0
		:param last: _description_, defaults to False
		:param line_state: _description_, defaults to None
		:return: _description_
		"""
		if line_state is None:
			line_state = []
		
		prefix = " "
		for level_state in line_state:
			prefix += "\u2502   " if level_state else "    "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)

		s = f"{arrow}[ {self.name} ]: "
		s += f"(n.parts={len(self.parts)}, n.packages={len(self.packages) if self.packages is not None else 0}, "
		s += f"_rels?={'y' if self._rels is not None else 'n'})\n"

		# Update the line state for the current depth
		if depth >= len(line_state):
			line_state.append(not last)
		else:
			line_state[depth] = not last

		# Sort parts names alphanumerically
		sorted_parts = sorted(self.parts.keys(), key=lambda x: (
				re.sub(r'[^a-zA-Z]+', '', x),
				int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 0
		))

		for i, part in enumerate(sorted_parts):
			prefix = " "
			for level_state in line_state:
				prefix += "\u2502   " if level_state else "    "
			arrow = prefix + (
				"\u2514\u2500\u2500\u25BA" if (i == len(sorted_parts)-1 and self.packages is None)
				else "\u251c\u2500\u2500\u25BA"
			)
			s += f"{arrow}{{ {part} }}\n"
		
		if self.packages is not None:
			sorted_packages = sorted(self.packages.values(), key=lambda x: x.name)
			for i, package in enumerate(sorted_packages):
				s += package._custom_str(
					depth=depth+1, last=i==len(sorted_packages)-1, line_state=line_state
				)

		return s
