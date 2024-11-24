from __future__ import annotations
from typing import Optional
from utils.pydantic import ArbitraryBaseModel

import os

from lxml import etree
from lxml.etree import _Element as etreeElement


class OoxmlElement(ArbitraryBaseModel):
	"""
	Represents an OOXML (Office Open XML) element.
	Wrapper class for lxml _Element (referenced throughout as etreeElement).
	"""
	element: etreeElement

	@property
	def local_name(self) -> str:
		"""
		Removes namespace from the XML element name.
		:return: Clean XML element name without the namespace prefix.
		"""
		return etree.QName(self.element).localname

	@property
	def skeleton(self) -> OoxmlElement:
		"""
		Computes the element skeleton (node metadata without including the child nodes information) of an XML element.
		:return: XML element skeleton.
		"""
		return OoxmlElement(element=etree.Element(self.element.tag, attrib=self.element.attrib))


	def xpath_query(self, query: str, nullable: bool = True, singleton: bool = False) -> XpathQueryResult:
		"""
		Wrapper of the .xpath() class function of the lxml package to avoid having to specify the namespaces every time.
		Handles the empty result cases, where instead of an empty list returns None.
		Also handles nullable and singleton constraints set by the user.
		:param query: Xpath query string.
		:param nullable: Boolean indicating whether the result can be None, defaults to True.
		:param singleton: Boolean indicating whether the result should only yield no results or one result, defaults to False.
		:return: Xpath query results, None when the result is empty.
		:raises ValueError: Raises error if nullable or single constraints are failed.
		"""
		query_result: etreeElement = self.element.xpath(query, namespaces=self.element.nsmap)
		
		if len(query_result) == 0:
			if not nullable:
				raise ValueError(f"xpath nullable constraint error for query: {query}")
			return None
		
		if singleton:
			if len(query_result) != 1:
				raise ValueError(f"xpath singleton constraint error for query: {query}\nresult: {query_result}")
			return query_result[0]
		
		return OoxmlElement(element=query_result)

	def __str__(self) -> str:
		"""
		Computes XML element string representation using LXML etree.tostring and decoding to utf-8.
		:return: XML element string representation.
		"""
		etree.indent(tree=self.element, space="\t")
		return etree.tostring(self.element, pretty_print=True, encoding="utf-8").decode("utf-8")


XpathQueryResult = Optional[OoxmlElement | list[OoxmlElement]]


class OoxmlPart(ArbitraryBaseModel):
	"""
	Represents an OOXML (Office Open XML) part, which is a component of an OOXML package.
	"""
	name: str
	element: OoxmlElement

	@classmethod
	def load(cls, name: str, content: str) -> OoxmlPart:
		"""
		Initializes an OOXML part with the content of a OOXML file (.xml).

		:param name: The name of the OOXML part. Removing .xml extension if necessary.
		:param content: String representation of the OOXML.
		"""
		return cls(name=os.path.splitext(name), element=OoxmlElement(element=etree.fromstring(content)))

	def __str__(self) -> str:
		return f"\U0001F4C4 '{self.name}'\n{self.element.__str__()}"


class OoxmlPackage(ArbitraryBaseModel):
	"""
	Represents an OOXML (Office Open XML) package, which can contain multiple parts and nested packages.
	Can contain an associated package which specifies the relationships between parts (identified by the '_rels' file extension).
	"""
	name: str
	parts: dict[str, OoxmlPart] = {}
	packages: dict[str, OoxmlPackage] = {}	
	relationships: Optional[OoxmlPackage] = None

	@classmethod
	def load(cls, name: str, contents: dict[str, str]) -> OoxmlPackage:
		"""
		Initializes an OOXML package with the given name and OOXML contents.

		:param name: The name of the OOXML package.
		:param contents: Dictionary representation of the OOXML content inside the OOXML package.
		 - Keys: OOXML file part root path name (split by '/').
		 - Values: String representation of the OOXML part.
		"""
		parts = {}
		packages = {}
		relationships = None

		# Load package level parts and initialize subpackage structures
		_packages: dict[str, dict[str, str]] = {}
		for content_name, content in contents.items():
			# Remove file name extension and split by directory structure
			_name = os.path.splitext(content_name)[0].split("/")
			
			# Load parts found in the package level
			if len(_name) == 1:
				parts[content_name] = OoxmlPart.load(name=content_name, content=content)
				continue
			
			# Initialize found subpackage structures in the package level
			if _name[0] not in _packages.keys():
				_packages[_name[0]] = {}
			_packages[_name[0]]["/".join(_name[1:])] = content
		
		# Load subpackage levels into the initialized subpackage structures in the package level
		for package_name, contents in _packages.items():
			if package_name == "_rels":
				relationships = OoxmlPackage.load(name="_rels", contents=contents)
			else:
				packages[package_name] = OoxmlPackage.load(name=package_name, contents=contents)
		
		return cls(name=name, parts=parts, packages=packages, relationships=relationships)

	def __str__(self) -> str:
		return self._custom_str_()

	def _custom_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		"""
		Computes string representation of a package.

		:param depth: Indentation depth integer, defaults to 0.
		:param last: Package is the last one from the parent packages list, defaults to False.
		:param line_state: List of booleans indicating whether to include vertical connection
		 for each previous indentation depth,
		 defaults to None to avoid mutable list initialization unexpected behavior.
		:return: Package string representation.
		"""
		if line_state is None:
			line_state = []
		
		# Compute string representation of package header
		prefix = " " if depth > 0 else ""
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)
		if self.name != "_rels":
			s = f"{arrow}\U0001F4C1 '{self.name}'"
			
			# Compute string representation of package metadata
			s += "("
			s += f"n.parts={len(self.parts)}, "
			s += f"n.packages={len(self.packages) if self.packages is not None else 0}"
			s += ")\n"
		else:
			s = f"{arrow}\u26D3 \U0001F4C1 '_rels'\n"

		# Update the line state for the current depth
		if depth > 0:
			if depth >= len(line_state):
				line_state.append(not last)
			else:
				line_state[depth] = not last

		# Sort parts names alphanumerically
		sorted_parts = sorted(self.parts.keys(), key=lambda x: (
				re.sub(r'[^a-zA-Z]+', '', x),
				int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 0
		))

		# Compute string representation of child parts
		prefix = " "
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		for i, part in enumerate(sorted_parts):
			arrow = prefix + (
				"\u2514\u2500\u2500\u25BA" if (
					i == len(sorted_parts)-1 
					and len(self.packages) == 0 and self.relationships is None
				)
				else "\u251c\u2500\u2500\u25BA"
			)
			if not part.endswith(".rels"):
				s += f"{arrow}\U0001F4C4 '{part}'\n"
			else:
				s += f"{arrow}\u26D3 \U0001F4C4 '{part}'\n"
		
		# Sort packages names
		sorted_packages = sorted(self.packages.values(), key=lambda x: x.name)

		# Compute string representation of child packages
		for i, package in enumerate(sorted_packages):
			s += package._custom_str_(
				depth=depth+1, last=(i==len(sorted_packages)-1 and self.relationships is None),
				line_state=line_state[:]  # Pass-by-value
			)
		
		# Compute string representation of relationships (_rels)
		if self.relationships is not None:
			s += self.relationships._custom_str_(
				depth=depth+1, last=True, line_state=line_state[:]  # Pass-by-value
			)

		return s
