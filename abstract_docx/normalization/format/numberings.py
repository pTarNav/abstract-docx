from __future__ import annotations
from typing import Optional
from ooxml_docx.structure.numberings import OoxmlNumberings
import ooxml_docx.structure.numberings as OOXML_NUMBERINGS

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.numberings import Numbering, LevelProperties, Level
from abstract_docx.views.format.styles import Style, StyleProperties

from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml


class EffectiveNumberingsFromOoxml(ArbitraryBaseModel):
	"""
	Auxiliary effective numbering class, not designed to structure data (same structure as Numbering),
	 but rather to house the necessary methods to compute the effective style properties.

	In the context of the project, effective means the result from the normalization of the source structure.
	"""
	ooxml_numberings: OoxmlNumberings
	effective_numberings: dict[int, Numbering]

	effective_styles_from_ooxml: EffectiveStylesFromOoxml

	# Auxiliary data for intermediate steps
	_discovered_effective_abstract_numberings: dict[int, Numbering] = {}
	# It might be the case that the effective numbering style has no actual level properties
	_discovered_effective_numbering_styles: dict[str, Optional[Numbering]] = {}

	@classmethod
	def normalization(
			cls, ooxml_numberings: OoxmlNumberings, effective_styles_from_ooxml: EffectiveStylesFromOoxml
		) -> EffectiveNumberingsFromOoxml:
		
		effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml = cls(
			ooxml_numberings=ooxml_numberings, effective_numberings={}, effective_styles_from_ooxml=effective_styles_from_ooxml
		)
		effective_numberings_from_ooxml.load()

		return effective_numberings_from_ooxml

	@staticmethod
	def _check_discovered(id: int | str, effective_discovered_numberings: dict[int | str, Numbering]) -> Optional[Numbering]:
		return effective_discovered_numberings.get(id, None)
		
	def aggregate_effective_numberings(self, agg_numbering: Numbering, add_numbering: Numbering) -> Numbering:
		effective_default_style: Style = self.effective_styles_from_ooxml.get_default()

		levels: dict[int, Level] = {}
		for i in set(list(agg_numbering.levels.keys()) + list(add_numbering.levels.keys())):
			agg_level: Optional[Level] = agg_numbering.levels.get(i, None)
			add_level: Optional[Level] = add_numbering.levels.get(i, None)

			levels[i] = Level(
				id=i,
				properties=LevelProperties.aggregate_ooxml(
					agg=agg_level.properties if agg_level is not None else None,
					add=add_level.properties if add_level is not None else None
				),
				style=Style(
					id=add_level.style.id if add_level is not None else agg_level.style.id,
					properties=StyleProperties.aggregate_ooxml(
						agg=agg_level.style.properties if agg_level is not None else effective_default_style.properties,
						add=add_level.style.properties if add_level is not None else effective_default_style.properties,
						default=effective_default_style.properties
					)
				)
			)

		return Numbering(id=add_numbering.id, levels=levels)
	
	def merge_into_effective_numbering_style(
			self, effective_numbering: Optional[Numbering], effective_abstract_numbering: Optional[Numbering]
		) -> Optional[Numbering]:
			if effective_numbering is None and effective_abstract_numbering is None:
				return None
			
			# Assumption: The merge can actually be treated the same as aggregation
			return self.aggregate_effective_numberings(
				agg_numbering=effective_abstract_numbering, add_numbering=effective_numbering
			)

	def _compute_effective_numbering_style(
			self,
			ooxml_style_parent: OOXML_NUMBERINGS.NumberingStyle,
			visited_ooxml_numberings: list[int],
			visited_ooxml_abstract_numberings: list[int]
		) -> Optional[Numbering]:
		# TODO: maybe divide this function into several chunks, it is too long for sure-
		effective_numbering: Optional[Numbering] = None
		effective_abstract_numbering: Optional[Numbering] = None

		if ooxml_style_parent.abstract_numbering_parent is not None:
			if ooxml_style_parent.abstract_numbering_parent in visited_ooxml_abstract_numberings:
				raise ValueError("") # TODO
			visited_ooxml_abstract_numberings.append(ooxml_style_parent.abstract_numbering_parent.id)

			# If ooxml abstract numbering has already been discovered, use already computed effective numbering
			effective_abstract_numbering = self._discovered_effective_abstract_numberings.get(
				ooxml_style_parent.abstract_numbering_parent.id, None
			)

			if effective_abstract_numbering is None:
				self.compute_effective_numbering(
					ooxml_numbering=None,  # Only interested in computing the abstract numbering
					ooxml_abstract_numbering=ooxml_style_parent.abstract_numbering_parent,
					visited_ooxml_numberings=visited_ooxml_numberings,
					visited_ooxml_abstract_numberings=visited_ooxml_abstract_numberings
				)

				effective_abstract_numbering = self._discovered_effective_abstract_numberings.get(
					ooxml_style_parent.abstract_numbering_parent.id, None
				)
				# The effective abstract numbering must have been discovered in the recursive step
				if effective_abstract_numbering is None:
					raise ValueError("") # TODO

		if ooxml_style_parent.numbering is not None and ooxml_style_parent.numbering not in visited_ooxml_numberings:
			visited_ooxml_numberings.append(ooxml_style_parent.numbering.id)

			# If ooxml numbering has already been discovered, use already computed effective numbering
			effective_numbering = self.effective_numberings.get(ooxml_style_parent.numbering.id, None)
			
			if effective_numbering is None:
				self.compute_effective_numbering(
					ooxml_numbering=ooxml_style_parent.numbering,
					ooxml_abstract_numbering=ooxml_style_parent.numbering.abstract_numbering,
					visited_ooxml_numberings=visited_ooxml_numberings,
					visited_ooxml_abstract_numberings=visited_ooxml_abstract_numberings
				)

				effective_numbering = self.effective_numberings.get(ooxml_style_parent.numbering.id, None)
				# The effective abstract numbering must have been discovered in the recursive step
				if effective_abstract_numbering is None:
					raise ValueError("") # TODO
			
		# Merge: (effective_abstract_numbering) + (effective_numbering) => merged_effective_numbering_style
		merged_effective_numbering_style: Optional[Numbering] = self.merge_into_effective_numbering_style(
			effective_numbering=effective_numbering, effective_abstract_numbering=effective_abstract_numbering
		)
		self._discovered_effective_numbering_styles[merged_effective_numbering_style.id] = merged_effective_numbering_style

		return merged_effective_numbering_style

	def compute_effective_numbering(
			self,
			ooxml_numbering: Optional[OOXML_NUMBERINGS.Numbering],
			ooxml_abstract_numbering: OOXML_NUMBERINGS.AbstractNumbering,
			visited_ooxml_numberings: list[int],
			visited_ooxml_abstract_numberings: list[int]
		) -> None:
		# TODO: maybe divide this function into several chunks, it is too long for sure-

		# Keeps track whether it is the end of the recursion, if it is, it must default
		must_default = True

		visited_ooxml_abstract_numberings.append(ooxml_abstract_numbering.id)

		# If ooxml abstract numbering has already been discovered, use already computed effective numbering
		agg_effective_abstract_numbering: Optional[Numbering] = self._discovered_effective_abstract_numberings.get(
			ooxml_abstract_numbering.id, None
		)

		if agg_effective_abstract_numbering is None:
			effective_numbering_style: Optional[Numbering] = None

			if (
				ooxml_abstract_numbering.associated_styles is not None 
				and ooxml_abstract_numbering.associated_styles.style_parent is not None
			):
				# If this condition is met, it means that there is at least another recursive step needed
				must_default = False

				# If ooxml numbering style has already been discovered, use already computed effective numbering
				effective_numbering_style: Optional[Numbering] = self._discovered_effective_numbering_styles.get(
					ooxml_abstract_numbering.associated_styles.style_parent.id, None
				)

				if effective_numbering_style is None:
					effective_numbering_style = self._compute_effective_numbering_style(
						ooxml_style_parent=ooxml_abstract_numbering.associated_styles.style_parent,
						visited_ooxml_numberings=visited_ooxml_numberings,
						visited_ooxml_abstract_numberings=visited_ooxml_abstract_numberings
					)

			effective_abstract_numbering: Numbering	= Numbering(
				id=ooxml_abstract_numbering.id,
				levels={
					k: Level(
						id=k,
						properties=LevelProperties.from_ooxml(level=v, must_default=must_default),
						style=Style(
							id=f"__@ABSTRACT_NUMBERING={ooxml_abstract_numbering.id}@LEVEL={v.id}__",  # TODO what if it already exists
							properties=StyleProperties.from_ooxml(
								run_properties=v.run_properties,
								paragraph_properties=v.paragraph_properties,
								must_default=must_default
							)
						)
					)
					for k, v in ooxml_abstract_numbering.levels.items()
				}
			)

			if effective_numbering_style is not None:
				# Aggregate: (effective_numbering_style) + effective_abstract_numbering => agg_effective_abstract_numbering
				agg_effective_abstract_numbering: Numbering = self.aggregate_effective_numberings(
					agg_numbering=effective_numbering_style,
					add_numbering=effective_abstract_numbering
				)
			else:
				agg_effective_abstract_numbering = effective_abstract_numbering
			
			self._discovered_effective_abstract_numberings[agg_effective_abstract_numbering.id] = agg_effective_abstract_numbering
		
		if ooxml_numbering is not None:
			effective_numbering: Numbering = Numbering(
				id=ooxml_numbering.id,
				levels={
					k: Level(
						id=k,
						properties=LevelProperties.from_ooxml(level=v.level, must_default=must_default),
						style=Style(
							id=f"__@NUMBERING={ooxml_numbering.id}@LEVEL={v.id}__",  # TODO what if it already exists
							properties=StyleProperties.from_ooxml(
								run_properties=v.level.run_properties if v.level is not None else None,
								paragraph_properties=v.level.paragraph_properties if v.level is not None else None,
								must_default=must_default
							)
						)
					)
					for k, v in ooxml_numbering.overrides.items()
				}
			)

			# Aggregate: agg_effective_abstract_numbering + effective_numbering => agg_effective_numbering
			agg_effective_numbering: Numbering = self.aggregate_effective_numberings(
				agg_numbering=agg_effective_abstract_numbering,
				add_numbering=effective_numbering
			)

			self.effective_numberings[agg_effective_numbering.id] = agg_effective_numbering		

	def _compute_effective_numberings(self) -> None:
		for ooxml_numbering in self.ooxml_numberings.numberings:
			# If ooxml numbering has already been discovered, skip
			effective_numbering: Optional[Numbering] = self.effective_numberings.get(ooxml_numbering.id, None)
			if effective_numbering is None:
				self.compute_effective_numbering(
					ooxml_numbering=ooxml_numbering,
					ooxml_abstract_numbering=ooxml_numbering.abstract_numbering,
					visited_ooxml_numberings=[ooxml_numbering.id],
					visited_ooxml_abstract_numberings=[]
				)

	def _associate_effective_numbering_styles(self) -> None:
		"""_summary_
		"""
		# TODO: Optimize this loop so the inner effective styles loop is only done once
		for effective_numbering in self.effective_numberings.values():
			for effective_level in effective_numbering.levels.values():
				found_effective_style_match: bool = False
				for effective_style in self.effective_styles_from_ooxml.effective_styles.values():
					if effective_level.style == effective_style:
						effective_level.style = effective_style
						found_effective_style_match = True
						break
				
				if not found_effective_style_match:
					self.effective_styles_from_ooxml.effective_styles[effective_level.style.id] = effective_level.style

	def load(self) -> None:
		"""
		"""
		self._compute_effective_numberings()
		self._associate_effective_numbering_styles()