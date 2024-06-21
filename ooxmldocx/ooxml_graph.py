from lxml import etree
from lxml.etree import _Element as etreeElement

from ooxmldocx.ooxml_docx import OoxmlDocx, OoxmlPackage, OoxmlPart
from utils.etree_element_aux import remove_nsmap
from utils.html_server import HTMLServer


def tab(d: int) -> str:
	"""
	Auxiliary template for html indentation for elements inside the body, always adding +2 to the depth to
	compensate for initial html and body tags indentation.
	:param d: Depth of the indentation.
	:return: Indentation string.
	"""
	return "\t"*(d+2)


class OoxmlGraph:
	html_main_template: str = lambda _, file, styles, graph: \
		(
			f"<!DOCTYPE html>\n"
			f"<html>\n"
			f"\t<head>\n\t\t<title>{file}</title>\n\t\t<style>{styles}</style>\n\t</head>\n"
			f"\t<body>\n{graph}\n\t</body>\n"
			f"</html>"
		)

	html_ooxml_element_template: str = lambda _, depth, tag, text, attributes, children: \
		(
			f"{tab(d=2*depth)}<div class='ooxml_element_node'>\n"
			f"{tab(d=2*depth+1)}<div class='ooxml_element_node_top'>\n"
			f"{tab(d=2*depth+2)}<div class='ooxml_element_tag'><b>&lt{tag}&gt</b></div>\n"
			f"{
				f'{tab(d=2*depth+2)}<div class={chr(39)}ooxml_element_attributes{chr(39)}>{chr(10)}' 
				if len(attributes) != 0 else ''
			}"
			f"{chr(10).join([
				f'{tab(d=2*depth+3)}<div class={chr(39)}ooxml_element_attribute{chr(39)}><b>{attr_key}</b>: '
				f'{chr(39)}{attr_val}{chr(39)}</div>' 
				for attr_key, attr_val in attributes.items()
			])}"
			f"{f'{chr(10)}{tab(d=2*depth+2)}</div>{chr(10)}' if len(attributes) != 0 else ''}"
			f"{tab(d=2*depth+1)}</div>\n"
			f"{
				f'<div class={chr(39)}ooxml_element_text{chr(39)}><i>{text}</i></div>{chr(10)}'
				if text is not None else ''
			}"
			# Children template (not included if leaf node)
			f"{
				f'{tab(d=2*depth+1)}<div class={chr(39)}ooxml_element_children{chr(39)}>{chr(10)}'
				if len(children) != 0 else ''
			}"
			f"{chr(10).join([child for child in children]) if len(children) != 0 else ''}"
			f"{f'{chr(10)}{tab(d=2*depth+1)}</div>{chr(10)}' if len(children) != 0 else ''}"
			f"{
				f'{tab(d=2*depth+1)}<div class={chr(39)}ooxml_element_node_bottom{chr(39)}></div>{chr(10)}'
				if len(children) != 0 else ''
			}"
			f"{tab(d=2*depth)}</div>"
		)

	__DEBUG = False
	styles = (
		f"{'div { border: 1px solid red; }' if __DEBUG else ''}\n"
		f"html {{ background-color: black; color: white; }}"
		f".ooxml_element_node {{ margin-left: 2rem; border-left: 1px solid LightBlue; padding-left: 0.5rem; }}\n"
		f".ooxml_element_node_top {{ display: flex; flex-direction: row; gap: 1rem; }}"
		f".ooxml_element_node_bottom {{ height: 0.5rem; }}"
		f".ooxml_element_tag {{ font-size: 1rem; color: #4287f5; }}"
		f".ooxml_element_attributes {{ display: flex; flex-direction: row; gap: 0.5rem; }}"
		f".ooxml_element_text {{ color: LightBlue; }}"
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
			file=self.ooxml_structure.name,
			styles=self.styles,
			graph=self._build_ooxml_element(element=self.ooxml_structure.element)
		)

	def _build_ooxml_element(self, element: etreeElement, depth: int = 0) -> str:
		"""

		:param element:
		:param depth:
		:return:
		"""

		return self.html_ooxml_element_template(
			depth=depth,
			tag=remove_nsmap(element.tag),
			text=element.text,
			attributes={remove_nsmap(attr_key): attr_val for attr_key, attr_val in element.attrib.items()},
			children=[self._build_ooxml_element(element=child, depth=depth+1) for child in element]
		)

	def open_graph(self, port: int = 8000) -> None:
		"""

		"""

		html_server = HTMLServer(html=self.html_output, port=port)
		html_server.serve_html()
