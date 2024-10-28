from __future__ import annotations
from pydantic import Field
from typing import Optional

import re

from lxml import etree
from lxml.etree import _Element as etreeElement

from utils.etree import etree_to_str
from utils.pydantic import ArbitraryBaseModel


class OoxmlPart(ArbitraryBaseModel):
	"""
	Represents an OOXML (Office Open XML) part, which is a component of an OOXML package.
	"""
	name: str
	element: etreeElement

	@classmethod
	def load(cls, name: str, content: str) -> OoxmlPart:
		"""
		Initializes an OOXML part with the content of a OOXML file part.

		:param name: The name of the OOXML part.
		:param content: String representation of the OOXML.
		"""
		return cls(name=name, element=etree.fromstring(content))

	def __str__(self) -> str:
		return f"\U0001F4C4 '{self.name}'\n{etree_to_str(element=self.element)}"


class OoxmlPackage(ArbitraryBaseModel):
	"""
	Represents an OOXML (Office Open XML) package, which can contain multiple parts and nested packages.
	Can contain an associated package which specifies the relationships between parts (identified by the '_rels' file extension).
	"""
	name: str

	# Note that it avoids using a mutable default dictionary which can lead to unintended behavior,
	# using pydantic dictionary field generator instead.
	parts: dict[str, OoxmlPart] = Field(default_factory=dict)
	packages: dict[str, OoxmlPackage] = Field(default_factory=dict)

	relationships: Optional[OoxmlPackage] = None

	@classmethod
	def load(cls, name: str, contents: dict[str, str]) -> OoxmlPackage:
		"""
		Initializes an OOXML package with a given name and contents.

		:param name: The name of the OOXML package.
		:param contents: Dictionary representation of the OOXML parts inside the OOXML package.
		 - Keys: OOXML file part root path name (separated by '/').
		 - Values: String representation of the OOXML.
		"""
		parts = {}
		packages = {}
		relationships = None

		# Load package level and initialize subpackage structures
		_packages: dict[str, dict[str, str]] = {}
		for _name, content in contents.items():
			name_split = _name.split("/")
			
			# Load parts found in the package level
			if len(name_split) == 1:
				parts[_name] = OoxmlPart.load(name=_name, content=content)
				continue
			
			# Initialize found subpackage structures in the package level
			if name_split[0] not in _packages.keys():
				_packages[name_split[0]] = {}
			_packages[name_split[0]]["/".join(name_split[1:])] = content
		
		# Load subpackage levels into the initialized subpackage structures in the package level
		for _name, contents in _packages.items():
			if _name == "_rels":
				relationships = OoxmlPackage.load(name="_rels", contents=contents)
			else:
				packages[_name] = OoxmlPackage.load(name=_name, contents=contents)
		
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
