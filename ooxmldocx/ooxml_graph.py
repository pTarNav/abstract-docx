from lxml.etree import _Element as etreeElement

from ooxmldocx.ooxml_docx import OoxmlDocx, OoxmlPackage, OoxmlPart


def tab(d: int) -> str:
	"""
	Auxiliary template for html indentation for elements inside the body.
	:param d: Depth of the indentation.
	:return:
	"""
	return "\t"*(d+2)


class OoxmlGraph:
	html_main_template: str = lambda _, file, styles, graph: \
		(
			f"<!DOCTYPE html>\n"
			f"<html>\n"
			f"\t<head>\n\t\t<title>{file}</title>\n\t\t<style>{styles}</style>\n\t</head>"
			f"\t<body>\n{graph}\n\t</body>\n"
			f"</html>"
		)

	html_ooxml_element_template: str = lambda _, depth, tag, children: \
		(
			f"{tab(d=depth)}<div class='ooxml_element_node'>\n"
			f"{tab(d=depth+1)}<div class='ooxml_element_tag'>{tag}</div>\n"
			# Children template (not included if leaf node)
			f"{f'{tab(d=depth+1)}<div class={chr(39)}ooxml_element_children{chr(39)}{chr(10)}>' if len(children) != 0 else ''}"
			f"{chr(10).join([child for child in children]) if len(children) != 0 else ''}"
			f"{f'{chr(10)}{tab(d=depth+1)}</div>{chr(10)}' if len(children) != 0 else ''}"
			f"{tab(d=depth)}</div>"
		)

	def __init__(self, ooxml_structure: OoxmlDocx | OoxmlPackage | OoxmlPart):
		"""

		:param ooxml_structure:
		"""

		self.ooxml_structure = ooxml_structure
		self.html_output: str

		if isinstance(self.ooxml_structure, OoxmlDocx):
			self._build_ooxml_graph_from_ooxml_docx()
		elif isinstance(self.ooxml_structure, OoxmlPackage):
			self._build_ooxml_graph_from_ooxml_package()
		elif isinstance(self.ooxml_structure, OoxmlPart):
			self._build_ooxml_graph_from_ooxml_part()
			print(self.html_output)
		else:
			raise ValueError(f"{type(ooxml_structure)} must be either 'OoxmlDocx', 'OoxmlPackage' or 'OoxmlPart'.")

	def _build_ooxml_graph_from_ooxml_docx(self):
		raise NotImplementedError

	def _build_ooxml_graph_from_ooxml_package(self):
		raise NotImplementedError

	def _build_ooxml_graph_from_ooxml_part(self):
		"""

		:return:
		"""

		self.html_output = self.html_main_template(
			file="x", styles="x", graph=self._build_ooxml_element(element=self.ooxml_structure.element)
		)

	def _build_ooxml_element(self, element: etreeElement, depth: int = 0) -> str:
		"""

		:param element:
		:param depth:
		:return:
		"""

		return self.html_ooxml_element_template(
			depth=depth,
			tag=element.tag,
			children=[self._build_ooxml_element(element=child, depth=depth+2) for child in element]
		)
