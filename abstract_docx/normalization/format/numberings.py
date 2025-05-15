from __future__ import annotations
from typing import Optional
from ooxml_docx.structure.numberings import OoxmlNumberings
import ooxml_docx.structure.numberings as OOXML_NUMBERINGS

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.numberings import Numbering, Enumeration, LevelProperties, Level
from abstract_docx.views.format.styles import Style, StyleProperties

from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml


class EffectiveNumberingsFromOoxml(ArbitraryBaseModel):
	"""
	Auxiliary effective numbering class, not designed to structure data (same structure as Numbering),
	 but rather to house the necessary methods to compute the effective style properties.

	In the context of the project, effective means the result from the normalization of the source structure.

	TODO:
	Be careful kind of confusing:
	- Abstract numbering => Numbering (However intermediate steps to compute enumerations use abstract enumerations, which are the enumeration representation of the abstract numbering)
	- Numbering => Enumeration
	"""
	ooxml_numberings: OoxmlNumberings

	effective_numberings: dict[int, Numbering]
	effective_enumerations: dict[int, Enumeration]
	effective_levels: dict[int, dict[int, Level]]

	effective_styles_from_ooxml: EffectiveStylesFromOoxml

	# Auxiliary data for intermediate steps
	_discovered_effective_abstract_enumerations: dict[int, Enumeration] = {}
	# It might be the case that the effective enumeration style has no actual level properties
	_discovered_effective_enumeration_styles: dict[str, Optional[Enumeration]] = {}

	@staticmethod
	def load_effective_numberings(ooxml_abstract_numberings: list[OOXML_NUMBERINGS.AbstractNumbering]) -> dict[int, Numbering]:
		return {
			ooxml_abstract_numbering.id: Numbering(id=ooxml_abstract_numbering.id, enumerations={})
			for ooxml_abstract_numbering in ooxml_abstract_numberings
		}

	@classmethod
	def normalization(
			cls, ooxml_numberings: OoxmlNumberings, effective_styles_from_ooxml: EffectiveStylesFromOoxml
		) -> EffectiveNumberingsFromOoxml:
		effective_numberings: dict[int, Numbering] = cls.load_effective_numberings(
			ooxml_abstract_numberings=ooxml_numberings.abstract_numberings
		)

		effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml = cls(
			ooxml_numberings=ooxml_numberings,
			effective_numberings=effective_numberings,
			effective_enumerations={},
			effective_levels={},
			effective_styles_from_ooxml=effective_styles_from_ooxml
		)
		effective_numberings_from_ooxml.load()

		return effective_numberings_from_ooxml

	@staticmethod
	def _check_discovered(id: int | str, effective_discovered_enumerations: dict[int | str, Enumeration]) -> Optional[Enumeration]:
		return effective_discovered_enumerations.get(id, None)
		
	def aggregate_effective_enumerations(self, agg_enumeration: Enumeration, add_enumeration: Enumeration) -> Enumeration:
		effective_default_style: Style = self.effective_styles_from_ooxml.get_default()

		levels: dict[int, Level] = {}
		for i in set(list(agg_enumeration.levels.keys()) + list(add_enumeration.levels.keys())):
			agg_level: Optional[Level] = agg_enumeration.levels.get(i, None)
			add_level: Optional[Level] = add_enumeration.levels.get(i, None)

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

		return Enumeration(id=add_enumeration.id, levels=levels)
	
	def merge_into_effective_enumeration_style(
			self, effective_enumeration: Optional[Enumeration], effective_abstract_enumeration: Optional[Enumeration]
		) -> Optional[Enumeration]:
			if effective_enumeration is None and effective_abstract_enumeration is None:
				return None
			
			# Assumption: The merge can actually be treated the same as aggregation
			return self.aggregate_effective_enumerations(
				agg_enumeration=effective_abstract_enumeration, add_enumeration=effective_enumeration
			)

	def _compute_effective_enumeration_style(
			self,
			ooxml_style_parent: OOXML_NUMBERINGS.NumberingStyle,
			visited_ooxml_numberings: list[int],
			visited_ooxml_abstract_numberings: list[int]
		) -> Optional[Enumeration]:
		# TODO: maybe divide this function into several chunks, it is too long for sure-
		effective_enumeration: Optional[Enumeration] = None
		effective_abstract_enumeration: Optional[Enumeration] = None

		if ooxml_style_parent.abstract_numbering_parent is not None:
			if ooxml_style_parent.abstract_numbering_parent in visited_ooxml_abstract_numberings:
				raise ValueError("") # TODO
			visited_ooxml_abstract_numberings.append(ooxml_style_parent.abstract_numbering_parent.id)

			# If ooxml abstract numbering has already been discovered, use already computed effective enumeration
			effective_abstract_enumeration = self._discovered_effective_abstract_enumerations.get(
				ooxml_style_parent.abstract_numbering_parent.id, None
			)

			if effective_abstract_enumeration is None:
				self.compute_effective_enumeration(
					ooxml_numbering=None,  # Only interested in computing the abstract numbering
					ooxml_abstract_numbering=ooxml_style_parent.abstract_numbering_parent,
					visited_ooxml_numberings=visited_ooxml_numberings,
					visited_ooxml_abstract_numberings=visited_ooxml_abstract_numberings
				)

				effective_abstract_enumeration = self._discovered_effective_abstract_enumerations.get(
					ooxml_style_parent.abstract_numbering_parent.id, None
				)
				# The effective abstract numbering must have been discovered in the recursive step
				if effective_abstract_enumeration is None:
					raise ValueError("") # TODO

		if ooxml_style_parent.numbering is not None and ooxml_style_parent.numbering not in visited_ooxml_numberings:
			visited_ooxml_numberings.append(ooxml_style_parent.numbering.id)

			# If ooxml numbering has already been discovered, use already computed effective enumeration
			effective_enumeration = self.effective_enumerations.get(ooxml_style_parent.numbering.id, None)
			
			if effective_enumeration is None:
				self.compute_effective_enumeration(
					ooxml_numbering=ooxml_style_parent.numbering,
					ooxml_abstract_numbering=ooxml_style_parent.numbering.abstract_numbering,
					visited_ooxml_numberings=visited_ooxml_numberings,
					visited_ooxml_abstract_numberings=visited_ooxml_abstract_numberings
				)

				effective_enumeration = self.effective_enumerations.get(ooxml_style_parent.numbering.id, None)
				# The effective abstract enumeration must have been discovered in the recursive step
				if effective_abstract_enumeration is None:
					raise ValueError("") # TODO
			
		# Merge: (effective_abstract_enumerations) + (effective_enumerations) => merged_effective_enumeration_style
		merged_effective_enumeration_style: Optional[Enumeration] = self.merge_into_effective_enumeration_style(
			effective_enumeration=effective_enumeration, effective_abstract_enumeration=effective_abstract_enumeration
		)
		self._discovered_effective_enumeration_styles[merged_effective_enumeration_style.id] = merged_effective_enumeration_style

		return merged_effective_enumeration_style

	def compute_effective_enumeration(
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

		# If ooxml abstract numbering has already been discovered, use already computed effective enumeration
		agg_effective_abstract_enumeration: Optional[Enumeration] = self._discovered_effective_abstract_enumerations.get(
			ooxml_abstract_numbering.id, None
		)

		if agg_effective_abstract_enumeration is None:
			effective_enumeration_style: Optional[Enumeration] = None

			if (
				ooxml_abstract_numbering.associated_styles is not None 
				and ooxml_abstract_numbering.associated_styles.style_parent is not None
			):
				# If this condition is met, it means that there is at least another recursive step needed
				must_default = False

				# If ooxml numbering style has already been discovered, use already computed effective enumeration
				effective_enumeration_style: Optional[Enumeration] = self._discovered_effective_enumeration_styles.get(
					ooxml_abstract_numbering.associated_styles.style_parent.id, None
				)

				if effective_enumeration_style is None:
					effective_enumeration_style = self._compute_effective_enumeration_style(
						ooxml_style_parent=ooxml_abstract_numbering.associated_styles.style_parent,
						visited_ooxml_numberings=visited_ooxml_numberings,
						visited_ooxml_abstract_numberings=visited_ooxml_abstract_numberings
					)

			effective_abstract_enumeration: Enumeration = Enumeration(
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

			if effective_enumeration_style is not None:
				# Aggregate: (effective_enumeration_style) + effective_abstract_enumeration => agg_effective_abstract_enumeration
				agg_effective_abstract_enumeration: Enumeration = self.aggregate_effective_enumerations(
					agg_enumeration=effective_enumeration_style,
					add_enumeration=effective_abstract_enumeration
				)
			else:
				agg_effective_abstract_enumeration = effective_abstract_enumeration
			
			self._discovered_effective_abstract_enumerations[agg_effective_abstract_enumeration.id] = agg_effective_abstract_enumeration
		
		if ooxml_numbering is not None:
			effective_enumeration: Enumeration = Enumeration(
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

			# Aggregate: agg_effective_abstract_enumeration + effective_enumeration => agg_effective_enumeration
			agg_effective_enumeration: Enumeration = self.aggregate_effective_enumerations(
				agg_enumeration=agg_effective_abstract_enumeration,
				add_enumeration=effective_enumeration
			)

			self.effective_enumerations[agg_effective_enumeration.id] = agg_effective_enumeration

	def _compute_effective_enumerations(self) -> None:
		for ooxml_numbering in self.ooxml_numberings.numberings:
			# If ooxml numbering has already been discovered, skip
			effective_enumeration: Optional[Enumeration] = self.effective_enumerations.get(ooxml_numbering.id, None)
			if effective_enumeration is None:
				self.compute_effective_enumeration(
					ooxml_numbering=ooxml_numbering,
					ooxml_abstract_numbering=ooxml_numbering.abstract_numbering,
					visited_ooxml_numberings=[ooxml_numbering.id],
					visited_ooxml_abstract_numberings=[]
				)

	def _associate_effective_level_styles(self) -> None:
		"""_summary_
		"""
		# TODO: Optimize this loop so the inner effective styles loop is only done once
		for effective_enumeration in self.effective_enumerations.values():
			for effective_level in effective_enumeration.levels.values():
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
		self._compute_effective_enumerations()
		self._associate_effective_level_styles()

		for effective_enumeration in self.effective_enumerations.values():
			print(effective_enumeration)
			print()

		quit()