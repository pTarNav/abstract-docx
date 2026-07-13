"""Unit tests for utils/pydantic.py"""
import pytest
from utils.pydantic import ArbitraryBaseModel
from lxml import etree


class TestArbitraryBaseModel:
    """Test suite for ArbitraryBaseModel"""

    def test_arbitrary_base_model_creation(self):
        """Test creating a basic model"""
        class TestModel(ArbitraryBaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

    def test_arbitrary_base_model_with_arbitrary_types(self):
        """Test that ArbitraryBaseModel allows arbitrary types like etree elements"""
        class TestModel(ArbitraryBaseModel):
            name: str
            element: etree._Element

        # Create an etree element
        element = etree.Element("test")
        element.text = "content"

        # This should not raise an error
        model = TestModel(name="test", element=element)
        assert model.name == "test"
        assert model.element.tag == "test"
        assert model.element.text == "content"

    def test_arbitrary_base_model_validation(self):
        """Test that basic validation still works"""
        class TestModel(ArbitraryBaseModel):
            name: str
            value: int

        # Valid model
        model = TestModel(name="test", value=42)
        assert model.value == 42

        # Invalid type should raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            TestModel(name="test", value="not an int")

    def test_arbitrary_base_model_config(self):
        """Test that Config class is properly set"""
        assert ArbitraryBaseModel.Config.arbitrary_types_allowed is True
