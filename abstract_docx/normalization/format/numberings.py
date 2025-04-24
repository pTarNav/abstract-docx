from __future__ import annotations
from typing import Optional
from ooxml_docx.structure.numberings import OoxmlNumberings
import ooxml_docx.structure.numberings as OOXML_NUMBERINGS

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.numberings import Numbering

from ooxml_docx.structure.numberings import OoxmlNumberings, AbstractNumbering, NumberingStyle


class EffectiveNumberingsFromOoxml(ArbitraryBaseModel):
	"""
	Auxiliary effective numbering class, not designed to structure data (same structure as Numbering),
	 but rather to house the necessary methods to compute the effective style properties.

	In the context of the project, effective means the result from the normalization of the source structure.
	"""
	ooxml_numberings: OoxmlNumberings
	effective_numberings: dict[int, Numbering]

	# Auxiliary data for intermediate steps
	_effective_discovered_abstract_numberings: dict[int, Numbering] = {}
	_effective_discovered_numbering_styles: dict[str, Numbering] = {}

	@classmethod
	def normalization(cls, ooxml_numberings: OoxmlNumberings) -> EffectiveNumberingsFromOoxml:
		
		effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml = cls(
			ooxml_numberings=ooxml_numberings, effective_numberings={}
		)
		effective_numberings_from_ooxml.load_effective_numberings()

		return effective_numberings_from_ooxml

	@staticmethod
	def _check_discovered(id: int | str, effective_discovered_numberings: dict[int | str, Numbering]) -> Optional[Numbering]:
		return effective_discovered_numberings.get(id, None)
		
	def _merge_effective_numbering_style(
			self,
			ooxml_style_parent: OOXML_NUMBERINGS.NumberingStyle,
			visited_ooxml_numberings: list[int],
			visited_ooxml_abstract_numberings: list[int]
		) -> Numbering:

		if ooxml_style_parent.abstract_numbering_parent is not None:
			if ooxml_style_parent.abstract_numbering_parent in visited_ooxml_abstract_numberings:
				raise ValueError("") # TODO
			visited_ooxml_abstract_numberings.append(ooxml_style_parent.abstract_numbering_parent.id)

			# If ooxml abstract numbering has already been discovered, use already computed effective numbering
			effective_abstract_numbering: Optional[Numbering] = self._effective_discovered_abstract_numberings.get(
				ooxml_style_parent.abstract_numbering_parent.id, None
			)

			if effective_abstract_numbering is None:
				self.compute_effective_numbering(
					ooxml_abstract_numbering=ooxml_style_parent.abstract_numbering_parent,
					visited_ooxml_numberings=visited_ooxml_numberings,
					visited_ooxml_abstract_numberings=visited_ooxml_abstract_numberings
				)

		if ooxml_style_parent.numbering is not None and ooxml_style_parent.numbering not in visited_ooxml_numberings:
			visited_ooxml_numberings.append(ooxml_style_parent.numbering.id)

			# If ooxml numbering has already been discovered, use already computed effective numbering
			effective_numbering: Optional[Numbering] = self.effective_numberings.get(
				ooxml_style_parent.numbering.id, None
			)
			
			if effective_numbering is None:
				self.compute_effective_numbering(
					ooxml_abstract_numbering=ooxml_style_parent.numbering.abstract_numbering,
					visited_ooxml_numberings=visited_ooxml_numberings,
					visited_ooxml_abstract_numberings=visited_ooxml_abstract_numberings
				)
			
		# Merge: (effective_abstract_numbering) + (effective_numbering) => merged_effective_numbering_style
		merged_effective_numbering_style: Numbering = ...
		self._effective_discovered_numbering_styles[merged_effective_numbering_style.id] = merged_effective_numbering_style

		return merged_effective_numbering_style
	
	def compute_effective_numbering(
			self,
			ooxml_abstract_numbering: OOXML_NUMBERINGS.AbstractNumbering,
			visited_ooxml_numberings: list[int],
			visited_ooxml_abstract_numberings: list[int]
		) -> None:
		visited_ooxml_numberings.append()
		visited_ooxml_abstract_numberings.append(ooxml_abstract_numbering.id)

		# If ooxml abstract numbering has already been discovered, use already computed effective numbering
		effective_abstract_numbering: Optional[Numbering] = self._effective_discovered_abstract_numberings.get(
			ooxml_abstract_numbering.id, None
		)

		if effective_abstract_numbering is None:
			effective_numbering_style: Optional[Numbering] = None

			if (
				ooxml_abstract_numbering.associated_styles is not None 
				and ooxml_abstract_numbering.associated_styles.style_parent is not None
			):
				# If ooxml numbering style has already been discovered, use already computed effective numbering
				effective_numbering_style: Optional[Numbering] = self._effective_discovered_numbering_styles.get(
					ooxml_abstract_numbering.associated_styles.style_parent.id, None
				)

				if effective_numbering_style is None:
					effective_numbering_style = self._merge_effective_numbering_style(
						ooxml_style_parent=ooxml_abstract_numbering.associated_styles.style_parent,
						visited_ooxml_numberings=visited_ooxml_numberings,
						visited_ooxml_abstract_numberings=visited_ooxml_abstract_numberings
					)
					
			# Aggregate: (effective_numbering_style) + effective_abstract_numbering => agg_effective_abstract_numbering
			agg_effective_abstract_numbering: Numbering = ...
			self._effective_discovered_abstract_numberings[agg_effective_abstract_numbering.id] = agg_effective_abstract_numbering
		
		# Aggregate: agg_effective_abstract_numbering + effective_numbering => agg_effective_numbering
		agg_effective_numbering: Numbering = ...
		self.effective_numberings[agg_effective_numbering.id] = agg_effective_numbering		

	def _compute_effective_numberings(self) -> None:
		for ooxml_numbering in self.ooxml_numberings.numberings:
			self.compute_effective_numbering(
				ooxml_abstract_numbering=ooxml_numbering.abstract_numbering,
				visited_ooxml_numberings=[ooxml_numbering.id],
				visited_ooxml_abstract_numberings=[]
			)

	def load_effective_styles(self) -> None:
		"""
		"""
		pass
		
		
