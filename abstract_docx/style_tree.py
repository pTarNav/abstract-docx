from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Literal

from ooxml_docx.docx import OoxmlPart
from utils.etree_element_aux import xpath_query


class StyleProperties(BaseModel):
	"""_summary_
	"""


class Style(BaseModel):
	"""
	Represents an AbstractDocx style, which is a node of the AbstractDocx style tree.
	"""
	id: str
	name: str
	properties: StyleProperties
	parent: Optional[Style] = None
	children: Optional[list[Style]] = None


DEFAULT_STYLE: Style = Style(name="default")
class StyleTree:
	"""
	Represents the AbstractDocx style tree.
	"""

	def __init__(self, roots: list[Style] = None, default: Style = DEFAULT_STYLE) -> None:
		"""_summary_

		:param roots: _description_
		:param default: The default style, defaults to DEFAULT_STYLE
		"""
		self.roots = self._validate_roots_input(roots=roots)
		self.default = default

	@staticmethod
	def _validate_roots_input(roots: Optional[list[Style]]) -> list[Style]:
		"""
		Validates roots objects type and handles empty default case.
		:param roots: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		# Empty default case
		if roots is None:
			return []
		
		if not isinstance(roots, list[Style]):
			raise ValueError("roots object must be a <list[Style]> instance")
		
		return roots  # Validation complete