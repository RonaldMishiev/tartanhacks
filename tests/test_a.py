from localbolt.compiler.driver import CompilerDriver

def test_driver():
    # create a dummy c++ file
    with open("temp_test.cpp", "w") as f:
        f.write("int add(int a, int b) { return a + b; }")
        
    driver = CompilerDriver("g++")
    
    print("--- Compiling ---")
    asm, err = driver.compile("temp_test.cpp")
    
    if err:
        print("ERRORS:", err)
    else:
        print("SUCCESS! Assembly sample:")
        print("\n".join(asm.splitlines()[:10])) # Print first 10 lines
        
    print("\n--- Performance Analysis ---")
    perf = driver.analyze_perf(asm)
    print("\n".join(perf.splitlines()[:10]))

if __name__ == "__main__":
    test_driver()