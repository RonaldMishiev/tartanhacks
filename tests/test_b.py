import sys
import os

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from localbolt.parsing import process_assembly

RAW_GARBAGE = """
    .file "test.cpp"
    .text
    .globl _Z3foov
    .type _Z3foov, @function
_Z3foov:
.LFB0:
    .cfi_startproc
    .loc 1 10 0
    pushq %rbp
    .loc 1 11 0
    movq %rsp, %rbp
    popq %rbp
    .loc 1 12 0
    ret
    .cfi_endproc
"""

def test_pipeline():
    print("--- INPUT ---")
    print(RAW_GARBAGE)
    
    result, mapping = process_assembly(RAW_GARBAGE)
    
    print("\n--- OUTPUT (Cleaned and Demangled) ---")
    print(result)
    
    print("\n--- MAPPING (ASM line -> Source line) ---")
    print(mapping)
    
    # Assertions for content
    assert ".cfi_startproc" not in result
    assert ".loc" not in result
    assert "foo()" in result
    assert "pushq" in result
    
    # Assertions for mapping
    # Expected output lines (approximate indices):
    # 0: foo():
    # 1:     pushq %rbp
    # 2:     movq %rsp, %rbp
    # 3:     popq %rbp
    # 4:     ret
    
    # Note: pushq is line 1, and should map to source line 10
    assert mapping[1] == 10
    assert mapping[2] == 11
    assert mapping[4] == 12
    
    print("\nTest Passed!")

if __name__ == "__main__":
    test_pipeline()