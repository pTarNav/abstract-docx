from __future__ import annotations
from typing import Optional
import copy

from utils.pydantic import ArbitraryBaseModel


class Style(ArbitraryBaseModel):
	id: str
	
	parent: Optional[Style] = None
	children: Optional[list[Style]] = None


class Numbering(ArbitraryBaseModel):
	idk: str


class Format(ArbitraryBaseModel):
	style: Style
	numbering: Numbering