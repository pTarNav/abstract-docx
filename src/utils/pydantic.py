from pydantic import BaseModel


class ArbitraryBaseModel(BaseModel):
	"""
	Auxiliary BaseModel class to avoid serialization error with etreeElement attributes.
	:param BaseModel: pydantic BaseModel
	"""

	class Config:
		arbitrary_types_allowed = True