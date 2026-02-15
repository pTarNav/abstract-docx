"""Unit tests for abstract_docx/main.py"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from abstract_docx.main import AbstractDocx
from ooxml_docx.docx import OoxmlDocx


class TestAbstractDocx:
    """Test suite for AbstractDocx class"""

    def test_abstract_docx_creation(self):
        """Test creating an AbstractDocx instance"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        doc = AbstractDocx(file_path="test.docx", ooxml_docx=mock_ooxml)
        
        assert doc.file_path == "test.docx"
        assert doc.ooxml_docx == mock_ooxml
        assert doc._effective_structure is None
        assert doc._hierarchical_structure is None
        assert doc._views is None

    def test_abstract_docx_setup_logger(self):
        """Test setting up logger"""
        # Just verify the method exists and doesn't crash
        AbstractDocx._setup_logger("DEBUG")
        AbstractDocx._setup_logger("INFO")
        AbstractDocx._setup_logger("WARNING")

    @patch('abstract_docx.main.OoxmlDocx')
    def test_abstract_docx_read_method(self, mock_ooxml_class):
        """Test the read class method"""
        mock_ooxml_instance = Mock()
        mock_ooxml_class.read.return_value = mock_ooxml_instance
        
        # Note: This will fail without a real docx file, but we can test the method exists
        # and has the right signature
        assert hasattr(AbstractDocx, 'read')
        assert callable(AbstractDocx.read)

    def test_abstract_docx_views_property_not_constructed(self):
        """Test accessing views property before construction raises error"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        doc = AbstractDocx(file_path="test.docx", ooxml_docx=mock_ooxml)
        
        with pytest.raises(ValueError, match="Please construct"):
            _ = doc.views

    def test_abstract_docx_to_pickle_method_exists(self):
        """Test that to_pickle method exists"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        doc = AbstractDocx(file_path="test.docx", ooxml_docx=mock_ooxml)
        
        assert hasattr(doc, 'to_pickle')
        assert callable(doc.to_pickle)

    def test_abstract_docx_from_pickle_method_exists(self):
        """Test that from_pickle class method exists"""
        assert hasattr(AbstractDocx, 'from_pickle')
        assert callable(AbstractDocx.from_pickle)

    def test_abstract_docx_print_method_exists(self):
        """Test that print method exists"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        doc = AbstractDocx(file_path="test.docx", ooxml_docx=mock_ooxml)
        
        assert hasattr(doc, 'print')
        assert callable(doc.print)

    def test_abstract_docx_to_txt_method_exists(self):
        """Test that to_txt method exists"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        doc = AbstractDocx(file_path="test.docx", ooxml_docx=mock_ooxml)
        
        assert hasattr(doc, 'to_txt')
        assert callable(doc.to_txt)

    def test_abstract_docx_to_json_method_exists(self):
        """Test that to_json method exists"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        doc = AbstractDocx(file_path="test.docx", ooxml_docx=mock_ooxml)
        
        assert hasattr(doc, 'to_json')
        assert callable(doc.to_json)

    def test_abstract_docx_construct_method_exists(self):
        """Test that _construct method exists"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        doc = AbstractDocx(file_path="test.docx", ooxml_docx=mock_ooxml)
        
        assert hasattr(doc, '_construct')
        assert callable(doc._construct)

    def test_abstract_docx_file_path_attribute(self):
        """Test that file_path is properly stored"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        test_path = "/path/to/document.docx"
        doc = AbstractDocx(file_path=test_path, ooxml_docx=mock_ooxml)
        
        assert doc.file_path == test_path

    def test_abstract_docx_ooxml_docx_attribute(self):
        """Test that ooxml_docx is properly stored"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        doc = AbstractDocx(file_path="test.docx", ooxml_docx=mock_ooxml)
        
        assert doc.ooxml_docx is mock_ooxml


class TestAbstractDocxErrorHandling:
    """Test suite for AbstractDocx error handling"""

    def test_invalid_file_path_type(self):
        """Test creating AbstractDocx with invalid file_path type"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        
        # Pydantic should validate this
        with pytest.raises(Exception):  # Pydantic validation error
            AbstractDocx(file_path=123, ooxml_docx=mock_ooxml)

    def test_missing_required_fields(self):
        """Test creating AbstractDocx without required fields"""
        with pytest.raises(Exception):  # Pydantic validation error
            AbstractDocx()

    def test_views_access_before_construction(self):
        """Test that accessing views before construction raises appropriate error"""
        mock_ooxml = Mock(spec=OoxmlDocx)
        doc = AbstractDocx(file_path="test.docx", ooxml_docx=mock_ooxml)
        
        with pytest.raises(ValueError) as exc_info:
            _ = doc.views
        
        assert "construct" in str(exc_info.value).lower()
