"""Unit tests for utils/printing.py"""
import pytest
from lxml import etree
from rich.tree import Tree
from utils.printing import etree_to_str, rich_tree_to_str


class TestEtreeToStr:
    """Test suite for etree_to_str function"""

    def test_etree_to_str_simple_element(self):
        """Test converting a simple XML element to string"""
        element = etree.Element("root")
        element.text = "Hello World"

        result = etree_to_str(element)
        
        assert "<root>" in result
        assert "Hello World" in result
        assert "</root>" in result

    def test_etree_to_str_with_children(self):
        """Test converting XML element with children to string"""
        root = etree.Element("root")
        child1 = etree.SubElement(root, "child1")
        child1.text = "First child"
        child2 = etree.SubElement(root, "child2")
        child2.text = "Second child"

        result = etree_to_str(root)
        
        assert "<root>" in result
        assert "<child1>First child</child1>" in result
        assert "<child2>Second child</child2>" in result
        assert "</root>" in result

    def test_etree_to_str_with_attributes(self):
        """Test converting XML element with attributes to string"""
        element = etree.Element("root", attrib={"attr1": "value1", "attr2": "value2"})
        element.text = "Content"

        result = etree_to_str(element)
        
        assert "<root" in result
        assert 'attr1="value1"' in result
        assert 'attr2="value2"' in result
        assert ">Content</root>" in result

    def test_etree_to_str_empty_element(self):
        """Test converting an empty XML element to string"""
        element = etree.Element("empty")

        result = etree_to_str(element)
        
        assert "<empty" in result
        assert result.strip().endswith(">")

    def test_etree_to_str_utf8_encoding(self):
        """Test that the function properly handles UTF-8 encoding"""
        element = etree.Element("root")
        element.text = "Hello 世界 🌍"

        result = etree_to_str(element)
        
        assert "Hello 世界 🌍" in result
        assert isinstance(result, str)


class TestRichTreeToStr:
    """Test suite for rich_tree_to_str function"""

    def test_rich_tree_to_str_simple(self):
        """Test converting a simple rich tree to string"""
        tree = Tree("Root")
        
        result = rich_tree_to_str(tree)
        
        assert "Root" in result
        assert isinstance(result, str)

    def test_rich_tree_to_str_with_children(self):
        """Test converting a rich tree with children to string"""
        tree = Tree("Root")
        tree.add("Child 1")
        tree.add("Child 2")
        
        result = rich_tree_to_str(tree)
        
        assert "Root" in result
        assert "Child 1" in result
        assert "Child 2" in result

    def test_rich_tree_to_str_nested(self):
        """Test converting a nested rich tree to string"""
        tree = Tree("Root")
        branch1 = tree.add("Branch 1")
        branch1.add("Leaf 1.1")
        branch1.add("Leaf 1.2")
        branch2 = tree.add("Branch 2")
        branch2.add("Leaf 2.1")
        
        result = rich_tree_to_str(tree)
        
        assert "Root" in result
        assert "Branch 1" in result
        assert "Branch 2" in result
        assert "Leaf 1.1" in result
        assert "Leaf 1.2" in result
        assert "Leaf 2.1" in result

    def test_rich_tree_to_str_empty(self):
        """Test converting an empty rich tree to string"""
        tree = Tree("Empty Tree")
        
        result = rich_tree_to_str(tree)
        
        assert "Empty Tree" in result
        assert len(result) > 0

    def test_rich_tree_to_str_with_special_characters(self):
        """Test converting a rich tree with special characters"""
        tree = Tree("Root 🌳")
        tree.add("Child with special chars: @#$%")
        
        result = rich_tree_to_str(tree)
        
        assert "Root 🌳" in result
        assert "Child with special chars: @#$%" in result
