from __future__ import annotations
from typing import Optional

from ooxml_docx.ooxml import OoxmlElement
from pydantic import PrivateAttr

class OoxmlProperties(OoxmlElement):
	"""
	Representation of an OOXML properties element.
	Where, despite a general OOXML properties element not existing in the OOXML standard,
	 it is helpful to have a general class that will enforce tag validation.
	
	Instead of needing to specify the fields for each type of properties element, store as the whole OOXML element.
	Avoids OOXML versioning problems, as properties child elements are the most changed between different OOXML versions.
	
	:raises ValueError: Raises error if tag validation is failed.
	"""
	tag: str

	def __init__(self, **data):
		super().__init__(**data)
		self.validate()

	def validate(self) -> None:
		"""
		Shared method between all OOXML properties elements which checks if
		 the parsed element tag matches with the expected type of properties element.

		:raises ValueError: Raises error if tag validation is failed.
		"""
		if self.local_name != self.tag:
			raise ValueError(
				f"<{self.__class__.__name__}> requires OOXML <w:{self.tag}> element, received <w:{self.local_name}> instead"
			)


class RunProperties(OoxmlProperties):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="rPr")


class ParagraphProperties(OoxmlProperties):
	_run_properties: Optional[RunProperties] = PrivateAttr(default=None)

	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="pPr")
	
		ooxml_run_properties: Optional[OoxmlElement] = ooxml.xpath_query(query="./rPr", singleton=True)
		self._run_properties = RunProperties(ooxml=ooxml_run_properties) if ooxml_run_properties is not None else None
	
	@property
	def run_properties(self) -> Optional[RunProperties]:
		return self._run_properties

class TableProperties(OoxmlProperties):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="tblPr")


class TableConditionalProperties(OoxmlProperties):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="tblStylePr")


class TableRowProperties(OoxmlProperties):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="trPr")


class TableCellProperties(OoxmlProperties):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="tcPr")


class NumberingProperties(OoxmlProperties):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="numPr")
