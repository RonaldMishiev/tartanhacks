import sys
import os

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from localbolt.parsing.lexer import clean_assembly_with_mapping

def debug_noise():
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
    print("--- CLEANED ASM ---")
    print(cleaned)
    print("--- END ---")

if __name__ == "__main__":
    debug_noise()
