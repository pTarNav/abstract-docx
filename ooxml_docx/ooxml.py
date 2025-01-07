from __future__ import annotations
from typing import Optional, Any

from lxml import etree
from lxml.etree import _Element as etreeElement
import re

from utils.pydantic import ArbitraryBaseModel


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
		query_result: list[etreeElement] = self.element.xpath(query, namespaces=self._prepare_namespaces())
		
		if len(query_result) == 0:
			if not nullable:
				raise ValueError(f"xpath nullable constraint error for query: {query}")
			return None
		
		if singleton:
			if len(query_result) != 1:
				raise ValueError(f"xpath singleton constraint error for query: {query}\nresult: {query_result}")
			return self._cast_xpath_query_result(query_result_element=query_result[0])
		
		return [
			self._cast_xpath_query_result(query_result_element=query_result_element) for query_result_element in query_result
		]
	
	def _prepare_namespaces(self) -> dict[str, str]:
		"""
		When a namespace is detected without a defined prefix (detected by None being the nsmap key)
		 assign an appropriate prefix to that namespace.
		Even though it won't be used for the actual query, it is just to avoid empty lxml namespace prefix error.
		Use '*[local-name()='x'] to actually search for the desired elements with the empty namespace prefix

		It is assumed that there can only be a maximum of 1 namespace with an empty prefix,
		 because if that is not the key it would actually violate namespace prefix uniqueness of the underlying XML.		
		Decided to go with 'ens' (empty namespace) prefix as a general and neutral option for empty namespace prefix.

		:return: Namespace dictionary without empty namespace key.
		:raises KeyError: If 'ens' is already being used as a prefix for another namespace.
		"""
		if None in self.element.nsmap.keys():
			if "ens" not in self.element.nsmap.keys():
				namespaces = self.element.nsmap.copy()  # Use a copy of the nsmap because lxml nsmap is immutable
				namespaces["ens"] = namespaces.pop(None)
				return namespaces
			else:
				raise KeyError(
					"Empty namespace prefix could not be assigned generic 'ens' prefix because it is already in use"
				)
		
		return self.element.nsmap

	# TODO: maybe to not have to do this weird casting thing for attributes create wrapper function to access attributes
	def _cast_xpath_query_result(self, query_result_element: Any) -> XpathQueryResult:
		"""
		Cast xpath query result to the appropriate OoxmlElement class if eligible.
		Necessary because when xpath is used to search attributes it does not return the XML element but the content itself.

		:param query_result_element: Raw xpath query result.
		:return: Casted xpath query result.
		"""
		if isinstance(query_result_element, etreeElement):
			return OoxmlElement(element=query_result_element)
		
		return query_result_element

	def __str__(self) -> str:
		"""
		Computes XML element string representation using LXML etree.tostring and decoding to utf-8.
		:return: XML element string representation.
		"""
		etree.indent(tree=self.element, space="\t")
		return etree.tostring(self.element, pretty_print=True, encoding="utf-8").decode("utf-8")


# Auxiliary type for the result of the .xpath_query method
XpathQueryResult = Optional[OoxmlElement | list[OoxmlElement] | Any]


class OoxmlPart(ArbitraryBaseModel):
	"""
	Represents an OOXML (Office Open XML) part, which is a component of an OOXML package.
	"""
	name: str
	ooxml: OoxmlElement

	@classmethod
	def load(cls, name: str, content: str) -> OoxmlPart:
		"""
		Initializes an OOXML part with the content of a OOXML file (.xml).
		:param name: The name of the OOXML part. Removing file extension if necessary.
		:param content: String representation of the OOXML.
		"""
		return cls(name=name, ooxml=OoxmlElement(element=etree.fromstring(content)))

	def __str__(self) -> str:
		return f"\U0001F4C4 '{self.name}'"


class OoxmlPackage(ArbitraryBaseModel):
	"""
	Represents an OOXML (Office Open XML) package, which can contain multiple parts and nested packages.
	Can contain an associated package which specifies the relationships between parts ('.rels' file extension).
	"""
	name: str
	content: dict[str, OoxmlPart | OoxmlPackage] = {}
	relationships: Optional[OoxmlPackage] = None

	@classmethod
	def load(cls, name: str, content: dict[str, str]) -> OoxmlPackage:
		"""
		Initializes an OOXML package with the given name and OOXML contents.
		:param name: The name of the OOXML package.
		:param content: Dictionary representation of the OOXML content inside the OOXML package.
		 - Keys: OOXML file part root path name (split by '/').
		 - Values: String representation of the OOXML part.
		"""
		_content = {}
		relationships = None

		# Load package level parts and initialize subpackage structures
		packages: dict[str, dict[str, str]] = {}
		for item_name, item_content in content.items():
			_name = item_name.split("/")
			
			# Load parts found in the package level
			if len(_name) == 1:
				_content[item_name] = OoxmlPart.load(name=item_name, content=item_content)
				continue
			
			# Initialize found subpackage structures in the package level
			if _name[0] not in packages.keys():
				packages[_name[0]] = {}
			packages[_name[0]]["/".join(_name[1:])] = item_content
		
		# Load subpackage levels into the initialized subpackage structures in the package level
		for package_name, package_content in packages.items():
			if package_name == "_rels":
				# Relationships are treated as a special kind of package
				relationships = OoxmlPackage.load(name="_rels", content=package_content)
			else:
				_content[package_name] = OoxmlPackage.load(name=package_name, content=package_content)
		
		return cls(name=name, content=_content, relationships=relationships)

	def __str__(self) -> str:
		return self._tree_str_()

	def _tree_str_(self, depth: int = 0, last: bool = False, line_state: list[bool] = None) -> str:
		"""
		Computes tree string representation of a package.
		:param depth: Indentation depth integer, defaults to 0.
		:param last: Package is the last one from the parent packages list, defaults to False.
		:param line_state: List of bools indicating whether to include vertical connection for each previous indentation depth.
		:return: Package string representation.
		"""
		line_state = line_state if line_state is not None else []
		
		# Compute string representation of package header
		prefix = " " if depth > 0 else ""
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		arrow = prefix + (
			("\u2514\u2500\u2500\u25BA" if last else "\u251c\u2500\u2500\u25BA")
			if depth > 0 else ""
		)
		s = f"{arrow}\U0001F4C1 '{self.name}'\n"

		# Update the line state for the current depth
		if depth > 0:
			if depth >= len(line_state):
				line_state.append(not last)
			else:
				line_state[depth] = not last

		parts: dict[str, OoxmlPart] = {}
		packages: dict[str, OoxmlPackage] = {}
		for k, v in self.content.items():
			if isinstance(v, OoxmlPart):
				parts[k] = v
			elif isinstance(v, OoxmlPackage):
				packages[k] = v

		# Sort parts names alphanumerically
		sorted_parts = sorted(
			parts.keys(),
			key=lambda x: (
				re.sub(r'[^a-zA-Z]+', '', x), int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 0
			)
		)

		# Compute string representation of child parts
		prefix = " "
		for level_state in line_state:
			prefix += "\u2502    " if level_state else "     "
		for i, part in enumerate(sorted_parts):
			arrow = prefix + (
				"\u2514\u2500\u2500\u25BA" if (
					i == len(sorted_parts)-1 and len(packages) == 0 and self.relationships is None
				)
				else "\u251c\u2500\u2500\u25BA"
			)
			if not part.endswith(".rels"):
				s += f"{arrow}\U0001F4C4 '{part}'\n"
			else:
				s += f"{arrow}\u26D3 '{part}'\n"
		
		# Sort packages names
		sorted_packages = sorted(packages.values(), key=lambda x: x.name)

		# Compute string representation of child packages
		for i, package in enumerate(sorted_packages):
			s += package._tree_str_(
				depth=depth+1, last=(i==len(sorted_packages)-1 and self.relationships is None),
				line_state=line_state[:]  # Pass-by-value
			)
		
		# Compute string representation of relationships (_rels)
		if self.relationships is not None:
			s += self.relationships._tree_str_(
				depth=depth+1, last=True, line_state=line_state[:]  # Pass-by-value
			)

		return s
