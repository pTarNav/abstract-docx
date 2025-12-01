"""Unit tests for abstract_docx/data_models/styles.py"""
import pytest
from abstract_docx.data_models.styles import (
    FontSize, FontColor, FontScript, ToggleProperty, Bold, Italic, Underline,
    RunStyleProperties, Justification, IndentationValue, Indentation,
    ParagraphStyleProperties, StyleProperties, Style
)


class TestFontSize:
    """Test suite for FontSize class"""

    def test_font_size_creation(self):
        """Test creating a FontSize"""
        font_size = FontSize(12.0)
        assert float(font_size) == 12.0

    def test_font_size_default(self):
        """Test FontSize default value"""
        default = FontSize.default()
        assert float(default) == 22.0

    def test_font_size_from_ooxml_val(self):
        """Test creating FontSize from OOXML value"""
        font_size = FontSize.from_ooxml_val("24")
        assert float(font_size) == 24.0

    def test_font_size_from_ooxml_val_none(self):
        """Test creating FontSize from None OOXML value"""
        font_size = FontSize.from_ooxml_val(None)
        assert font_size is None

    def test_font_size_from_ooxml_val_none_with_default(self):
        """Test creating FontSize from None OOXML value with must_default"""
        font_size = FontSize.from_ooxml_val(None, must_default=True)
        assert float(font_size) == 22.0


class TestFontColor:
    """Test suite for FontColor class"""

    def test_font_color_creation(self):
        """Test creating a FontColor"""
        color = FontColor("#FF0000")
        assert color.hex_l == "#ff0000"

    def test_font_color_default(self):
        """Test FontColor default value"""
        default = FontColor.default()
        assert default.hex_l == "#000000"

    def test_font_color_from_ooxml_val(self):
        """Test creating FontColor from OOXML value"""
        color = FontColor.from_ooxml_val("FF0000")
        assert color.hex_l == "#ff0000"

    def test_font_color_from_ooxml_val_auto(self):
        """Test creating FontColor from 'auto' OOXML value"""
        color = FontColor.from_ooxml_val("auto")
        assert color is None

    def test_font_color_from_ooxml_val_auto_with_default(self):
        """Test creating FontColor from 'auto' OOXML value with must_default"""
        color = FontColor.from_ooxml_val("auto", must_default=True)
        assert color.hex_l == "#000000"

    def test_font_color_from_ooxml_val_none(self):
        """Test creating FontColor from None OOXML value"""
        color = FontColor.from_ooxml_val(None)
        assert color is None


class TestFontScript:
    """Test suite for FontScript enum"""

    def test_font_script_values(self):
        """Test FontScript enum values"""
        assert FontScript.NORMAL.value == "normal"
        assert FontScript.SUPERSCRIPT.value == "superscript"
        assert FontScript.SUBSCRIPT.value == "subscript"

    def test_font_script_default(self):
        """Test FontScript default value"""
        assert FontScript.default() == FontScript.NORMAL

    def test_font_script_from_ooxml_val(self):
        """Test creating FontScript from OOXML values"""
        assert FontScript.from_ooxml_val("baseline") == FontScript.NORMAL
        assert FontScript.from_ooxml_val("superscript") == FontScript.SUPERSCRIPT
        assert FontScript.from_ooxml_val("subscript") == FontScript.SUBSCRIPT

    def test_font_script_from_ooxml_val_none(self):
        """Test creating FontScript from None OOXML value"""
        result = FontScript.from_ooxml_val(None)
        assert result is None

    def test_font_script_from_ooxml_val_unknown(self):
        """Test creating FontScript from unknown OOXML value defaults"""
        result = FontScript.from_ooxml_val("unknown", must_default=True)
        assert result == FontScript.NORMAL


class TestToggleProperty:
    """Test suite for ToggleProperty class"""

    def test_toggle_property_true(self):
        """Test creating a ToggleProperty with True value"""
        prop = ToggleProperty(True)
        assert int(prop) == 1
        assert str(prop) == "True"

    def test_toggle_property_false(self):
        """Test creating a ToggleProperty with False value"""
        prop = ToggleProperty(False)
        assert int(prop) == 0
        assert str(prop) == "False"

    def test_toggle_property_truthy(self):
        """Test creating a ToggleProperty with truthy value"""
        prop = ToggleProperty(1)
        assert int(prop) == 1

    def test_toggle_property_falsey(self):
        """Test creating a ToggleProperty with falsey value"""
        prop = ToggleProperty(0)
        assert int(prop) == 0

    def test_toggle_property_default(self):
        """Test ToggleProperty default value"""
        default = ToggleProperty.default()
        assert int(default) == 0

    def test_toggle_property_from_existing_ooxml_val_str(self):
        """Test parsing OOXML value strings"""
        assert ToggleProperty._from_existing_ooxml_val_str("1") is True
        assert ToggleProperty._from_existing_ooxml_val_str("true") is True
        assert ToggleProperty._from_existing_ooxml_val_str("0") is False
        assert ToggleProperty._from_existing_ooxml_val_str("false") is False


class TestBold:
    """Test suite for Bold class"""

    def test_bold_is_toggle_property(self):
        """Test that Bold is a ToggleProperty"""
        bold = Bold(True)
        assert isinstance(bold, ToggleProperty)
        assert int(bold) == 1


class TestItalic:
    """Test suite for Italic class"""

    def test_italic_is_toggle_property(self):
        """Test that Italic is a ToggleProperty"""
        italic = Italic(True)
        assert isinstance(italic, ToggleProperty)
        assert int(italic) == 1


class TestUnderline:
    """Test suite for Underline class"""

    def test_underline_is_toggle_property(self):
        """Test that Underline is a ToggleProperty"""
        underline = Underline(True)
        assert isinstance(underline, ToggleProperty)
        assert int(underline) == 1

    def test_underline_from_existing_ooxml_val_str_none(self):
        """Test Underline parsing 'none' value"""
        assert Underline._from_existing_ooxml_val_str("none") is False

    def test_underline_from_existing_ooxml_val_str_single(self):
        """Test Underline parsing 'single' value"""
        assert Underline._from_existing_ooxml_val_str("single") is True


class TestRunStyleProperties:
    """Test suite for RunStyleProperties class"""

    def test_run_style_properties_creation(self):
        """Test creating RunStyleProperties"""
        props = RunStyleProperties(
            font_size=FontSize(12.0),
            font_color=FontColor("#000000"),
            font_script=FontScript.NORMAL,
            bold=Bold(True),
            italic=Italic(False),
            underline=Underline(False)
        )
        assert props.font_size == 12.0
        assert props.font_color.hex_l == "#000000"
        assert props.font_script == FontScript.NORMAL
        assert int(props.bold) == 1
        assert int(props.italic) == 0

    def test_run_style_properties_default(self):
        """Test RunStyleProperties default values"""
        default = RunStyleProperties.default()
        assert default.font_size == 22.0
        assert default.font_color.hex_l == "#000000"
        assert default.font_script == FontScript.NORMAL
        assert int(default.bold) == 0
        assert int(default.italic) == 0

    def test_run_style_properties_empty(self):
        """Test creating empty RunStyleProperties"""
        props = RunStyleProperties()
        assert props.font_size is None
        assert props.font_color is None
        assert props.font_script is None

    def test_run_style_properties_patch(self):
        """Test patching RunStyleProperties"""
        props = RunStyleProperties(font_size=FontSize(12.0))
        other = RunStyleProperties(font_size=FontSize(14.0), bold=Bold(True))
        
        props.patch(other)
        
        assert props.font_size == 14.0
        assert props.bold == 1


class TestJustification:
    """Test suite for Justification enum"""

    def test_justification_values(self):
        """Test Justification enum values"""
        assert Justification.START.value == "start"
        assert Justification.CENTER.value == "center"
        assert Justification.END.value == "end"
        assert Justification.JUSTIFIED.value == "justified"

    def test_justification_default(self):
        """Test Justification default value"""
        assert Justification.default() == Justification.START

    def test_justification_from_ooxml_val(self):
        """Test creating Justification from OOXML values"""
        assert Justification.from_ooxml_val("start") == Justification.START
        assert Justification.from_ooxml_val("left") == Justification.START
        assert Justification.from_ooxml_val("center") == Justification.CENTER
        assert Justification.from_ooxml_val("end") == Justification.END
        assert Justification.from_ooxml_val("right") == Justification.END
        assert Justification.from_ooxml_val("both") == Justification.JUSTIFIED

    def test_justification_from_ooxml_val_none(self):
        """Test creating Justification from None OOXML value"""
        result = Justification.from_ooxml_val(None)
        assert result is None


class TestIndentationValue:
    """Test suite for IndentationValue class"""

    def test_indentation_value_creation(self):
        """Test creating an IndentationValue"""
        indent = IndentationValue(100.0)
        assert float(indent) == 100.0

    def test_indentation_value_default(self):
        """Test IndentationValue default value"""
        default = IndentationValue.default()
        assert float(default) == 0.0

    def test_indentation_value_from_ooxml_val(self):
        """Test creating IndentationValue from OOXML value"""
        indent = IndentationValue.from_ooxml_val("720")
        assert float(indent) == 720.0

    def test_indentation_value_from_ooxml_val_none(self):
        """Test creating IndentationValue from None OOXML value"""
        indent = IndentationValue.from_ooxml_val(None)
        assert indent is None


class TestIndentation:
    """Test suite for Indentation class"""

    def test_indentation_creation(self):
        """Test creating an Indentation"""
        indent = Indentation(
            start=IndentationValue(100.0),
            end=IndentationValue(50.0),
            first=IndentationValue(25.0)
        )
        assert indent.start == 100.0
        assert indent.end == 50.0
        assert indent.first == 25.0

    def test_indentation_default(self):
        """Test Indentation default values"""
        default = Indentation.default()
        assert default.start == 0.0
        assert default.end == 0.0
        assert default.first == 0.0

    def test_indentation_empty(self):
        """Test creating empty Indentation"""
        indent = Indentation()
        assert indent.start is None
        assert indent.end is None
        assert indent.first is None


class TestParagraphStyleProperties:
    """Test suite for ParagraphStyleProperties class"""

    def test_paragraph_style_properties_creation(self):
        """Test creating ParagraphStyleProperties"""
        indent = Indentation(start=IndentationValue(100.0))
        props = ParagraphStyleProperties(
            justification=Justification.CENTER,
            indentation=indent
        )
        assert props.justification == Justification.CENTER
        assert props.indentation.start == 100.0

    def test_paragraph_style_properties_default(self):
        """Test ParagraphStyleProperties default values"""
        default = ParagraphStyleProperties.default()
        assert default.justification == Justification.START
        assert default.indentation.start == 0.0

    def test_paragraph_style_properties_empty(self):
        """Test creating empty ParagraphStyleProperties"""
        props = ParagraphStyleProperties()
        assert props.justification is None
        # indentation should have a default value of Indentation()
        assert isinstance(props.indentation, Indentation)


class TestStyleProperties:
    """Test suite for StyleProperties class"""

    def test_style_properties_creation(self):
        """Test creating StyleProperties"""
        run_props = RunStyleProperties(font_size=FontSize(12.0))
        para_props = ParagraphStyleProperties(justification=Justification.CENTER)
        
        style_props = StyleProperties(
            run_style_properties=run_props,
            paragraph_style_properties=para_props
        )
        
        assert style_props.run_style_properties.font_size == 12.0
        assert style_props.paragraph_style_properties.justification == Justification.CENTER
        assert style_props.table_style_properties is None


class TestStyle:
    """Test suite for Style class"""

    def test_style_creation(self):
        """Test creating a Style"""
        run_props = RunStyleProperties.default()
        para_props = ParagraphStyleProperties.default()
        style_props = StyleProperties(
            run_style_properties=run_props,
            paragraph_style_properties=para_props
        )
        
        style = Style(id="Heading1", properties=style_props)
        
        assert style.id == "Heading1"
        assert style.parent is None
        assert style.children is None
        assert style.properties is not None

    def test_style_with_parent(self):
        """Test creating a Style with parent"""
        run_props = RunStyleProperties.default()
        para_props = ParagraphStyleProperties.default()
        style_props = StyleProperties(
            run_style_properties=run_props,
            paragraph_style_properties=para_props
        )
        
        parent_style = Style(id="Normal", properties=style_props)
        child_style = Style(id="Heading1", parent=parent_style, properties=style_props)
        
        assert child_style.parent.id == "Normal"

    def test_style_equality(self):
        """Test Style equality based on properties"""
        run_props = RunStyleProperties.default()
        para_props = ParagraphStyleProperties.default()
        style_props1 = StyleProperties(
            run_style_properties=run_props,
            paragraph_style_properties=para_props
        )
        style_props2 = StyleProperties(
            run_style_properties=run_props,
            paragraph_style_properties=para_props
        )
        
        style1 = Style(id="Style1", properties=style_props1)
        style2 = Style(id="Style2", properties=style_props2)
        
        # Styles should be equal if properties are equal
        assert style1 == style2

    def test_style_with_children(self):
        """Test creating a Style with children"""
        run_props = RunStyleProperties.default()
        para_props = ParagraphStyleProperties.default()
        style_props = StyleProperties(
            run_style_properties=run_props,
            paragraph_style_properties=para_props
        )
        
        parent = Style(id="Parent", properties=style_props)
        child1 = Style(id="Child1", parent=parent, properties=style_props)
        child2 = Style(id="Child2", parent=parent, properties=style_props)
        parent.children = [child1, child2]
        
        assert len(parent.children) == 2
        assert parent.children[0].id == "Child1"
        assert parent.children[1].id == "Child2"
