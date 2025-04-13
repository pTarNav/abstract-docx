from __future__ import annotations
from typing import Optional
from enum import Enum

from colour import Color

from utils.pydantic import ArbitraryBaseModel

from ooxml_docx.ooxml import OoxmlElement
import ooxml_docx.structure.properties as OOXML_PROPERTIES


class Numbering(ArbitraryBaseModel):
	pass