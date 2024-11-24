from typing import Optional

from lxml import etree
from lxml.etree import _Element as etreeElement

from utils.visualization import bool_utf8_symbol

import logging
logger = logging.getLogger(__name__)


def etree_to_str(element: etreeElement) -> str:
    """
    Computes XML element string representation using LXML etree.tostring and decoding to utf-8.
    :param element: XML element.
    :return: XML element string representation.
    """
    etree.indent(tree=element, space="\t")
    return etree.tostring(element, pretty_print=True, encoding="utf-8").decode("utf-8") 


def print_etree(element: etreeElement) -> None:
    """
    Prints XML element using etree_to_str.
    :param element: XML element.
    """
    print(etree_to_str(element=element))


def local_name(element: etreeElement) -> str:
    """
    Removes namespace from the XML element.
    :param element: XML element.
    :return: Clean XML element name without the namespace prefix.
    """
    return etree.QName(element).localname


def element_skeleton(element: etreeElement) -> etreeElement:
    """
    Computes the element skeleton (node metadata without including the child nodes information) of an XML element.
    :param element: XML element.
    :return: XML element skeleton.
    """
    return etree.Element(element.tag, attrib=element.attrib)


def xpath_query(
        element: etreeElement, query: str, nullable: bool = True, singleton: bool = False,
    ) -> Optional[etreeElement | list[etreeElement]]:
    """
    Wrapper of the .xpath() class function of the lxml package to avoid having to specify the namespaces every time.
    Also handles the empty result cases, where instead of an empty list returns None.
    :param element: XML element to perform the xpath query on.
    :param query: Xpath query string.
    :param nullable: Boolean indicating whether the result can be None, defaults to True.
    :param singleton: Boolean indicating whether the result should only yield no results or one result, defaults to False.
    :return: Xpath query results, None when the result is empty.
    :raises ValueError: Raises error if singleton or nullable constraints are failed.
    """
    logger.debug(f"xpath_query: '{query}'")
    logger.debug(f"(nullable: {bool_utf8_symbol(nullable)}, singleton: {bool_utf8_symbol(singleton)})")
    logger.debug(f"element: '{element_skeleton(element=element)}'")

    query_result = element.xpath(query, namespaces=element.nsmap)
    
    if len(query_result) == 0:
        if not nullable:
            logger.error(f"! xpath nullable constraint error for query: {query}")
            raise ValueError(f"xpath nullable constraint error for query: {query}")
        logger.debug(f"=> []")
        return None
    
    if singleton:
        if len(query_result) != 1:
            logger.error(f"! xpath singleton constraint error for query: {query}\nresult: {query_result}")
            raise ValueError(f"xpath singleton constraint error for query: {query}\nresult: {query_result}")
        logger.debug(f"=> [{element_skeleton(query_result[0])}]")
        return query_result[0]
    
    logger.debug(f"=> [{", ".join([element_skeleton(r) for r in query_result])}]")
    return query_result
