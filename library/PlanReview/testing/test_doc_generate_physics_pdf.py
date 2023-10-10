"""
Testing functions for generate_physics_pdf.py

"""
# Import necessary modules and functions
import pytest
from PlanReview.documentation.generate_physics_pdf import make_paragraph

# Define test cases


def test_make_paragraph_basic():
    # Test with basic input
    input_text = "Hello, world!"
    expected_output = "<p>Hello, world!</p>"
    assert make_paragraph(input_text) == expected_output


def test_make_paragraph_with_style():
    # Test with custom style
    input_text = "Custom style text"
    custom_style = {'fontName': 'Helvetica-Bold', 'fontSize': 12}
    expected_output = "<p style='fontName: Helvetica-Bold; fontSize: 12'>Custom style text</p>"
    assert make_paragraph(input_text, style=custom_style) == expected_output


def test_make_paragraph_with_special_characters():
    # Test with special characters
    input_text = "Special characters: \u00a0 \n \r \t * "
    expected_output = "<p>Special characters: &nbsp; <br/> <br/> &nbsp;&nbsp;&nbsp;&nbsp; &bull;&nbsp;</p>"
    assert make_paragraph(input_text) == expected_output


# Run the tests
if __name__ == "__main__":
    pytest.main()