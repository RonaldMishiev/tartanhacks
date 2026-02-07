import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AssemblyUpdateHandler(FileSystemEventHandler):
    """
    Listens for changes to a specific source file and triggers a callback.
    """
    def __init__(self, target_file: str, callback: Callable[[str], None]):
        self.target_file = str(Path(target_file).resolve())
        self.callback = callback
        self.last_triggered = 0
        self.debounce_seconds = 0.5 # Prevent double-triggers from some editors

    def on_modified(self, event):
        if event.is_directory:
            return
            
        if str(Path(event.src_path).resolve()) == self.target_file:
            now = time.time()
            if now - self.last_triggered > self.debounce_seconds:
                self.callback(self.target_file)
                self.last_triggered = now

class FileWatcher:
    """
    Manages the watchdog observer thread.
    """
    def __init__(self):
        self.observer = Observer()
        self.watch = None

    def start_watching(self, file_path: str, callback: Callable[[str], None]):
        """
        Starts a background thread watching the directory of the file_path.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Cannot watch non-existent file: {file_path}")

        handler = AssemblyUpdateHandler(str(path), callback)
        # Watch the parent directory
        self.watch = self.observer.schedule(handler, path.parent, recursive=False)
        self.observer.start()

    def stop_watching(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
