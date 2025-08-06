from __future__ import annotations
from typing import Optional
import os
from io import BytesIO
import zipfile

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlPackage
from ooxml_docx.relationships import OoxmlRelationships
from ooxml_docx.structure.styles import OoxmlStyles
from ooxml_docx.structure.numberings import OoxmlNumberings
from ooxml_docx.structure.document import OoxmlDocument

import logging
logger = logging.getLogger(__name__)


class OoxmlDocxStructure(ArbitraryBaseModel):
	styles: OoxmlStyles  # Parses ooxml information about styles
	numberings: OoxmlNumberings  # Parses ooxml information about numberings
	document: OoxmlDocument  # Parses ooxml information about the document content

	@classmethod
	def load(cls, docx: OoxmlDocx) -> OoxmlDocxStructure:

		logger.debug("Building OOXML styles part...")
		styles = OoxmlStyles.build(ooxml_styles_part=docx.ooxml.content["word"].content["styles.xml"])
		logger.debug("OOXML styles part built.")

		logger.debug("Building OOXML numberings part...")
		numberings = OoxmlNumberings.build(
			ooxml_numbering_part=docx.ooxml.content["word"].content["numbering.xml"], styles=styles
		)
		logger.debug("OOXML numberings part built.")
		
		logger.debug("Building OOXML document part...")
		document_relationships = OoxmlRelationships.parse(ooxml_rels=docx.ooxml.content["word"].relationships.content["document.xml.rels"].ooxml)
		document = OoxmlDocument.build(
			ooxml_document_part=docx.ooxml.content["word"].content["document.xml"], 
			styles=styles, numberings=numberings, relationships=document_relationships
		)
		logger.debug("OOXML document part built.")
		
		return cls(styles=styles, numberings=numberings, document=document)


class OoxmlDocx(ArbitraryBaseModel):
	"""
	Represents and processes the inner Office Open XML (OOXML) structure of a .docx file.
	"""
	file_path: str
	ooxml: OoxmlPackage

	structure: Optional[OoxmlDocxStructure] = None

	@classmethod
	def read(cls, file_path: str) -> OoxmlDocx:
		"""
		An .docx file can be essentially understood as a compressed folder with an specific file tree structure.
		In order to actually read the contents of the document, first convert the file into a .zip folder.
		This is actually done inside a memory buffer, so no need to actually save the actual compressed folder.
		Then the contents of the document are saved into memory by crawling the file tree structure.
		"""
		contents: dict[str, str] = {}
		with open(file_path, "rb") as f:
			# Read the .docx file as a .zip and crawl through the contents
			with zipfile.ZipFile(BytesIO(f.read())) as zip_ref:
				for f_name in zip_ref.namelist():
					# ! TODO: Handle other file extensions inside the package
					if f_name.endswith(".xml") or f_name.endswith(".rels"):
						contents[f_name] = zip_ref.read(f_name)
		logger.debug(f"{file_path} contents read.")

		logger.debug(f"Building .docx OOXML package structure...")
		ooxml_docx: OoxmlDocx = cls(
			file_path=file_path, ooxml=OoxmlPackage.load(name=os.path.splitext(file_path)[0], content=contents)
		)
		ooxml_docx.build()
		logger.info(f".docx OOXML package structure built.")

		return ooxml_docx
	
	def build(self) -> None:
		"""_summary_
		"""
		self.structure = OoxmlDocxStructure.load(docx=self)

	def __str__(self):
		s = f"\U0001F4D1 \033[36m\033[1m'{self.file_path}'\033[0m\n"
		s += f"{self.ooxml}"
		return s
