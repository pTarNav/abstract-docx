from __future__ import annotations
from typing import Optional
import ooxml_docx.document.paragraph as OOXML_PARAGRAPH

from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml
from abstract_docx.normalization.format.numberings import EffectiveNumberingsFromOoxml

from abstract_docx.views.format.styles import Style, StyleProperties, RunStyleProperties, ParagraphStyleProperties
from abstract_docx.views.document import Paragraph, Run, Block, Text, Hyperlink

import ooxml_docx.document.run as OOXML_RUN
from abstract_docx.views.format import Format
from abstract_docx.views.format.numberings import Level, Numbering, Enumeration, Index

from ooxml_docx.structure.document import OoxmlDocument
from utils.pydantic import ArbitraryBaseModel


# ! TODO: Rework this to only contain the possible levels, one should be able to trace back the possible numberings and enumerations through them
PossibleIndexMatches = dict[int, dict[str, dict[str, list[Level]]]]

class EffectiveDocumentFromOoxml(ArbitraryBaseModel):
	ooxml_document: OoxmlDocument
	effective_document: dict[int, Block]

	effective_styles_from_ooxml: EffectiveStylesFromOoxml
	effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml

	possible_levels_matches: dict[int, PossibleIndexMatches] = {}

	@classmethod
	def normalization(
		cls,
		ooxml_document: OoxmlDocument,
		effective_styles_from_ooxml: EffectiveStylesFromOoxml,
		effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml
	) -> EffectiveDocumentFromOoxml:
		effective_document_from_ooxml: EffectiveDocumentFromOoxml = cls(
			ooxml_document=ooxml_document,
			effective_document={},
			effective_styles_from_ooxml=effective_styles_from_ooxml,
			effective_numberings_from_ooxml=effective_numberings_from_ooxml
		)
		effective_document_from_ooxml.load()

		return effective_document_from_ooxml
	
	def compute_effective_run(self, ooxml_run: OOXML_RUN.Run, effective_paragraph_style: Style, run_id_str: str) -> Run:
		if ooxml_run.style is not None:
			effective_run_style: Style = Style(
				id=run_id_str,
				properties=StyleProperties.aggregate_ooxml(
					agg=effective_paragraph_style.properties,
					add=self.effective_styles_from_ooxml.get(ooxml_style_id=ooxml_run.style.id).properties,
					default=self.effective_styles_from_ooxml.get_default().properties
				)
			)
		else:
			effective_run_style: Style = effective_paragraph_style
		
		if ooxml_run.properties is not None:
			effective_run_style: Style = Style(
				id=run_id_str,
				properties=StyleProperties.aggregate_ooxml(
					agg=effective_run_style.properties,
					add=StyleProperties.from_ooxml(run_properties=ooxml_run.properties),
					default=self.effective_styles_from_ooxml.get_default().properties
				)
			)

		return Run.from_ooxml(ooxml_run=ooxml_run, style=effective_run_style)

	def _compute_effective_texts(
			self, ooxml_texts: list[OOXML_RUN.Run | OOXML_PARAGRAPH.Hyperlink], effective_paragraph_style: Style, block_id: int
		) -> list[Text]:

		effective_texts: list[Text] = []
		for ooxml_text in ooxml_texts:
			# Use length of seen content since it may not match the original length due to normalization
			text_id = len(effective_texts)
			
			curr_text: Optional[Text] = None
			if isinstance(ooxml_text, OOXML_RUN.Run):
				run_id_str = f"__@PARAGRAPH={block_id}@RUN={text_id}__"
				curr_text: Run = self.compute_effective_run(
					ooxml_run=ooxml_text, effective_paragraph_style=effective_paragraph_style, run_id_str=run_id_str
				)
					
			elif isinstance(ooxml_text, OOXML_PARAGRAPH.Hyperlink):
				print("Hyperlink")

			if curr_text is not None:
				# Concatenate with previous text if possible
				if (
					len(effective_texts) > 0 and isinstance(effective_texts[-1], type(curr_text))
					and effective_texts[-1].style == curr_text.style
				):
					effective_texts[-1].concat(other=curr_text)
				else:
					effective_texts.append(curr_text)
		
		return effective_texts
	
	def _n_matches(self, matches: PossibleIndexMatches) -> int:
		return len(set(
			level
			for enumeration_matches in matches.values()
			for detection_dict in enumeration_matches.values()
			for detected_levels in detection_dict()
			for level in detected_levels
		))

	def _possible_levels_detection(self, effective_paragraph_content: list[Text]) -> PossibleIndexMatches:
		# Join all the text inside the paragraph content (keeping only the style of the first element).
		# This is to avoid false negatives in the level detection.
		full_text: Text = Text(text="".join([t.text for t in effective_paragraph_content]), style=effective_paragraph_content[0].style)

		enumeration_matches: dict[str, dict[str, list[Level]]] = {}	
		for effective_enumeration in self.effective_numberings_from_ooxml.effective_enumerations.values():
			effective_enumeration_matches: dict[str, list[Level]] = effective_enumeration.detect(text=full_text)
			if sum([len(v) for v in effective_enumeration_matches.values()]) > 0:  # Not empty
				enumeration_matches[effective_enumeration.id] = effective_enumeration_matches

		matches: PossibleIndexMatches = {}
		for effective_numbering in self.effective_numberings_from_ooxml.effective_numberings.values():
			for effective_enumeration_id, possible_level_matches in enumeration_matches.items():
				if effective_enumeration_id in effective_numbering.enumerations.keys():
					matches[effective_numbering.id][effective_enumeration_id] = possible_level_matches
		
		return matches

	def compute_effective_paragraph(self, ooxml_paragraph: OOXML_PARAGRAPH.Paragraph, block_id: int) -> None:
		if ooxml_paragraph.properties is not None:
			effective_paragraph_style: Style = Style(
				id=f"__@PARAGRAPH={block_id}__",
				properties=StyleProperties.aggregate_ooxml(
					agg=(
						self.effective_styles_from_ooxml.get(ooxml_style_id=ooxml_paragraph.style.id).properties
						if ooxml_paragraph.style is not None else self.effective_styles_from_ooxml.get_default().properties
					),
					add=(
						StyleProperties.from_ooxml(
							run_properties=ooxml_paragraph.properties.run_properties, paragraph_properties=ooxml_paragraph.properties
						)
					),
					default=self.effective_styles_from_ooxml.get_default().properties
				)
			)
			
		else:
			if ooxml_paragraph.style is not None:
				effective_paragraph_style: Style = self.effective_styles_from_ooxml.get(ooxml_style_id=ooxml_paragraph.style.id)
			else:
				effective_paragraph_style: Style = self.effective_styles_from_ooxml.get_default()

		effective_paragraph_content: list[Text] = self._compute_effective_texts(
			ooxml_texts=ooxml_paragraph.content, effective_paragraph_style=effective_paragraph_style, block_id=block_id
		)

		# TODO: put this logic inside the style properties interface
		# TODO: this should include the majority not all !!!!
		# Check if there are run style properties shared amongst all the paragraph contents.
		# If so pull them into the paragraph style.
		if len(effective_paragraph_content) > 0:
			shared_text_run_style_properties: RunStyleProperties = effective_paragraph_content[0].style.properties.run_style_properties

			for i, effective_text in enumerate(effective_paragraph_content[1:]):
				if len(effective_text.text.strip()) > 0:

					shared_text_run_style_properties = RunStyleProperties(
						font_size=shared_text_run_style_properties.font_size
						if shared_text_run_style_properties.font_size == effective_text.style.properties.run_style_properties.font_size
						else None,
						font_color=shared_text_run_style_properties.font_color
						if shared_text_run_style_properties.font_color == effective_text.style.properties.run_style_properties.font_color
						else None,
						font_script=shared_text_run_style_properties.font_script
						if shared_text_run_style_properties.font_script == effective_text.style.properties.run_style_properties.font_script
						else None,
						bold=shared_text_run_style_properties.bold
						if shared_text_run_style_properties.bold == effective_text.style.properties.run_style_properties.bold
						else None,
						italic=shared_text_run_style_properties.italic
						if shared_text_run_style_properties.italic == effective_text.style.properties.run_style_properties.italic
						else None,
						underline=shared_text_run_style_properties.underline
						if shared_text_run_style_properties.underline == effective_text.style.properties.run_style_properties.underline
						else None
					)

			if shared_text_run_style_properties != effective_paragraph_style.properties.run_style_properties:
				effective_paragraph_style.properties.run_style_properties.patch(other=shared_text_run_style_properties)

		# TODO: Check if there is whitespace in front of the paragraph contents
		# Cases:
		#  - Paragraph occupies just 1 line: The whitespace is pulled into the start indentation.
		#  - Paragraph occupies more than just 1 line:
		#  		- Whitespace detected only at the beginning: The whitespace is pulled into the first indentation.
		#  		- Whitespace detected repeatedly for each line: The whitespace is pulled into the start indentation.

		# TODO Look for any style - numbering association

		effective_paragraph_index: Optional[Index] = None
		if len(effective_paragraph_content) > 0:
			# Case: Index associated through the block (or block style)
			if ooxml_paragraph.numbering is not None:
				effective_paragraph_index: Index = self.effective_numberings_from_ooxml.get_index(
					ooxml_abstract_numbering_id=ooxml_paragraph.numbering.abstract_numbering.id,
					ooxml_numbering_id=ooxml_paragraph.numbering.id,
					ooxml_level_id=ooxml_paragraph.indentation_level
				)
			else:
				# Possible outcomes and meanings:
				# - If no matches are detected then the paragraph is certain to not have any numbering associated.				
				# - If there is only 1 match detected it means that there is no uncertainty that it is associated.
				# - If there is more than 1 match, cannot do any decision with certainty.
				detected_matches: PossibleIndexMatches = self._possible_levels_detection(
					effective_paragraph_content=effective_paragraph_content,
				)
				
				match self._n_matches(matches=detected_matches):
					case 0:
						pass
					case 1:
						effective_numbering_id, effective_enumeration_id, detection_type, effective_level = next(
							(effective_numbering_id, effective_enumeration_id, detection_type, next(effective_levels_list))
							for effective_numbering_id, enumeration_detected_matches in detected_matches.items()
							for effective_enumeration_id, detection_dict in enumeration_detected_matches.items()
							for detection_type, effective_levels_list in detection_dict.items()
						)
						# TODO the prints would be nice to have in debug mode
						print(f"Unique index detected for block: {block_id} (with {detection_type} => numbering: {effective_numbering_id}, enumeration: {effective_enumeration_id}, level: {effective_level.id})")

						effective_paragraph_index: Index = Index(
							numbering=self.effective_numberings_from_ooxml.effective_numberings[effective_numbering_id],
							enumeration=self.effective_numberings_from_ooxml.effective_enumerations[effective_enumeration_id],
							level=effective_level
						)
					case _:
						self.possible_levels_matches[block_id] = detected_matches
		
		effective_paragraph: Paragraph = Paragraph(
			id=block_id,
			content=effective_paragraph_content,
			format=Format(style=effective_paragraph_style, index=effective_paragraph_index)
		)
		# print()
		# print(effective_paragraph)
		# print("possible numbering and level matches", possible_numbering_and_level_matches)

		self.effective_document[block_id] = effective_paragraph

	def _compute_effective_blocks(self) -> None:
		"""
		Iterate through the blocks of the document, routing each block according to the type of block
		"""
		for block_id, ooxml_block in enumerate(self.ooxml_document.body):
			match type(ooxml_block):
				case OOXML_PARAGRAPH.Paragraph:
					self.compute_effective_paragraph(ooxml_paragraph=ooxml_block, block_id=block_id)
				case _:
					# ! TODO: Remove continue
					continue
					raise ValueError(f"Unexpected ooxml block: {type(ooxml_block)}>")

	def _associate_effective_block_styles(self) -> None:
		"""_summary_
		"""
		for effective_block in self.effective_document.values():
			found_effective_style_match: bool = False
			for effective_style in self.effective_styles_from_ooxml.effective_styles.values():
				if effective_block.format.style == effective_style:
					effective_block.format.style = effective_style
					found_effective_style_match = True
					break
			
			if not found_effective_style_match:
				effective_block_style_id: str = effective_block.format.style.id
				self.effective_styles_from_ooxml.effective_styles[effective_block_style_id] = effective_block.format.style
			
			if isinstance(effective_block, Paragraph):
				self._associate_effective_text_styles(effective_texts=effective_block.content)

	def _associate_effective_text_styles(self, effective_texts: list[Text]) -> None:
		# TODO: Optimize this loop so the inner effective styles loop is only done once
		for effective_text in effective_texts:
			found_effective_style_match: bool = False
			for effective_style in self.effective_styles_from_ooxml.effective_styles.values():
				if effective_text.style == effective_style:
					effective_text.style = effective_style
					found_effective_style_match = True
					break
			
			if not found_effective_style_match:
				self.effective_styles_from_ooxml.effective_styles[effective_text.style.id] = effective_text.style

	def load(self) -> None:
		self._compute_effective_blocks()
		self._associate_effective_block_styles()
	