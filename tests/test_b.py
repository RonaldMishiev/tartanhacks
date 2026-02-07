import sys
import os

# Add project root to python path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parsing import process_assembly

RAW_GARBAGE = """
    .file "test.cpp"
    .text
    .globl _Z3foov
    .type _Z3foov, @function
_Z3foov:
.LFB0:
    .cfi_startproc
    pushq %rbp
    movq %rsp, %rbp
    popq %rbp
    ret
    .cfi_endproc
"""

def test_pipeline():
    print("--- INPUT ---")
    print(RAW_GARBAGE)
    
    result = process_assembly(RAW_GARBAGE)
    
    print("\n--- OUTPUT (Should be clean and say 'foo()') ---")
    print(result)
    
    # Assertions
    assert ".cfi_startproc" not in result
    assert "_Z3foov" not in result  # Should be replaced
    assert "foo()" in result        # Should be present
    assert "pushq" in result        # Instructions should persist

if __name__ == "__main__":
    test_pipeline()
