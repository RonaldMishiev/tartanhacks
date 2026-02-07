import sys
import os

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from localbolt.parsing.lexer import clean_assembly_with_mapping

def test_filtering_by_file():
    raw_asm = """
	.file 1 "main.cpp"
	.file 2 "/usr/include/c++/v1/iostream"
	.text
.Ltext0:
	.cfi_startproc
	.file 1 "main.cpp"
	.loc 1 1 0
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	.loc 2 500 0
	movl	$42, %eax
	.loc 1 2 0
	popq	%rbp
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
"""
    # We want to keep lines from file 1 (main.cpp) and discard file 2 (iostream)
    # Also noise like .cfi_ and .file should be gone.
    cleaned, mapping = clean_assembly_with_mapping(raw_asm, "main.cpp")
    
    lines = cleaned.splitlines()
    
    # Expected instructions:
    # 0: .Ltext0: (preserved label)
    # 1: pushq	%rbp  (from .loc 1 1 0)
    # 2: movq	%rsp, %rbp (still file 1 context)
    # 3: popq	%rbp (from .loc 1 2 0)
    # 4: ret (still file 1 context)
    
    assert ".Ltext0:" in lines[0]
    assert "pushq" in lines[1]
    assert "movq" in lines[2]
    assert "popq" in lines[3]
    assert "ret" in lines[4]
    
    # Ensure the instruction from file 2 is NOT there
    for line in lines:
        assert "movl" not in line and "$42" not in line

    # Verify mapping
    # line 1 in cleaned assembly comes from source line 1
    assert mapping[1] == 1
    # line 3 in cleaned assembly comes from source line 2
    assert mapping[3] == 2
    print("test_filtering_by_file passed")

def test_filtering_noise():
    raw_asm = """
	.file 1 "test.cpp"
	.loc 1 1 0
	.p2align 4
	.globl	main
	.type	main, @function
main:
	.cfi_startproc
	endbr64
	pushq	%rbp
	movq	%rsp, %rbp
	.loc 1 2 0
	movl	$0, %eax
	popq	%rbp
	ret
	.cfi_endproc
"""
    cleaned, mapping = clean_assembly_with_mapping(raw_asm, "test.cpp")
    lines = cleaned.splitlines()
    
    # Noise like .p2align, .globl, .type, .cfi, endbr64 should be gone
    # Labels (main:) should stay
    assert "main:" in lines[0]
    assert "pushq\t%rbp" in lines[1]
    assert "movq\t%rsp, %rbp" in lines[2]
    assert "movl\t$0, %eax" in lines[3]
    
    for line in lines:
        assert ".p2align" not in line
        assert ".globl" not in line
        assert "endbr64" not in line
    print("test_filtering_noise passed")

if __name__ == "__main__":
    test_filtering_by_file()
    test_filtering_noise()
    print("ALL TESTS PASSED!")