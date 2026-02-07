import sys
import os

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from localbolt.utils.asm_help import ASM_INSTRUCTIONS, create_gradient_header
from rich.text import Text

def test_asm_instructions_content():
    """Verify that the instruction dictionary is populated and has correct structure."""
    assert len(ASM_INSTRUCTIONS) >= 20
    assert "MOV" in ASM_INSTRUCTIONS
    assert "PUSH" in ASM_INSTRUCTIONS
    
    # Check structure: (Description, Example, Meaning)
    data = ASM_INSTRUCTIONS["MOV"]
    assert len(data) == 3
    assert isinstance(data[0], str)
    assert isinstance(data[1], str)
    assert isinstance(data[2], str)
    assert "mov" in data[1].lower()

def test_gradient_header_generation():
    """Verify that the gradient header is generated as a Rich Text object."""
    title = "TEST HEADER"
    result = create_gradient_header(title)
    
    assert isinstance(result, Text)
    assert title in result.plain
    
    # Check that styles (colors) were applied
    assert len(result._spans) > 0

def test_instruction_sorting():
    """Ensure we can sort the instructions for display."""
    keys = list(ASM_INSTRUCTIONS.keys())
    sorted_keys = sorted(keys)
    # Just check that it's sorted and has the same number of elements
    assert len(sorted_keys) == len(keys)
    assert sorted_keys == sorted(keys)
    assert "ADD" in sorted_keys
    assert "MOV" in sorted_keys

if __name__ == "__main__":
    try:
        test_asm_instructions_content()
        print("test_asm_instructions_content PASSED")
        test_gradient_header_generation()
        print("test_gradient_header_generation PASSED")
        test_instruction_sorting()
        print("test_instruction_sorting PASSED")
        print("ALL ASM HELP UNIT TESTS PASSED!")
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)