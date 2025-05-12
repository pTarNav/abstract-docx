from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.document import Block
from abstract_docx.views.format import FormatsView

class AbstractDocxViews(ArbitraryBaseModel):
	format: FormatsView
	document: dict[int, Block]