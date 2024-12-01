from ooxml_docx.ooxml import OoxmlElement


class OoxmlProperties(OoxmlElement):
	"""
	Represents an OOXML (Office Open XML) properties element.
	Where despite a general OOXML properties element not existing in the OOXML standard,
	 it is helpful to have a general class that will enforce tag validation.
	
	Instead of needing to specify the fields for each type of properties element, store as the whole OOXML element.
	Avoids OOXML versioning problems, as properties child elements are the most changed between different versions.
	
	:raises ValueError: Raises error if tag validation is failed.
	"""
	tag: str

	def __init__(self, **data):
		super().__init__(**data)
		self.validate()

	def validate(self) -> None:
		"""
		Share method between all OOXML properties elements which checks if
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
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="pPr")


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
