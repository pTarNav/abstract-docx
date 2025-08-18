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
from abstract_docx.data_models.numberings import Level, Numbering, Enumeration, Index, LevelProperties, MarkerType, ImpliedIndex

from ooxml_docx.structure.document import OoxmlDocument
from utils.pydantic import ArbitraryBaseModel


class EffectiveDocumentFromOoxml(ArbitraryBaseModel):
	ooxml_document: OoxmlDocument
	effective_document: dict[int, Block]

	effective_styles_from_ooxml: EffectiveStylesFromOoxml
	effective_numberings_from_ooxml: EffectiveNumberingsFromOoxml

	_computed_numberings_index_ctr: dict[int, dict[int, Optional[int]]] = {}

	# Parameters
	# TODO: parameterize in the input of normalization()
	_allow_partial_implied_index_matches: bool = True

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

	def _associate_effective_block_indexes(self) -> None:
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

	def _resolve_index(self, effective_block: Block, prev_effective_block: Block) -> bool:
		# ! TODO: Maybe its stupid to have to check the level key all the time like this
		indentation_level: Optional[int] = next((ordered_level_id for ordered_level_id, level in effective_block.format.index.enumeration.levels.items() if level.id == effective_block.format.index.level.id), None)
		if indentation_level is None:
			raise ValueError("") # TODO
		
		if self._computed_numberings_index_ctr[effective_block.format.index.numbering.id][indentation_level] is None:
			self._computed_numberings_index_ctr[effective_block.format.index.numbering.id][indentation_level] = (
				self.effective_numberings_from_ooxml
				.effective_enumerations[effective_block.format.index.enumeration.id].levels[indentation_level].properties.start
			)
		else:
			if (
				prev_effective_block is not None and prev_effective_block.format.index is not None 
				and prev_effective_block.format.index.numbering != effective_block.format.index.numbering 
				and effective_block.format.index.level.properties.override_start != -1
			):  
				# Start override (change of numbering)
				self._computed_numberings_index_ctr[effective_block.format.index.numbering.id][indentation_level] = (
					self.effective_numberings_from_ooxml
					.effective_enumerations[effective_block.format.index.enumeration.id].levels[indentation_level].properties.start
				)
			else:
				self._computed_numberings_index_ctr[effective_block.format.index.numbering.id][indentation_level] += 1

		# Restart logic
		for level_id in range(
			indentation_level + 1, len(self._computed_numberings_index_ctr[effective_block.format.index.numbering.id].keys())
		):
			match (
				self.effective_numberings_from_ooxml
				.effective_enumerations[effective_block.format.index.enumeration.id].levels[level_id].properties.restart
			):
				case -1:
					self._computed_numberings_index_ctr[effective_block.format.index.numbering.id][level_id] = (
						self.effective_numberings_from_ooxml
						.effective_enumerations[effective_block.format.index.enumeration.id].levels[level_id].properties.start - 1
					)
				case 0:
					pass
				case _:
					# TODO implement this if better into the match case, also what happens if for some reason the restart happens when a new instance of a lower level happens
					if (
						self.effective_numberings_from_ooxml
						.effective_enumerations[effective_block.format.index.enumeration.id].levels[level_id].properties.restart 
						== effective_block.format.index.level.id + 1
					):
						self._computed_numberings_index_ctr[effective_block.format.index.numbering.id][level_id] = (
							self.effective_numberings_from_ooxml
							.effective_enumerations[effective_block.format.index.enumeration.id].levels[level_id].properties.start - 1
						)

		# Associate the index counter
		effective_block.format.index.index_ctr = {
			k: v for k, v in self._computed_numberings_index_ctr[effective_block.format.index.numbering.id].items()
			if v is not None and k <= indentation_level
		}

		return True

	def _resolve_indexes(self) -> None:
		# Initialize numberings index counters
		self._computed_numberings_index_ctr: dict[int, dict[int, Optional[int]]] = {}
		for numbering in self.effective_numberings_from_ooxml.effective_numberings.values():
			if len(numbering.enumerations) > 0:
				max_indentation_level: int = max([len(enumeration.levels.keys()) for enumeration in numbering.enumerations.values()])
				self._computed_numberings_index_ctr[numbering.id] = {i: None for i in range(max_indentation_level)}

		prev_effective_block: Optional[Block] = None
		for effective_block in self.effective_document.values():
			if effective_block.format.index is not None:
				self._resolve_index(effective_block=effective_block, prev_effective_block=prev_effective_block)
				prev_effective_block = effective_block

	@staticmethod
	def _n_implied_index_matches(matches: dict[str, dict[str, list[Level]]], only_full: bool = False) -> int:
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
			
	def _remove_implied_index_str_from_effective_paragraph(
			self, effective_paragraph: Paragraph, matched_enumerations: list[Enumeration], matched_levels: list[Level]
		) -> str:

		# Dummy partial index to detect the index string
		# It should not matter what index combination is used to extract the detected index
		dummy_enumeration: Enumeration = next(enumeration for enumeration in matched_enumerations)
		dummy_level: Level = next(level for level in matched_levels if level.id in [l.id for l in dummy_enumeration.levels.values()])
		
		# ! TODO: Maybe its stupid to have to check the level key all the time like this
		detected_level_key: int = next(level_key for level_key, level in dummy_enumeration.levels.items() if dummy_level.id == level.id)

		seen_runs: list[Run] = []
		for i, run in enumerate(effective_paragraph.content):
			seen_runs.append(run)
			partial_text: Run = Run(text="".join([t.text for t in seen_runs]), style=seen_runs[0].style)
			detected_index_str_match = re.match(dummy_enumeration.detection_regexes[detected_level_key], partial_text.text)
			if detected_index_str_match:
				partial_text.text = re.sub(
					dummy_enumeration.detection_regexes[detected_level_key], "", partial_text.text
				)
				effective_paragraph.content = [partial_text] + effective_paragraph.content[i+1:]

				return detected_index_str_match.group(0) # TODO: why group(0)?

	def _extract_level_key_index_str_from_implied_index_str(
			self, implied_index_str: str, matched_enumerations: list[Enumeration], matched_levels: list[Level]
		) -> str:

			# Dummy partial index to detect the level key index string
			# It should not matter what index combination is used to extract the detected index
			dummy_enumeration: Enumeration = next(enumeration for enumeration in matched_enumerations)
			dummy_level: Level = next(level for level in matched_levels if level.id in [l.id for l in dummy_enumeration.levels.values()])

			# ! TODO: Maybe its stupid to have to check the level key all the time like this
			detected_level_key: int = next(level_key for level_key, level in dummy_enumeration.levels.items() if dummy_level.id == level.id)

			# Extract the level key contents inside the detected index string
			regex_level_key_index_str: str = re.sub(
				r"\\\{" + rf"({detected_level_key})" +r"\\\}", r"(.*?)", re.escape(dummy_level.properties.marker_pattern)
			) # Turn the {detected_level_key} into a regex capture group
			detected_level_key_index_str_match = re.match(regex_level_key_index_str, implied_index_str)
			if detected_level_key_index_str_match is not None:
				return detected_level_key_index_str_match.group(1)
			else:
				raise ValueError("") # TODO


	def _implied_index_detection(self, effective_paragraph: Paragraph) -> Optional[list[ImpliedIndex]]:
		"""

		:param effective_paragraph_content: _description_
		:raises ValueError: _description_
		:return: _description_
		"""
		# Join all the text inside the paragraph content (keeping only the style of the first element).
		# This is to avoid false negatives in the level detection.
		full_text: Run = Run(
			text="".join([t.text for t in effective_paragraph.content]), style=effective_paragraph.content[0].style
		)

		matches: dict[str, dict[str, list[Level]]] = {}
		for effective_enumeration in self.effective_numberings_from_ooxml.effective_enumerations.values():
			effective_enumeration_matches: dict[str, list[Level]] = effective_enumeration.detect(run=full_text)
			if self._n_implied_index_matches(matches={effective_enumeration.id: effective_enumeration_matches}) != 0:
				matches[effective_enumeration.id] = effective_enumeration_matches
		
		n__matches: int = self._n_implied_index_matches(matches=matches)
		n_full_matches: int = self._n_implied_index_matches(matches=matches, only_full=True)
		n_partial_matches: int = n__matches - n_full_matches

		match (n_full_matches, n_partial_matches, self._allow_partial_implied_index_matches):
			case (0, _, False) | (0, 0, True):
				# Neither full nor partial (if allowed) implied index matches,
				# => No implied index
				return None
			case (0, 1, True):
				# No full implied index matches, with allowed single partial implied index match
				enumeration_id, enumeration_match = next(iter(matches.items()))
				matched_enumerations: list[Enumeration] = [
					self.effective_numberings_from_ooxml.effective_enumerations[enumeration_id]
				]
				matched_levels: list[Level] = enumeration_match["regex_only"]
			case (0, _, True):
				# No full implied index matches, with allowed multiple partial implied index matches
				unique_level_ids: set[str] = set()
				matched_enumerations: list[Enumeration]	= []
				for enumeration_id, enumeration_match in matches.items():
					unique_level_ids.update(level.id for level in enumeration_match["regex_only"])
					matched_enumerations.append(self.effective_numberings_from_ooxml.effective_enumerations[enumeration_id])

				matched_levels: list[Level] = [
					self.effective_numberings_from_ooxml.effective_levels[level_id] for level_id in list(unique_level_ids)
				]
			case (1, _, _):
				# Single full implied index match (which overrides any existing partial implied index matches)
				for enumeration_id, enumeration_match in matches.items():
					if len(enumeration_match["regex_and_style"]) == 1:  # Need to search for the single full implied index match
						matched_enumerations: list[Enumeration] = [
							self.effective_numberings_from_ooxml.effective_enumerations[enumeration_id]
						]
						matched_levels: list[Level] = enumeration_match["regex_and_style"]
			case (_, _, _):
				# Multiple full implied index matches (which overrides any existing partial implied index matches)
				unique_level_ids: set[str] = set()
				matched_enumerations: list[Enumeration]	= []
				for enumeration_id, enumeration_match in matches.items():
					unique_level_ids.update(level.id for level in enumeration_match["regex_and_style"])
					if len(enumeration_match["regex_and_style"]) != 0:
						matched_enumerations.append(self.effective_numberings_from_ooxml.effective_enumerations[enumeration_id])

				matched_levels: list[Level] = [
					self.effective_numberings_from_ooxml.effective_levels[level_id] for level_id in list(unique_level_ids)
				]
		
		# Instead of using the matched levels for the implied index matches create new instances of levels based on: 
		#  - The distinct marker types available
		#  - The detected index string style.
		# All other level properties can be ignored because they will not be used in the hierarchization step.

		distinct_marker_types: list[MarkerType] = list(set([level.properties.marker_type for level in matched_levels]))
		implied_index_matches_effective_levels: list[Level] = [
			Level(
				id=f"dummy-{marker_type}", # TODO: find some better naming mechanism
				properties=LevelProperties(marker_type=marker_type),
				style=effective_paragraph.content[0].style
			)
			for marker_type in distinct_marker_types
		]

		index_str: str = self._remove_implied_index_str_from_effective_paragraph(
			effective_paragraph=effective_paragraph, matched_enumerations=matched_enumerations, matched_levels=matched_levels
		)
		level_key_index_str: str = self._extract_level_key_index_str_from_implied_index_str(
			implied_index_str=index_str, matched_enumerations=matched_enumerations, matched_levels=matched_levels
		)

		return [
			ImpliedIndex(level=level, index_str=index_str, index_ctr=level.properties.marker_type.counter(s=level_key_index_str))
			for level in implied_index_matches_effective_levels
		]

	def _compute_effective_block_implied_indexes(self) -> None:
		implied_index_matches_table: dict[int, list[ImpliedIndex]] = {}
		
		for effective_block in self.effective_document.values():
			if isinstance(effective_block, Paragraph) and len(effective_block.content) > 0 and effective_block.format.index is None: # TODO: investigate why so many clauses
				# Do not try to find implied index matches for other block types.
				# Because with tables, it is much more difficult for a user to set the numbering manually			
				implied_index_matches: Optional[list[ImpliedIndex]] = self._implied_index_detection(
					effective_paragraph=effective_block
				)
				if implied_index_matches is not None:
					implied_index_matches_table[effective_block.id] = implied_index_matches
		
		for effective_block in self.effective_document.values():
			if effective_block.id in implied_index_matches_table.keys():
				implied_index_matches = implied_index_matches_table[effective_block.id]
				print(f"{effective_block.id=} => {implied_index_matches[0].index_str} [{len(implied_index_matches)}]")
				for iim in implied_index_matches:
					print("\t - ", iim.level.id, iim.level.properties.marker_pattern, iim.level.properties.marker_type, iim.index_str, iim.index_ctr)
					

	def load(self) -> None:
		self._compute_effective_blocks()
		
		self._associate_effective_block_styles()
		
		self._associate_effective_block_indexes()
		self._resolve_indexes()
		
		self._compute_effective_block_implied_indexes()

		