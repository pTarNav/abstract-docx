from __future__ import annotations
from typing import Optional, Literal

from ooxml_docx.ooxml_docx import OoxmlPart
from utils.etree_element_aux import xpath_query

# LXML
from lxml.etree import _Element as etreeElement

class Style:
	"""
	Represents an AbstractDocx style, which is a node of the AbstractDocx style tree.
	"""

	def __init__(self, id: str) -> None:
		"""_summary_
		"""
		self.name = id
		
		self.parent: Optional[Style] = None
		self.children: Optional[list[Style]] = None
	

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


class OoxmlStylesInterface:
	"""
	Interface between the OOXML style definitions part and the AbstractDocx style tree.
	"""

	def __init__(self, styles_ooxml_part: OoxmlPart) -> None:
		"""_summary_

		:param styles_ooxml_part: _description_
		"""
		self.styles_ooxml_part = styles_ooxml_part
		self._style_tree: StyleTree

		self._build_style_tree_from_ooxml()

	@property
	def style_tree(self) -> StyleTree:
		"""
		Interface style tree getter, which allows the user to work with the style tree separately
		from the interface while still having any modifications registered for later compilation.
		:return: The style tree associated to the OOXML styles interface.
		"""
		return self._style_tree
			
	def _build_style_tree_from_ooxml(self) -> None:
		"""_summary_
		"""
		self._style_tree = StyleTree(
			roots=[],
			default=self._build_default_style()
		)


	def _build_default_style(self) -> Style:
		"""
		Generates the default style based on the docDefaults OOXML element.
		:return: The default style, None if not present inside the style definitions part.
		"""
		docDefaults_element = xpath_query(element=self.styles_ooxml_part, query="//w:docDefaults")
		if docDefaults_element is not None:
			return Style(name="default")  # TODO: change for actual style properties logic
		
		return None

	def compile_style_tree(self):
		pass