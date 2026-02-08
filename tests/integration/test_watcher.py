import sys
import os
import time
from pathlib import Path

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from localbolt.compiler import CompilerDriver
from localbolt.parsing import process_assembly
from localbolt.utils.watcher import FileWatcher

def on_file_change(file_path):
    print(f"\n[EVENT] {file_path} changed! Recompiling...")
    
    driver = CompilerDriver()
    asm, err = driver.compile(file_path)
    
    if err:
        print("Compiler Warnings/Errors:", err)
        
    if asm:
        # process_assembly returns (asm_str, mapping, mangled_asm)
        clean_asm, mapping, _mangled = process_assembly(asm)
        print(f"Success! Clean assembly generated ({len(clean_asm.splitlines())} lines).")
        print(f"First 3 mapping entries: {list(mapping.items())[:3]}")

def test_full_watcher_loop():
    test_file = "watch_me.cpp"
    # Ensure any old file is gone
    if os.path.exists(test_file):
        os.remove(test_file)

    with open(test_file, "w") as f:
        f.write("int square(int x) { return x * x; }\n")
        
    watcher = FileWatcher()
    print(f"Starting watcher for {test_file}...")
    watcher.start_watching(test_file, on_file_change)
    
    try:
        print("Simulating a file save in 1 second...")
        time.sleep(1)
        with open(test_file, "a") as f:
            f.write("// Minor change to trigger watchdog\n")
            
        print("Waiting for callback...")
        time.sleep(2) # Give it time to trigger and finish compile
        
    finally:
        print("Stopping watcher...")
        watcher.stop_watching()
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_full_watcher_loop()