<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/TUI-Textual-45d3ee?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-191A1A?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Tests-50%20passing-d1e7dd?style=for-the-badge" />
</p>

<h1 align="center">
  ⚡ LocalBolt
</h1>
<<<<<<< HEAD

<p align="center">
<<<<<<< HEAD
  <b>A local, offline Compiler Explorer — right in your terminal.</b><br/>
  <sub>Write C++ in your editor. Watch the assembly update live. Understand every instruction.</sub>
=======
  <sub>Write C++ in your editor. Watch the assembly update live. Understand every instruction.</sub><br/>                                                                                                   │
  <a href="https://pages.cs.wisc.edu/~samad/localbolt/localbolt.html">Visit the Project Website</a>
>>>>>>> 63c514f (Update README to remove bold description)
</p>

<p align="center">
  <code>localbolt hello.cpp</code>
</p>

---
=======
<p align="center">                                                                                                                                                                                          
<b>A local, offline Compiler Explorer — right in your terminal.</b><br/>                                                                                                                                  
<sub>Write C++ in your editor. Watch the assembly update live. Understand every instruction.</sub><br/>                                                                                                   
<a href="https://pages.cs.wisc.edu/~samad/localbolt/localbolt.html">Visit the Project Website</a>                                                                                                         
</p>
>>>>>>> 121670c (Revise README content for clarity and accuracy)

## What is LocalBolt?

**LocalBolt** is an offline, privacy-first Compiler Explorer that runs entirely in your terminal. It watches your C++ source files, recompiles on every save, and displays syntax-highlighted assembly output with per-instruction performance metrics — all without ever leaving your local machine. Inspired by Godbolt (https://godbolt.org/). 

Built with [Textual](https://textual.textualize.io/) and [Rich](https://rich.readthedocs.io/), this project was initially built for the TartanHacks (Carnegie Mellon) Hackathon. Where the project won the "Best Innovation without AI" award. It features a clean **Mosaic** light theme with a cyan-to-teal gradient palette designed for extended readability.

### ✨ Key Features

| Feature | Description |
|---|---|
| 🔄 **Live Reload** | Watches your `.cpp` file with [Watchdog](https://github.com/gorakhargosh/watchdog) — assembly refreshes instantly on save |
| 🎨 **Syntax Highlighting** | Color-coded assembly: <span style="color:#45d3ee">instructions</span>, <span style="color:#fecd91">registers</span>, <span style="color:#94bfc1">labels</span>, <span style="color:#a37acc">size keywords</span>, and <span style="color:#666">numbers</span> |
| 📊 **Performance Heatmap** | Per-instruction cycle counts from `llvm-mca` with a green → amber → red severity gradient |
| 🔗 **Source ↔ Assembly Mapping** | Floating peek popup shows exactly which C++ line generated the current assembly |
| 🔗 **Sibling Highlighting** | Assembly lines from the same C++ source line get a `│` gutter indicator when selected |
| 📖 **Instruction Help** | Floating popup with description, example, and meaning for the instruction under the cursor |
| ⌨️ **Vim-Style Navigation** | `j`/`k` and arrow keys for scrolling through assembly |
| 🧹 **Clean Output** | Strips compiler directives, debug noise, and system symbols — shows only your code |
| 🔧 **Auto-Discovery** | Finds `compile_commands.json` in your project and inherits build flags automatically |
| 📖 **Assembly Reference** | Built-in `--assemblyhelp` reference for 30+ common x86 and ARM64 (Apple Silicon) instructions |

---

## 🚀 Quick Start

### Prerequisites

| Tool | Purpose | Install |
|---|---|---|
| **Python 3.10+** | Runtime | [python.org](https://www.python.org/downloads/) |
| **g++ or clang++** | C++ compilation | `brew install gcc` / `apt install g++` |
| **llvm-mca** | Performance analysis | `brew install llvm` / `apt install llvm` |
| **c++filt** | C++ symbol demangling | Included with `gcc` / `binutils` |
| **rustc** *(optional)* | Rust compilation | [rustup.rs](https://rustup.rs/) |
| **rustfilt** *(optional)* | Rust symbol demangling | `cargo install rustfilt` |

### Install

```bash
# Clone the repository
git clone https://github.com/RonaldMishiev/tartanhacks.git
cd tartanhacks

# Create a virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run

```bash
# Launch the TUI with a source file
localbolt hello.cpp

# Or view the assembly instruction reference
localbolt --assemblyhelp
```

> **Tip:** Edit `hello.cpp` in your favorite editor (VS Code, Vim, etc.) and save — the assembly view updates automatically.

---

## 🖥️ Interface

<img width="1263" height="1206" alt="image" src="https://github.com/user-attachments/assets/33f9d9d4-c792-42ff-b37e-21f2119beebe" />

> **`▶`** marks the cursor line. **`│`** marks sibling assembly lines that originate from the same C++ source line.

### Keybindings

| Key | Action |
|---|---|
| `j` / `↓` | Move cursor down |
| `k` / `↑` | Move cursor up |
| `r` | Force recompile |
| `o` | Compiler options |
| `q` | Quit |

### Performance Heatmap Colors

| Background | Meaning |
|---|---|
| 🟢 Green (`#d1e7dd`) | Low latency — 1 cycle |
| 🟡 Amber (`#fff3cd`) | Medium latency — 2–4 cycles |
| 🔴 Red (`#f8d7da`) | High latency — 5+ cycles |

---

## 🏗️ Architecture

LocalBolt follows a clean **pipeline architecture** where data flows through four independent layers:

```
 ┌─────────────┐     ┌─────────────┐     ┌────────────┐     ┌─────────────┐
 │  Compiler    │────▶│   Parser    │────▶│   Engine   │────▶│     UI      │
 │   Driver     │     │   (Lexer)   │     │  (State)   │     │  (Textual)  │
 └─────────────┘     └─────────────┘     └────────────┘     └─────────────┘
   g++ / clang++       clean & map         coordinate          render &
   llvm-mca            demangle            watch               navigate
                       diagnostics
```

### Module Map

```
src/localbolt/
├── main.py                  # CLI entry point & argument parsing
├── engine.py                # BoltEngine — coordinates the full pipeline
├── __init__.py              # Package root, exports process_assembly
│
├── compiler/                # 🔧 Compilation & Analysis
│   ├── driver.py            #   CompilerDriver — runs g++/clang++ and llvm-mca
│   ├── analyzer.py          #   Auto-discovers compile_commands.json flags
│   └── types.py             #   CompilationResult dataclass
│
├── parsing/                 # 🧹 Assembly Processing
│   ├── lexer.py             #   5-stage assembly cleaner with source line mapping
│   ├── mapper.py            #   C++ symbol demangling via c++filt
│   ├── perf_parser.py       #   Parses llvm-mca output into InstructionStats
│   └── diagnostics.py       #   Parses GCC/Clang stderr into Diagnostic objects
│
├── ui/                      # 🎨 Terminal User Interface
│   ├── app.py               #   LocalBoltApp — main Textual application
│   ├── source_peek.py       #   SourcePeekPanel — floating C++ context popup
│   ├── instruction_help.py  #   InstructionHelpPanel — floating asm instruction reference
│   └── widgets.py           #   AssemblyView & StatusBar reusable widgets
│
├── asm_ui/                  # 🧪 Standalone assembly viewer (development tool)
│   └── asm_app.py           #   AsmApp — file-based assembly viewer prototype
│
└── utils/                   # ⚙️ Shared Utilities
    ├── state.py             #   LocalBoltState — single source of truth dataclass
    ├── config.py            #   ConfigManager — ~/.localbolt/config.json
    ├── watcher.py           #   FileWatcher — Watchdog-based file monitoring
    ├── highlighter.py       #   Assembly syntax highlighting & heatmap gutter
    └── asm_help.py          #   Built-in assembly instruction reference table
```

---

## 🔍 How It Works

### 1. Compilation (`compiler/driver.py`)

The `CompilerDriver` invokes `g++` or `clang++` with carefully layered flags:

```
System flags (-S -g -fverbose-asm)
  └▶ Architecture flags (-masm=intel on x86)
      └▶ Config flags (-O3, user preferences from ~/.localbolt/config.json)
          └▶ Auto-discovered flags (from compile_commands.json)
              └▶ Runtime overrides (user-provided at launch)
```

It then pipes the generated assembly through `llvm-mca` for per-instruction performance metrics (latency, μops, throughput).

### 2. Parsing (`parsing/lexer.py`)

The lexer applies a **5-stage pipeline** to clean raw compiler output:

| Stage | Purpose |
|---|---|
| **Section Filter** | Skip debug sections (`.debug_*`, `__DWARF`) — keep `.text` |
| **Mapping** | Track `.loc` directives to map asm lines → C++ source lines |
| **Block Filter** | Remove system symbols (`__cxa_*`, `__gxx_*`, STL internals) |
| **Instruction Filter** | Strip assembler directives (`.align`, `.cfi_*`) |
| **Portability** | Normalize macOS (`_main`) vs Linux (`.LBB0_1`) label formats |

The result: clean, readable assembly with an accurate `{asm_line → source_line}` mapping dictionary.

### 3. Engine (`engine.py`)

`BoltEngine` is the orchestrator. It:
- Reads the source file
- Calls `CompilerDriver.compile()` → raw assembly
- Passes through `process_assembly()` → cleaned asm + mapping
- Runs `CompilerDriver.analyze_perf()` → `llvm-mca` output
- Parses into `InstructionStats` (latency, μops, throughput)
- Updates `LocalBoltState` (the single source of truth)
- Fires the `on_update_callback` to notify the UI
- Starts `FileWatcher` to auto-refresh on save (debounced at 500ms)

### 4. UI (`ui/app.py`)

`LocalBoltApp` renders the state into an interactive TUI:
- **Per-line `AsmLine` widgets** for individual cursor highlighting & CSS severity classes
- **`AsmScroll`** — a `VerticalScroll` with disabled bindings so the app handles cursor movement with priority
- **Sibling line indicators** — when cursor is on an asm line, all other asm lines from the same C++ source get a `│` gutter mark
- **`SourcePeekPanel`** — floating popup that walks the asm→source mapping (with backward lookup) to show 3 lines of C++ context
- **`InstructionHelpPanel`** — floating popup that shows the description, example, and meaning for the instruction under the cursor
- **Generation-based widget IDs** (`asm-line-{gen}-{idx}`) to prevent `DuplicateIds` errors on refresh

---

## ⚙️ Configuration

LocalBolt stores preferences in `~/.localbolt/config.json`:

```json
{
    "compiler": "g++",
    "opt_level": "-O3",
    "flags": ["-Wall", "-std=c++20"]
}
```

| Key | Default | Description |
|---|---|---|
| `compiler` | `"g++"` | Compiler to use (`g++`, `clang++`, `gcc`, `clang`) |
| `opt_level` | `"-O0"` | Optimization level (`-O0` through `-O3`, `-Os`, `-Oz`) |
| `flags` | `[]` | Additional compiler flags passed to every compilation |

If a `compile_commands.json` is found in the project directory (or `build/`, `out/`, `debug/` subdirectories), its include paths and flags are automatically merged.

---

## 🧪 Testing

LocalBolt features a comprehensive suite of unit and integration tests.

### Run All Tests
The easiest way to verify the entire project is to use the provided test runner:
```bash
./run_all_tests.sh
```

### Individual Test Suites
You can also run specific tests using the virtual environment's Python:

**Unit Tests (Logic & Utilities)**
```bash
pytest tests/unit/
```

**Integration Tests (End-to-End & Systems)**
```bash
pytest tests/integration/
```

**UI Tests (App, Widgets, Source Peek)**
```bash
pytest tests/test_c_app.py tests/test_c_main.py tests/test_c_widgets.py
```

---

## 🎨 Theme: Mosaic

LocalBolt uses a custom light-mode color palette called **Mosaic**:

| Swatch | Hex | Role |
|---|---|---|
| ⬜ | `#EBEEEE` | Background |
| ⬛ | `#191A1A` | Text / Header background |
| 🔵 | `#45d3ee` | Cyan accent — instructions, footer |
| 🔷 | `#9FBFC5` | Muted blue — borders, cursor highlight |
| 🟢 | `#94bfc1` | Teal — labels, panel titles |
| 🟠 | `#fecd91` | Orange — registers, examples |

---

## 📋 Requirements

```
textual>=0.47.1      # TUI framework
watchdog>=3.0.0      # File system monitoring
pygments>=2.17.2     # Syntax highlighting support
rich>=13.7.0         # Terminal rendering
```

System tools: `g++` or `clang++`, `llvm-mca`, `c++filt`

---

## 📄 License

This project was built for [TartanHacks](https://tartanhacks.com/) 2026.

---

<p align="center">
  <sub>Built with ⚡ by the LocalBolt team</sub>
</p>
