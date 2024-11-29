from ooxml_docx.ooxml import OoxmlElement


class OoxmlProperties(OoxmlElement):
	"""_summary_


	:raises ValueError: _description_
	"""
	tag: str

	def __init__(self, **data):
		super().__init__(**data)
		self.validate()

	def validate(self) -> bool:
		"""_summary_

		:raises ValueError: _description_
		:return: _description_
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
