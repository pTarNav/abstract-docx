from __future__ import annotations
from typing import Optional

from ooxml_docx.structure.styles import OoxmlStyles
import ooxml_docx.structure.styles as OOXML_STYLES

from utils.pydantic import ArbitraryBaseModel

from abstract_docx.views.format.styles import Style, StyleProperties


# TODO: Maybe create an abstract template for the effective styles class, so no matter the source it always contains the same methods

class EffectiveStylesFromOoxml(ArbitraryBaseModel):
	"""
	Auxiliary effective style class, not designed to structure data (same structure as Style),
	 but rather to house the necessary methods to compute the effective style properties.

	In the context of the project, effective means the result from the normalization of the source structure.
	"""
	ooxml_styles: OoxmlStyles
	effective_styles: dict[str, Style]
	map_ooxml_to_effective_merged_styles: dict[str, str] = {}
	map_effective_to_effective_deduplicated_styles: dict[str, str] = {}

	# Auxiliary data for intermediate steps
	_effective_paragraph_styles: dict[str, Style] = {}
	_effective_run_styles: dict[str, Style] = {}

	@staticmethod
	def load_effective_default_style(doc_defaults: OOXML_STYLES.DocDefaults) -> Style:
		return Style(
			id="__DocDefaults__",  # TODO: what happens if for some reason there already exists a style with this id?
			properties=StyleProperties.from_ooxml(
				run_properties=doc_defaults.default_run_properties,
				paragraph_properties=doc_defaults.default_paragraph_properties,
				must_default=True
			)
		)

	@classmethod
	def normalization(cls, ooxml_styles: OoxmlStyles) -> EffectiveStylesFromOoxml:
		effective_default_style: Style = cls.load_effective_default_style(doc_defaults=ooxml_styles.doc_defaults)
		effective_styles_from_ooxml: EffectiveStylesFromOoxml = cls(
			ooxml_styles=ooxml_styles, effective_styles={effective_default_style.id: effective_default_style}
		)
		effective_styles_from_ooxml.load()
		effective_styles_from_ooxml.deduplicate()

		return effective_styles_from_ooxml
	
	@staticmethod
	def aggregate_effective_style(agg_style: Style, add_style: Style, default_style: Style) -> Style:
		# Can assume that agg_style will never have empty style properties since it inherits from the default style at the root
		return Style(
			id=add_style.id,
			properties=StyleProperties.aggregate_ooxml(
				agg=agg_style.properties, add=add_style.properties, default=default_style.properties
			)
		)
	
	def compute_effective_style(self, ooxml_style: OOXML_STYLES.Style, agg_effective_style: Style) -> None:
		match type(ooxml_style):
			case OOXML_STYLES.RunStyle:
				other_shallow_effective_style_properties: StyleProperties = StyleProperties.from_ooxml(
					run_properties=ooxml_style.properties
				)
			case OOXML_STYLES.ParagraphStyle:
				other_shallow_effective_style_properties: StyleProperties = StyleProperties.from_ooxml(
					run_properties=ooxml_style.run_properties, paragraph_properties=ooxml_style.properties
				)
			case _:
				raise ValueError("") # TODO

		agg_effective_style: Style = self.aggregate_effective_style(
			agg_style=agg_effective_style,
			add_style=Style(id=ooxml_style.id, properties=other_shallow_effective_style_properties),
			default_style=self.effective_styles["__DocDefaults__"]
		)	

		match type(ooxml_style):
			case OOXML_STYLES.RunStyle:
				self._effective_run_styles[ooxml_style.id] = agg_effective_style
			case OOXML_STYLES.ParagraphStyle:
				self._effective_paragraph_styles[ooxml_style.id] = agg_effective_style
			case _:
				raise ValueError("") # TODO

		if ooxml_style.children is not None:
			for child in ooxml_style.children:
				self.compute_effective_style(ooxml_style=child, agg_effective_style=agg_effective_style)

	def _compute_effective_paragraph_and_run_styles(self) -> list[OOXML_STYLES.ParagraphStyle]:
		"""
		Compute effective styles top-down through the basedOn hierarchy.
		Only returns folded paragraph styles because folded run styles is not used further down the process.
		:return: _description_ 
		"""
		folded_run_styles: list[OOXML_STYLES.RunStyle] = []
		for ooxml_style in self.ooxml_styles.roots.run:
			self.compute_effective_style(ooxml_style=ooxml_style, agg_effective_style=self.effective_styles["__DocDefaults__"])
			folded_run_styles = ooxml_style.fold(agg=folded_run_styles)

		folded_paragraph_styles: list[OOXML_STYLES.ParagraphStyle] = []
		for ooxml_style in self.ooxml_styles.roots.paragraph:
			self.compute_effective_style(ooxml_style=ooxml_style, agg_effective_style=self.effective_styles["__DocDefaults__"])
			folded_paragraph_styles = ooxml_style.fold(agg=folded_paragraph_styles)

		return folded_paragraph_styles

	def _merge_linked_effective_paragraph_and_run_styles(
			self, folded_paragraph_styles: list[OOXML_STYLES.ParagraphStyle]
		) -> None:
		"""
		Merge linked effective paragraph and run styles into one effective style while compiling the effective paragraph styles.

		:param folded_paragraph_styles: _description_
		"""
		for effective_paragraph_style, ooxml_paragraph_style in zip(
			self._effective_paragraph_styles.values(), folded_paragraph_styles
		):
			if ooxml_paragraph_style.linked_run_style is not None:
				effective_run_style: Style = self._effective_run_styles[ooxml_paragraph_style.linked_run_style.id]
				
				# Essentially the run style run properties override the paragraph style run properties
				effective_merged_style_id: str = f"{effective_paragraph_style.id}+{effective_run_style.id}" # TODO: what happens if for some reason there already exists a style with this id?
				self.effective_styles[effective_merged_style_id] = Style(
					id=effective_merged_style_id, 
					properties=StyleProperties(
						run_style_properties=effective_run_style.properties.run_style_properties,
						paragraph_style_properties=effective_paragraph_style.properties.paragraph_style_properties
					)
				)
				self.map_ooxml_to_effective_merged_styles[effective_paragraph_style.id] = effective_merged_style_id
				self.map_ooxml_to_effective_merged_styles[effective_run_style.id] = effective_merged_style_id
			else:
				self.effective_styles[effective_paragraph_style.id] = effective_paragraph_style

	def _compile_remaining_effective_run_styles(self) -> None:
		"""
		Compile all the remaining effective run styles (without adding the run styles previously merged into effective styles).
		"""
		
		skips = list(self.map_ooxml_to_effective_merged_styles.keys())  # To not call the method every iteration of the loop
		for effective_run_style_id, effective_run_style in self._effective_run_styles.items():
			if effective_run_style_id not in skips:
				self.effective_styles[effective_run_style_id] = effective_run_style

	def load(self) -> None:
		"""
		"""
		folded_paragraph_styles: list[OOXML_STYLES.ParagraphStyle] = self._compute_effective_paragraph_and_run_styles()
		self._merge_linked_effective_paragraph_and_run_styles(folded_paragraph_styles=folded_paragraph_styles)
		self._compile_remaining_effective_run_styles()

	def deduplicate(self) -> None:
		groups: dict[str, Style] = {}
		_map_effective_to_effective_deduplicated_styles: dict[str, list[str]] = {}
		for style in self.effective_styles.values():
			duplicated_in_group: Optional[str] = None
			for group_id, grouped_style in groups.items():
				if style == grouped_style:	
					duplicated_in_group = group_id
			
			if duplicated_in_group is not None:
				new_group_id = f"{duplicated_in_group}&{style.id}" # TODO: what happens if for some reason there already exists a style with this id?
				
				groups[new_group_id] = groups.pop(duplicated_in_group)
				groups[new_group_id].id = new_group_id

				_map_effective_to_effective_deduplicated_styles[new_group_id] = (
					_map_effective_to_effective_deduplicated_styles.pop(duplicated_in_group)
				)
				_map_effective_to_effective_deduplicated_styles[new_group_id].append(style.id)
			else:
				groups[style.id] = style.model_copy()  # It should be treated as another instance of the style in memory
				_map_effective_to_effective_deduplicated_styles[style.id] = [style.id]

		self.effective_styles = groups
		
		for group_id, style_ids in _map_effective_to_effective_deduplicated_styles.items():
			for style_id in style_ids:
				self.map_effective_to_effective_deduplicated_styles[style_id] = group_id
	
	def get_mapped_id(self, ooxml_style_id: str) -> str:
		effective_merged_style_id: str = self.map_ooxml_to_effective_merged_styles.get(ooxml_style_id, ooxml_style_id)
		return self.map_effective_to_effective_deduplicated_styles.get(effective_merged_style_id, effective_merged_style_id)

	def get(self, ooxml_style_id: str) -> Optional[Style]:
		return self.effective_styles.get(self.get_mapped_id(ooxml_style_id=ooxml_style_id))

	def get_default(self) -> Style:
		return self.get(ooxml_style_id="__DocDefaults__")


					