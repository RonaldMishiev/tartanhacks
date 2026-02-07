import sys
import os

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from localbolt.parsing.lexer import clean_assembly_with_mapping

def debug_lexer():
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
    cleaned, mapping = clean_assembly_with_mapping(raw_asm, "main.cpp")
    print("--- CLEANED ASM ---")
    print(cleaned)
    print("--- END ---")
    print("--- MAPPING ---")
    print(mapping)
    print("--- END ---")

if __name__ == "__main__":
    debug_lexer()