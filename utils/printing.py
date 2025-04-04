from lxml import etree
from lxml.etree import _Element as etreeElement


def etree_to_str(element: etreeElement) -> str:
	"""
	Computes XML element string representation using LXML etree.tostring and decoding to utf-8.
	:return: XML element string representation.
	"""

	# TODO: Add boolean with default False to indicate wether to include global namespaces declarations
	etree.indent(tree=element, space="\t")
	return etree.tostring(element, pretty_print=True, encoding="utf-8").decode("utf-8")


from rich.console import Console
from rich.tree import Tree


def rich_tree_to_str(tree: Tree) -> str:
	console = Console()
	with console.capture() as capture:
		console.print(tree)
	return capture.get()
