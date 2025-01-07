from __future__ import annotations
from typing import Optional

from ooxml_docx.ooxml import OoxmlElement


class Relationship(OoxmlElement):
	"""
	Represents an OOXML relationship.
	Which indicates the relationship between an OOXML element of an OOXML part, with either:
	 - Another OOXML of a different OOXML part (in the same OOXML package), called internal relationship.
	 - An external resource, called external relationship.
	"""
	id: str
	# Note that an enumeration is not used just in case there exists a type not contemplated used in some obscure .docx version
	type: str
	target: str

	@classmethod
	def parse(cls, ooxml_relationship: OoxmlElement) -> Relationship:
		"""
		Reads the contents of an OOXML relationship.
		:param ooxml_relationship: Raw OOXML relationship.
		:return: Parsed relationship representation.
		"""
		return cls(
			element=ooxml_relationship.element,
			id=str(ooxml_relationship.xpath_query("./@Id", nullable=False, singleton=True)),
			type=str(ooxml_relationship.xpath_query("./@Type", nullable=False, singleton=True)),
			target=str(ooxml_relationship.xpath_query("./@Target", nullable=False, singleton=True))
		)


class OoxmlRelationships(OoxmlElement):
	"""
	Represents an OOXML relationships part (identified inside an OOXML package by the '.rels' files of a '_rels' package).
	Contains information about how different OOXML elements between different OOXML parts inside an OOXML package are related.
	"""
	content: dict[str, Relationship] = {}

	@classmethod
	def parse(cls, ooxml_rels: OoxmlElement) -> OoxmlRelationships:
		"""
		Reads the contents of an OOXML relationships part.
		:param ooxml_rels: Raw OOXML relationships part.
		:return: Parsed relationships part representation.
		"""
		return cls(element=ooxml_rels.element, content=cls._parse_relationships(ooxml_rels=ooxml_rels))
	
	@staticmethod
	def _parse_relationships(ooxml_rels: OoxmlElement) -> dict[str, Relationship]:
		"""
		Auxiliary function that contains the logic to parse the read OOXML relationships part.
		:param ooxml_rels: Raw OOXML relationships part.
		:return: Relationships part content representation.
		"""
		# Using local-name in the xpath_query because there is no actual namespace prefix
		ooxml_relationships: Optional[list[OoxmlElement]] = ooxml_rels.xpath_query(query="./*[local-name()='Relationship']")
		if ooxml_relationships is None:
			return {}
		
		content: dict[str, Relationship] = {}
		for ooxml_relationship in ooxml_relationships:
			relationship: Relationship = Relationship.parse(ooxml_relationship=ooxml_relationship)
			content[relationship.id] = relationship
		
		return content