from typing import Optional

# LXML
from lxml import etree
from lxml.etree import _Element as etreeElement


def print_etree(element: etreeElement) -> None:
    """
    Prints XML element using LXML etree.tostring and decoding to utf-8
    :param element: XML element.
    """
    etree.indent(tree=element, space="\t")
    print(etree.tostring(element, pretty_print=True, encoding="utf-8").decode("utf-8"))


def local_name(element: etreeElement) -> str:
    """
    Removes namespace from the XML element.
    :param element: XML element.
    :return: Clean XML element name without the namespace prefix.
    """
    return etree.QName(element).localname

def element_skeleton(element: etreeElement) -> etreeElement:
    """_summary_

    :param element: _description_
    :return: _description_
    """
    return etree.Element(element.tag, attrib=element.attrib)

def xpath_query(element: etreeElement, query: str, singleton: bool = False, nullable=True) -> Optional[etreeElement | list[etreeElement]]:
    """
    Wrapper of the .xpath() class function of the lxml package to avoid having to specify
    the namespaces every time.
    Also handles the empty result cases, where instead of an empty list returns None.
    :param element: XML element to perform the xpath query on.
    :param query: Xpath query string.
    :param singleton: Boolean indicating whether the result should only yield
    no results or one result, defaults to False.
    :param nullable: Boolean indicating whether the result can be None, defaults to True.
    :return: Xpath query results, None when the result is empty.
    :raises ValueError: Raises error if singleton or nullable constraints are failed.
    """

    query_result = element.xpath(query, namespaces=element.nsmap)
    if len(query_result) == 0:
        if not nullable:
            raise ValueError(f"xpath nullable constraint error for query: {query}")
        return None
    
    #
    if singleton:
        if len(query_result) != 1:
            raise ValueError(f"xpath singleton constraint error for query: {query}\nresult: {query_result}")
        return query_result[0]
    
    return query_result