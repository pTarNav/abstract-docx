import copyreg
from lxml import etree


def _pickle_etree_element(elem: etree._Element):
	return (etree.fromstring, (etree.tostring(elem),))

def _pickle_etree_elementtree(tree: etree._ElementTree):
	return (etree.ElementTree, (etree.fromstring(etree.tostring(tree.getroot())),))

def register_picklers() -> None:
	copyreg.pickle(etree._Element, _pickle_etree_element)
	copyreg.pickle(etree._ElementTree, _pickle_etree_elementtree)