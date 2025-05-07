from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.document import Block
from abstract_docx.views.format import AbstractDocxFormatViews

class AbstractDocxViews(ArbitraryBaseModel):
	format: AbstractDocxFormatViews
	document: dict[int, Block]