from typing import Callable, Optional
from .compiler.driver import CompilerDriver
from .parsing import process_assembly, parse_mca_output, parse_diagnostics
from .utils.state import LocalBoltState
from .utils.watcher import FileWatcher
import time

class BoltEngine:
    """
    The 'Brain' that coordinates compilation, parsing, and state updates.
    """
    def __init__(self, source_file: str):
        self.state = LocalBoltState(source_path=source_file)
        self.driver = CompilerDriver()
        self.watcher = FileWatcher()
        self.on_update_callback: Optional[Callable[[LocalBoltState], None]] = None

    def start(self):
        """Initial compile and start watching."""
        self.refresh()
        self.watcher.start_watching(self.state.source_path, self._on_file_saved)

    def stop(self):
        self.watcher.stop_watching()

    def _on_file_saved(self, path: str):
        self.refresh()

    def refresh(self):
        """
        Runs the full pipeline:
        1. Read Source
        2. Compile to ASM
        3. Parse Diagnostics (Errors/Warnings)
        4. Clean/Map ASM
        5. Analyze with MCA (if available)
        6. Trigger UI update
        """
        try:
            # 1. Read source
            with open(self.state.source_path, "r") as f:
                content = f.read()
                self.state.source_code = content
                self.state.source_lines = content.splitlines()

            # 2. Compile
            asm_raw, stderr = self.driver.compile(self.state.source_path)
            
            # 3. Handle Diagnostics
            self.state.compiler_output = stderr
            self.state.diagnostics = parse_diagnostics(stderr)

            # 4. Handle Assembly (Only if compilation didn't fail hard)
            if asm_raw:
                clean_asm, mapping = process_assembly(asm_raw, self.state.source_path)
                self.state.update_asm(clean_asm, mapping)

                # 5. Performance Analysis
                mca_raw = self.driver.analyze_perf(asm_raw)
                if mca_raw and not mca_raw.startswith("Error"):
                    perf_stats = parse_mca_output(mca_raw)
                    self.state.update_perf(perf_stats, mca_raw)
                else:
                    self.state.update_perf({}, mca_raw)
            else:
                # If no assembly, clear old data so UI knows to switch to error view
                self.state.update_asm("", {})

            self.state.last_update = time.time()
            
            # 6. Notify the UI if a callback is registered
            if self.on_update_callback:
                self.on_update_callback(self.state)

        except Exception as e:
            self.state.compiler_output = f"Internal Engine Error: {str(e)}"
            if self.on_update_callback:
                self.on_update_callback(self.state)