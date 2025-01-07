from __future__ import annotations
from typing import Optional
from ooxml_docx.ooxml import OoxmlElement


class Relationship(OoxmlElement):
	id: str
	type: str
	target: str

	@classmethod
	def parse(cls, ooxml_relationship: OoxmlElement) -> Relationship:
		"""_summary_

		:param ooxml_relationship: _description_
		:return: _description_
		"""
		return cls(
			element=ooxml_relationship.element,
			id=str(ooxml_relationship.xpath_query("./@Id", nullable=False, singleton=True)),
			type=str(ooxml_relationship.xpath_query("./@Type", nullable=False, singleton=True)),
			target=str(ooxml_relationship.xpath_query("./@Target", nullable=False, singleton=True))
		)


class OoxmlRelationships(OoxmlElement):
	content: dict[str, Relationship] = {}

	@classmethod
	def parse(cls, ooxml_rels: OoxmlElement) -> OoxmlRelationships:
		"""_summary_

		:param ooxml_relationships: _description_
		:return: _description_
		"""
		return cls(element=ooxml_rels.element, content=cls._parse_relationships(ooxml_rels=ooxml_rels))
	
	@staticmethod
	def _parse_relationships(ooxml_rels: OoxmlElement) -> dict[str, Relationship]:
		"""_summary_

		:param ooxml_relationships: _description_
		:return: _description_
		"""
		ooxml_relationships: Optional[list[OoxmlElement]] = ooxml_rels.xpath_query(query="./*[local-name()='Relationship']")
		if ooxml_relationships is None:
			return {}
		
		content: dict[str, Relationship] = {}
		for ooxml_relationship in ooxml_relationships:
			relationship: Relationship = Relationship.parse(ooxml_relationship=ooxml_relationship)
			content[relationship.id] = relationship
		
		return content