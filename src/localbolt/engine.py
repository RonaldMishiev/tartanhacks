from typing import Callable, Optional
from .compiler.driver import CompilerDriver
from .parsing import process_assembly, parse_mca_output, parse_diagnostics, InstructionStats
from .utils.state import LocalBoltState
from .utils.watcher import FileWatcher
import time
import shutil
import os

class BoltEngine:
    def __init__(self, source_file: str):
        self.state = LocalBoltState(source_path=source_file)
        self.driver = CompilerDriver()
        self.watcher = FileWatcher()
        self.on_update_callback: Optional[Callable[[LocalBoltState], None]] = None
        self.log_file = "/tmp/localbolt_engine.log"

    def _log(self, msg: str):
        with open(self.log_file, "a") as f:
            f.write(f"[{time.time()}] {msg}\n")

    def start(self):
        self.refresh()
        self.watcher.start_watching(self.state.source_path, self._on_file_saved)

    def stop(self):
        self.watcher.stop_watching()

    def _on_file_saved(self, path: str):
        self.refresh()

    def refresh(self):
        self._log(f"Refreshing {self.state.source_path}")
        try:
            with open(self.state.source_path, "r") as f:
                content = f.read()
                self.state.source_code = content
                self.state.source_lines = content.splitlines()

            asm_raw, stderr = self.driver.compile(self.state.source_path)
            self.state.compiler_output = stderr
            self.state.diagnostics = parse_diagnostics(stderr)

            if asm_raw:
                # 1. Get both demangled and mangled cleaned versions
                clean_asm, mapping, mangled_asm = process_assembly(asm_raw, self.state.source_path)
                self.state.update_asm(clean_asm, mapping)

                # 2. Run performance analysis on the MANGLED code
                # (llvm-mca doesn't like C++ symbols like 'add(int, int)')
                self._log("Running analyze_perf on mangled ASM...")
                mca_raw = self.driver.analyze_perf(mangled_asm)
                self._log(f"MCA Raw Length: {len(mca_raw) if mca_raw else 0}")
                
                if mca_raw and "Instruction Info:" in mca_raw:
                    perf_stats = parse_mca_output(mca_raw)
                    self._log(f"Parsed Stats Count: {len(perf_stats)}")
                    self.state.update_perf(perf_stats, mca_raw)
                else:
                    self._log(f"MCA failed. Sample: {mca_raw[:100] if mca_raw else 'None'}")
                    self.state.update_perf({}, mca_raw or "")

            if self.on_update_callback:
                self.on_update_callback(self.state)

        except Exception as e:
            self._log(f"Refresh Error: {str(e)}")
            self.state.compiler_output = f"Internal Engine Error: {str(e)}"
            if self.on_update_callback:
                self.on_update_callback(self.state)
