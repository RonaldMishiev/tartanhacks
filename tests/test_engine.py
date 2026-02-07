import sys
import os
import time

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from localbolt.engine import BoltEngine

def ui_simulator(state):
    """This represents the TUI's update function."""
    print("\n[UI REFRESH TRIGGERED]")
    print(f"Source Lines: {len(state.source_code.splitlines())}")
    print(f"ASM Lines: {len(state.asm_content.splitlines())}")
    print(f"Mapping Entries: {len(state.asm_mapping)}")
    if state.perf_stats:
        print(f"Performance bottlenecks detected: {len(state.perf_stats)}")
    print("-" * 20)

def test_engine_workflow():
    test_file = "engine_test.cpp"
    # Cleanup old file
    if os.path.exists(test_file):
        os.remove(test_file)

    with open(test_file, "w") as f:
        f.write("int multiply(int a, int b) { return a * b; }\n")

    engine = BoltEngine(test_file)
    engine.on_update_callback = ui_simulator
    
    print("Starting Engine...")
    engine.start() # Trigger first compile
    
    print("\nModifying file to trigger auto-refresh...")
    time.sleep(1)
    with open(test_file, "a") as f:
        f.write("\nint add(int a, int b) { return a + b; }\n")
    
    time.sleep(2) # Wait for re-compile
    engine.stop()
    
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_engine_workflow()