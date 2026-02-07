import subprocess
import shutil

def demangle_stream(asm_content: str) -> str:
    """
    Pipes the entire assembly string through the system's c++filt command.
    This converts _Z7addNumsii -> addNums(int, int) automatically.
    """
    # Check if tool exists (Member A should have installed binutils)
    if not shutil.which("c++filt"):
        return asm_content + "\n# [WARN] c++filt not found, symbols mangled."

    try:
        # Run c++filt as a subprocess
        process = subprocess.Popen(
            ["c++filt"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=asm_content)
        
        if process.returncode != 0:
            return asm_content # Fallback on error
            
        return stdout

    except Exception as e:
        return f"# Error demangling: {e}\n{asm_content}"
