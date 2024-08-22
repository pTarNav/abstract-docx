from lxml import etree
from lxml.etree import _Element as etreeElement


def remove_nsmap(element: etreeElement) -> str:
    """
    Removes namespace from the XML element.
    :return: Clean XML element name without the namespace prefix.
    """
    return etree.QName(element).localname

def xpath_query(element: etreeElement, query: str) -> list[etreeElement] | None:
    """
    Wrapper of the .xpath() class function of the lxml package to avoid having to specify
    the namespaces every time.
    Also handles the empty result cases, where instead of an empty list returns None.
    :param element: XML element to perform the xpath query on.
    :param query: Xpath query string.
    :return: Xpath query results, None when the result is empty.
    """

    query_result = element.xpath(query, namespaces=element.nsmap)
    
    if len(query_result) == 0:
        return None
    return query_result