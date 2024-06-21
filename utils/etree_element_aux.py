from lxml import etree
from lxml.etree import _Element as etreeElement


def remove_nsmap(element: etreeElement) -> str:
    """

    :return:
    """
    return etree.QName(element).localname