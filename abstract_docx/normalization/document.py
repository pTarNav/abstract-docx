from __future__ import annotations
from typing import Optional
import ooxml_docx.document.paragraph as OOXML_PARAGRAPH

from abstract_docx.normalization.format.styles import EffectiveStylesFromOoxml
from abstract_docx.normalization.format.numberings import EffectiveNumberingsFromOoxml

from abstract_docx.views.format.styles import Style, StyleProperties
from abstract_docx.views.document import Paragraph, Run, Block, Text, Hyperlink

import ooxml_docx.document.run as OOXML_RUN
from abstract_docx.views.format import Format
from abstract_docx.views.format.numberings import Level, Numbering

from ooxml_docx.structure.document import OoxmlDocument
from utils.pydantic import ArbitraryBaseModel


class EffectiveDocumentFromOoxml(ArbitraryBaseModel):
	ooxml_document: OoxmlDocument
	effective_document: dict[int, Block]

	effective_styles_from_ooxml: EffectiveStylesFromOoxml
	effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml

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
	
	def possible_numberings_and_levels_detection(
			self, effective_paragraph_content: list[Text], effective_numberings: dict[int, Numbering]
		) -> Optional[dict[int, dict[str, list[Level]]] | tuple[int, Level]]:
		# Join all the text inside the paragraph content (keeping only the style of the first element).
		# This is to avoid false negatives in the level detection.
		x: Text = Text(text="".join([t.text for t in effective_paragraph_content]), style=effective_paragraph_content[0].style)

		matches: dict[int, dict[str, list[Level]]] = {}
		for effective_numbering in effective_numberings.values():
			effective_numbering_matches: dict[str, list[Level]] = effective_numbering.detect(text=x)
			if sum([len(v) for v in effective_numbering_matches.values()]) > 0:  # Not empty
				matches[effective_numbering.id] = effective_numbering_matches
		
		# No matches detected
		if sum([sum([len(v2) for v2 in v1.values()]) for v1 in matches.values()]) == 0:
			return None
		# One match detected
		if sum([sum([len(v2) for v2 in v1.values()]) for v1 in matches.values()]) == 1:
			return None # TODO return match
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

		# TODO Look for any style - numbering association
		
		effective_numbering: Optional[Numbering] = None
		effective_level: Optional[Level] = None
		possible_numbering_and_level_matches: Optional[dict[int, dict[str, list[Level]]] | tuple[int, Level]] = None
		if len(effective_paragraph_content) > 0:
			if ooxml_paragraph.numbering is not None:
				print("BY NUMBERING")
				print(ooxml_paragraph.numbering.id, ooxml_paragraph.indentation_level)
				effective_numbering: Numbering = self.effective_numberings_from_ooxml.effective_numberings[
					ooxml_paragraph.numbering.id
				]
				if ooxml_paragraph.indentation_level not in effective_numbering.levels.keys():
					raise ValueError("") # TODO
				effective_level: Level = effective_numbering.levels[ooxml_paragraph.indentation_level]
			# elif ooxml_paragraph.style is not None and ooxml_paragraph.style.numbering is not None:
				# TODO: Think about how the numbering - style association should be treated after normalization
				# TODO: For now just ignore, because the paragraph will always contain the numbering if it does through style anyway (this might change)
				# print("BY STYLE NUMBERING")
				# print(ooxml_paragraph.style.numbering.id)
				# print(ooxml_paragraph.numbering, ooxml_paragraph.indentation_level)
				
				# effective_numbering: Numbering = self.effective_numberings_from_ooxml.effective_numberings[
				# 	ooxml_paragraph.style.numbering.id
				# ]
				# if ooxml_paragraph.style.indentation_level not in effective_numbering.levels.keys():
				# 	raise ValueError("") # TODO
				# effective_level: Level = effective_numbering.levels[ooxml_paragraph.indentation_level]
			else:
				print("BY NUMBERING DETECTION")
				matches: Optional[dict[int, dict[str, list[Level]]] | tuple[int, Level]] = self.possible_numberings_and_levels_detection(
					effective_paragraph_content=effective_paragraph_content,
					effective_numberings=self.effective_numberings_from_ooxml.effective_numberings
				)
				
				# Possible outcomes and meanings:
				# - If no matches are detected then the paragraph is certain to not have any numbering associated.				
				# - If there is only 1 match detected it means that there is no uncertainty that it is associated.
				# - If there is more than 1 match, cannot do any decision with certainty.
				if matches is not None:
					if isinstance(matches, tuple):
						effective_numbering: Numbering = self.effective_numberings_from_ooxml.effective_numberings[matches[0]]
						effective_level: Level = matches[1]
					else:
						possible_numbering_and_level_matches = matches

		effective_paragraph: Paragraph = Paragraph(
			id=block_id,
			content=effective_paragraph_content,
			format=Format(style=effective_paragraph_style, numbering=effective_numbering, level=effective_level)
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
					self._associate_effective_text_styles
				case _:
					continue
					raise ValueError("")  # TODO

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
		
	