from __future__ import annotations
from typing import Optional

import re
		

import ooxml_docx.document.paragraph as OOXML_PARAGRAPH
import ooxml_docx.document.table as OOXML_TABLE

from abstract_docx.normalization.styles import EffectiveStylesFromOoxml
from abstract_docx.normalization.numberings import EffectiveNumberingsFromOoxml

from abstract_docx.data_models.styles import Style, StyleProperties, RunStyleProperties, ParagraphStyleProperties
from abstract_docx.data_models.document import Paragraph, Run, Block, Hyperlink, Table, Row, Cell, PARAGRAPH_CONTENT

import ooxml_docx.document.run as OOXML_RUN
from abstract_docx.data_models.document import Format
from abstract_docx.data_models.numberings import Level, Numbering, Enumeration, Index

from ooxml_docx.structure.document import OoxmlDocument
from utils.pydantic import ArbitraryBaseModel


class ImplicitIndexMatches(ArbitraryBaseModel):
	numberings: list[Numbering]
	enumerations: list[Enumeration]
	levels: list[Level]

	detected_index_str: str

	_index_combinations: Optional[list[tuple[Numbering, Enumeration, Level]]] = None

	@property
	def index_combinations(self):
		if self._index_combinations is None:
			self._index_combinations = []
			for numbering in self.numberings:
				for enumeration in self.enumerations:
					if enumeration.id in numbering.enumerations.keys():
						possible_level_ids: list[str] = [l.id for l in enumeration.levels.values()]
						for level in self.levels:
							if level.id in possible_level_ids:
								self._index_combinations.append((numbering, enumeration, level))

		return self._index_combinations


class EffectiveDocumentFromOoxml(ArbitraryBaseModel):
	ooxml_document: OoxmlDocument
	effective_document: dict[int, Block]

	effective_styles_from_ooxml: EffectiveStylesFromOoxml
	effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml

	implicit_index_matches: dict[int, ImplicitIndexMatches] = {}

	# TODO: parameterize in the input of normalization()
	_allow_partial_implicit_index_matches: bool = True

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
			self,
			ooxml_texts: list[OOXML_RUN.Run | OOXML_PARAGRAPH.Hyperlink],
			effective_paragraph_style: Style,
			block_id: int
		) -> list[PARAGRAPH_CONTENT]:

		effective_texts: list[PARAGRAPH_CONTENT] = []
		for ooxml_text in ooxml_texts:
			# Use length of seen content since it may not match the original length due to normalization
			text_id = len(effective_texts)
			
			curr_text: Optional[PARAGRAPH_CONTENT] = None
			if isinstance(ooxml_text, OOXML_RUN.Run):
				run_id_str: str = f"__@PARAGRAPH={block_id}@RUN={text_id}__"
				curr_text: Run = self.compute_effective_run(
					ooxml_run=ooxml_text, effective_paragraph_style=effective_paragraph_style, run_id_str=run_id_str
				)
					
			elif isinstance(ooxml_text, OOXML_PARAGRAPH.Hyperlink):				
				hyperlink_content: list[Run] = []
				for i, ooxml_run in enumerate(ooxml_text.content):
					hyperlink_content.append(
						self.compute_effective_run(
							ooxml_run=ooxml_run,
							effective_paragraph_style=effective_paragraph_style,
							run_id_str=f"__@PARAGRAPH={block_id}@HYPERLINK={text_id}@RUN={i}__"
						)
					)

				curr_text: Hyperlink = Hyperlink(
					content=hyperlink_content, target=ooxml_text.target, style=effective_paragraph_style # TODO: Actually compute hyperlink style
				)

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

	def compute_effective_paragraph(self, ooxml_paragraph: OOXML_PARAGRAPH.Paragraph, block_id: int) -> Paragraph:
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
							run_properties=ooxml_paragraph.properties.run_properties,
							paragraph_properties=ooxml_paragraph.properties
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

		effective_paragraph_content: list[PARAGRAPH_CONTENT] = self._compute_effective_texts(
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
		
		return Paragraph(
			id=block_id,
			content=effective_paragraph_content,
			format=Format(style=effective_paragraph_style)
		)

	def _compute_effective_cells(
			self, ooxml_cells: list[OOXML_TABLE.TableCell], effective_row_style: Style, block_id: int
		) -> list[Cell]:
		
		# ! TODO: take into account styles

		effective_cells: list[Cell] = []

		for ooxml_cell in ooxml_cells:
			effective_cell_content: list[Block] = []
			for ooxml_block in ooxml_cell.content:
				match type(ooxml_block):
					case OOXML_PARAGRAPH.Paragraph:
						effective_cell_content.append(self.compute_effective_paragraph(ooxml_paragraph=ooxml_block, block_id=block_id))
					case OOXML_TABLE.Table:
						effective_cell_content.append(self.compute_effective_table(ooxml_table=ooxml_block, block_id=block_id))
					case _:
						# ! TODO: Remove continue
						continue
						raise ValueError(f"Unexpected ooxml block: {type(ooxml_block)}>")

			effective_cells.append(Cell(loc=ooxml_cell.loc, blocks=effective_cell_content))

		return effective_cells

	def _compute_effective_rows(
			self, ooxml_rows: list[OOXML_TABLE.TableRow], effective_table_style: Style, block_id: int
		) -> list[Row]:
		
		# ! TODO: take into account styles

		effective_rows: list[Row] = []

		for ooxml_row in ooxml_rows:
			effective_row_cells: list[Cell] = self._compute_effective_cells(
				ooxml_cells=ooxml_row.cells, 
				effective_row_style=effective_table_style,
				block_id=block_id
			)
			effective_rows.append(Row(loc=ooxml_row.loc, cells=effective_row_cells))

		return effective_rows
		
	
	def compute_effective_table(self, ooxml_table: OOXML_TABLE.Table, block_id: int) -> Table:

		# ! TODO: take into account table associated properties

		if ooxml_table.style is not None:
			effective_table_style: Style = self.effective_styles_from_ooxml.get(ooxml_style_id=ooxml_table.style.id)
		else:
			effective_table_style: Style = self.effective_styles_from_ooxml.get_default()

		effective_table_rows: list[Row] = self._compute_effective_rows(
			ooxml_rows=ooxml_table.rows, effective_table_style=effective_table_style, block_id=block_id
		)

		return Table(
			id=block_id,
			rows=effective_table_rows,
			format=Format(style=effective_table_style)
		)

	def _compute_effective_blocks(self) -> None:
		"""
		Iterate through the blocks of the document, routing each block according to the type of block
		"""
		for block_id, ooxml_block in enumerate(self.ooxml_document.body):
			match type(ooxml_block):
				case OOXML_PARAGRAPH.Paragraph:
					self.effective_document[block_id] = self.compute_effective_paragraph(ooxml_paragraph=ooxml_block, block_id=block_id)
				case OOXML_TABLE.Table:
					self.effective_document[block_id] = self.compute_effective_table(ooxml_table=ooxml_block, block_id=block_id)
				case _:
					# ! TODO: Remove continue
					continue
					raise ValueError(f"Unexpected ooxml block: {type(ooxml_block)}>")

	def _associate_effective_text_styles(self, effective_texts: list[Run]) -> None:
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

	@staticmethod
	def _n_implicit_index_matches(matches: dict[str, dict[str, list[Level]]], only_full: bool = False) -> int:
		if not only_full:
			return len(set(
				level.id
				for enumeration_matches in matches.values()
				for detected_levels in enumeration_matches.values()
				for level in detected_levels
			))

		return len(set(
			level.id
			for enumeration_matches in matches.values()
			for level in enumeration_matches["regex_and_style"]
		))

	def _resolve_enumerations_associated_numberings(self, enumerations: list[Enumeration]) -> list[Numbering]:
		associated_numbering_ids: set[int] = set()
		for numbering_id, numbering in self.effective_numberings_from_ooxml.effective_numberings.items():
			if any(enumeration.id in set(numbering.enumerations.keys()) for enumeration in enumerations):
				associated_numbering_ids.add(numbering_id)

		# TODO: Raise error if end list has len() == 0
		return [
			self.effective_numberings_from_ooxml.effective_numberings[associated_numbering_id] 
			for associated_numbering_id in list(associated_numbering_ids)
		]
	
	def _detected_index_str_from_effective_paragraph(self) -> str:
		# ! TODO !!
		return ""

	def _implicit_index_detection(self, effective_paragraph_content: list[Run]) -> Optional[ImplicitIndexMatches]:
		"""
		When no explicit numbering is found

		:param effective_paragraph_content: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		# Join all the text inside the paragraph content (keeping only the style of the first element).
		# This is to avoid false negatives in the level detection.
		full_text: Run = Run(
			text="".join([t.text for t in effective_paragraph_content]), style=effective_paragraph_content[0].style
		)

		matches: dict[str, dict[str, list[Level]]] = {}
		for effective_enumeration in self.effective_numberings_from_ooxml.effective_enumerations.values():
			effective_enumeration_matches: dict[str, list[Level]] = effective_enumeration.detect(run=full_text)
			if self._n_implicit_index_matches(matches={effective_enumeration.id: effective_enumeration_matches}) != 0:
				matches[effective_enumeration.id] = effective_enumeration_matches
		
		n__matches: int = self._n_implicit_index_matches(matches=matches)
		n_full_matches: int = self._n_implicit_index_matches(matches=matches, only_full=True)
		n_partial_matches: int = n__matches - n_full_matches

		match (n_full_matches, n_partial_matches, self._allow_partial_implicit_index_matches):
			case (0, _, False) | (0, 0, True):
				# Neither full nor partial (if allowed) implicit index matches,
				# => No implicit index
				return None
			case (0, 1, True):
				# No full implicit index matches, with allowed single partial implicit index match
				enumeration_id, enumeration_match = next(iter(matches.items()))
				matched_enumerations: list[Enumeration] = [
					self.effective_numberings_from_ooxml.effective_enumerations[enumeration_id]
				]
				matched_levels: list[Level] = enumeration_match["regex_only"]
			case (0, _, True):
				# No full implicit index matches, with allowed multiple partial implicit index matches
				unique_level_ids: set[str] = set()
				matched_enumerations: list[Enumeration]	= []
				for enumeration_id, enumeration_match in matches.items():
					unique_level_ids.update(level.id for level in enumeration_match["regex_only"])
					matched_enumerations.append(self.effective_numberings_from_ooxml.effective_enumerations[enumeration_id])

				matched_levels: list[Level] = [
					self.effective_numberings_from_ooxml.effective_levels[level_id] for level_id in list(unique_level_ids)
				]
			case (1, _, _):
				# Single full implicit index match (which overrides any existing partial implicit index matches)
				for enumeration_id, enumeration_match in matches.items():
					if len(enumeration_match["regex_and_style"]) == 1:  # Need to search for the single full implicit index match
						matched_enumerations: list[Enumeration] = [
							self.effective_numberings_from_ooxml.effective_enumerations[enumeration_id]
						]
						matched_levels: list[Level] = enumeration_match["regex_and_style"]
			case (_, _, _):
				# Multiple full implicit index matches (which overrides any existing partial implicit index matches)
				unique_level_ids: set[str] = set()
				matched_enumerations: list[Enumeration]	= []
				for enumeration_id, enumeration_match in matches.items():
					unique_level_ids.update(level.id for level in enumeration_match["regex_and_style"])
					matched_enumerations.append(self.effective_numberings_from_ooxml.effective_enumerations[enumeration_id])

				matched_levels: list[Level] = [
					self.effective_numberings_from_ooxml.effective_levels[level_id] for level_id in list(unique_level_ids)
				]
		
		matched_numberings: list[Numbering] = self._resolve_enumerations_associated_numberings(enumerations=matched_enumerations)
		return ImplicitIndexMatches(
			numberings=matched_numberings,
			enumerations=matched_enumerations,
			levels=matched_levels,
			detected_index_str=self._detected_index_str_from_effective_paragraph() # TODO
		)

	def _remove_detected_index_str_from_effective_paragraph(self, effective_paragraph: Paragraph, detected_index: Index) -> None:
		detected_level_key: int = next(level_key for level_key, level in detected_index.enumeration.levels.items() if detected_index.level.id == level.id)

		seen_runs: list[Run] = []
		for i, run in enumerate(effective_paragraph.content):
			seen_runs.append(run)
			partial_text: Run = Run(text="".join([t.text for t in seen_runs]), style=seen_runs[0].style)

			if re.match(detected_index.enumeration.detection_regexes[detected_level_key], partial_text.text):
				partial_text.text = re.sub(
					detected_index.enumeration.detection_regexes[detected_level_key], "", partial_text.text
				)
				effective_paragraph.content = [partial_text] + effective_paragraph.content[i+1:]
				break

	def _associate_effective_block_index(self) -> None:
		for effective_block in self.effective_document.values():
			# TODO: Add typehint for ooxml table
			ooxml_block: OOXML_PARAGRAPH.Paragraph = self.ooxml_document.body[effective_block.id]

			# TODO Look for any style - numbering association
			if ooxml_block.numbering is not None:
				# Case: Index associated through the block (or block style)
				effective_block_index: Index = self.effective_numberings_from_ooxml.get_index(
					ooxml_abstract_numbering_id=ooxml_block.numbering.abstract_numbering.id,
					ooxml_numbering_id=ooxml_block.numbering.id,
					ooxml_level_id=ooxml_block.indentation_level
				)

				effective_block.format.index = effective_block_index
			elif isinstance(effective_block, Paragraph):
				# Do not try to find implicit enumerations and levels matches for other block types
				# Because with tables, it is much more difficult for a user to set the numbering manually
				if len(effective_block.content) > 0: # TODO; why?				
					detected_implicit_index_matches: Optional[ImplicitIndexMatches] = self._implicit_index_detection(
						effective_paragraph_content=effective_block.content
					)

					if detected_implicit_index_matches is not None:
						if (
							len(detected_implicit_index_matches.numberings)
							== len(detected_implicit_index_matches.enumerations)
							== len(detected_implicit_index_matches.levels)
							== 1
						): # Certain implicit index match => Associate detected index
							detected_index: Index = Index(
								numbering=detected_implicit_index_matches.numberings[0],
								enumeration=detected_implicit_index_matches.enumerations[0],
								level=detected_implicit_index_matches.levels[0]
							)
							effective_block.format.index = detected_index
							self._remove_detected_index_str_from_effective_paragraph(effective_paragraph=effective_block, detected_index=detected_index)
							# TODO: need to somehow keep the removed index str from the paragraph to later perform assumption check
						else:
							self.implicit_index_matches[effective_block.id] = detected_implicit_index_matches
					
	def load(self) -> None:
		self._compute_effective_blocks()
		self._associate_effective_block_styles()
		self._associate_effective_block_index()

		# TODO: do this beautifully
		active_numberings = set()
		active_enumerations = set()

		for b in self.effective_document.values():
			if b.format.index is not None:
				active_numberings.add(b.format.index.numbering.id)
				active_enumerations.add(b.format.index.enumeration.id)

		for b in self.effective_document.values():
			b_iim = self.implicit_index_matches.get(b.id)
			if b_iim is not None :
				print("------ IMPLICIT INDEX MATCH ---------", f"{b.id=}", "\t", b.__str__()[:64])
				
				active_matches_numbering = list(set([n.id for n in b_iim.numberings]) & active_numberings)
				print("numberings\t", f"{len(b_iim.numberings)=}", " & ", f"{len(active_numberings)=}", " = ", f"{len(active_matches_numbering)=}")
				
				active_matches_enumeration = list(set([e.id for e in b_iim.enumerations]) & active_enumerations)				
				print("enumerations\t", f"{len(b_iim.enumerations)=}", " & ", f"{len(active_enumerations)=}", " = ", f"{len(active_matches_enumeration)=}")
				
				if len(active_enumerations) != 0:
					active_levels: set[str] = set([level.id for i in range(len(active_enumerations)) for level in self.effective_numberings_from_ooxml.effective_enumerations[list(active_enumerations)[i]].levels.values()])
					active_matches_levels = list(set([l.id for l in b_iim.levels]) & active_levels)
				else:
					active_levels = set()
					active_matches_levels = []
				print("levels\t", f"{len(b_iim.levels)=}", " & ", f"{len(active_levels)=}", " = ", f"{len(active_matches_levels)=}")
				print("index_combinations", f"{len(b_iim.index_combinations)=}")

				# if len(active_matches_numbering) == len(active_matches_enumeration) == 1:
				# 	print("!!!!!!!!")
				# 	print([level.id for level in self.effective_numberings_from_ooxml.effective_enumerations[active_matches_enumeration[0]].levels.values()])
				# 	print(active_matches_levels)
				# 	print("!!!!!!!!")

				# if len(active_matches_enumeration) == 0 and len(active_enumerations) == 1:
				# 	print("@@@@@@@@")
				# 	print([level.id for level in self.effective_numberings_from_ooxml.effective_enumerations[list(active_enumerations)[0]].levels.values()])
				# 	print([l.id for l in b_iim.levels])
				# 	print(set([level.id for level in self.effective_numberings_from_ooxml.effective_enumerations[list(active_enumerations)[0]].levels.values()]) & set([l.id for l in b_iim.levels]))
				# 	print("@@@@@@@@")

				# if len(active_matches_numbering) == len(active_matches_enumeration) == len(active_matches_levels) == 1:
				# 	detected_active_index_match = Index(
				# 		numbering=self.effective_numberings_from_ooxml.effective_numberings[active_matches_numbering[0]],
				# 		enumeration=self.effective_numberings_from_ooxml.effective_enumerations[active_matches_enumeration[0]],
				# 		level=self.effective_numberings_from_ooxml.effective_levels[active_matches_levels[0]]
				# 	)
				# 	b.format.index = detected_active_index_match
				# 	self._remove_detected_index_from_effective_paragraph(effective_paragraph=b, detected_index=detected_active_index_match)
