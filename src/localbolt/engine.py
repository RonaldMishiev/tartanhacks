from typing import Callable, Optional
from .compiler.driver import CompilerDriver
from .compiler.rust_driver import RustCompilerDriver
from .parsing import process_assembly, parse_mca_output, parse_diagnostics, InstructionStats
from .utils.state import LocalBoltState
from .utils.watcher import FileWatcher
from .utils.lang import detect_language, Language
import time
import shutil
import os

class BoltEngine:
    def __init__(self, source_file: str):
        self.state = LocalBoltState(source_path=source_file)
        self.language = detect_language(source_file)
        if self.language == Language.RUST:
            self.driver = RustCompilerDriver()
        else:
            self.driver = CompilerDriver()
        self.watcher = FileWatcher()
        self.on_update_callback: Optional[Callable[[LocalBoltState], None]] = None
        self.log_file = "/tmp/localbolt_engine.log"
        self.user_flags: list[str] = []

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

    def set_flags(self, flags: list[str]):
        self.user_flags = flags
        self.refresh()

    def refresh(self):
        self._log(f"Refreshing {self.state.source_path} with flags {self.user_flags}")
        try:
            with open(self.state.source_path, "r") as f:
                content = f.read()
                self.state.source_code = content
                self.state.source_lines = content.splitlines()

            asm_raw, stderr = self.driver.compile(self.state.source_path, user_flags=self.user_flags)
            self.state.compiler_output = stderr
            self.state.user_flags = self.user_flags
            self.state.diagnostics = parse_diagnostics(stderr)
            # write asm to err.txt
            try:
                with open("err.txt", "a") as err_f:
                    err_f.write("ASM_RAW\n")
                    err_f.write(asm_raw)
            except Exception:
                with open("err.txt", "a") as err_f:
                    err_f.write("Error in asm_raw to err.txt\n")

            if asm_raw:
                # 1. Get both demangled and mangled cleaned versions
                lang_str = "rust" if self.language == Language.RUST else "cpp"
                clean_asm, mapping, mangled_asm = process_assembly(
                    asm_raw, self.state.source_path, language=lang_str
                )
                self.state.update_asm(clean_asm, mapping)

                # 2. Run performance analysis on the MANGLED code
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
