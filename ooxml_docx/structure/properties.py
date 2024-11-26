from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement


class OoxmlProperty(OoxmlElement):
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


class rPr(OoxmlProperty):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="rPr")


class pPr(OoxmlProperty):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="pPr")


class tblPr(OoxmlProperty):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="tblPr")


class tblStylePr(OoxmlProperty):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="tblStylePr")


class trPr(OoxmlProperty):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="trPr")


class tcPr(OoxmlProperty):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="tcPr")


class numPr(OoxmlProperty):
	def __init__(self, ooxml: OoxmlElement):
		super().__init__(element=ooxml.element, tag="numPr")
