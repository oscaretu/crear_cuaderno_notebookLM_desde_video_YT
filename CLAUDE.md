# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI tools to automate Google NotebookLM tasks: create notebooks from YouTube videos, generate artifacts (reports, audio, slides, etc.), and list notebooks. Now features rich terminal output.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
notebooklm login  # Authenticate with Google account
notebooklm skill install  # Install Claude Code skill for notebooklm
```

For Bash script, also install `jq`:
```bash
sudo apt install jq  # Linux/WSL
```

## Key Commands

```bash
# Create notebook from YouTube video (Python v0.7.0)
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
python main.py "URL" --todo                 # All artifacts
python main.py "URL" --audio --slides --quiz     # Specific artifacts
python main.py "URL" --mostrar-descripcion  # Show video description
python main.py "URL" --idioma en --debug

# Create notebook from YouTube video (Bash v1.3.0, Spanish only)
./crear_cuaderno.sh "URL"
./crear_cuaderno.sh "URL" --audio --slides  # Add rate-limited artifacts
./crear_cuaderno.sh "URL" --todo            # All artifacts
./crear_cuaderno.sh "URL" --mostrar-descripcion

# View/manage existing notebook (Python v0.1.0)
python ver_cuaderno.py "NOTEBOOK_ID"                  # View artifacts
python ver_cuaderno.py "https://notebooklm.google.com/notebook/ID"
python ver_cuaderno.py "NOTEBOOK_ID" --todo           # Generate missing artifacts
python ver_cuaderno.py "NOTEBOOK_ID" --audio --slides --quiz # Specific artifacts
python ver_cuaderno.py "NOTEBOOK_ID" --mostrar-informe
python ver_cuaderno.py "NOTEBOOK_ID" --idioma en --debug

# List notebooks
python listar_cuadernos.py
python listar_cuadernos.py --ordenar creacion --desc
./listar_cuadernos_como_JSON_ordenados_por_fecha.sh  # JSON output

# Extract Firefox cookies for authentication (v1.0.0)
python extraer_cookies_firefox.py                    # Default profile
python extraer_cookies_firefox.py --listar-perfiles  # List profiles
python extraer_cookies_firefox.py --perfil Susana    # Specific profile
```

## Architecture

### Shared Module

- **common.py**: Shared functions and constants used by `main.py` and `ver_cuaderno.py`. Uses `rich` library for visual output (`Console`, `Table`, `Progress`). Contains: `debug()`, `set_debug()`, `timestamp()`, artifact constants, `verificar_artefactos_existentes()`, `generar_artefactos()` (with progress bars), `mostrar_informe()`.

### Scripts

- **main.py** (Python v0.7.0): Creates notebooks from YouTube videos. Uses `notebooklm` Python API with asyncio. By default only generates report (no daily limit). Use `--todo` for all artifacts. Has smart quota handling (detects rate limits via `is_rate_limited`, skips related artifacts). Artifacts ordered by: no-limit first, then by generation time.

- **ver_cuaderno.py** (Python v0.1.0): Views and manages artifacts of an existing notebook. Accepts a NotebookLM URL or notebook ID. Without artifact flags, only shows current state. With `--todo` or `--report`/`--audio`/etc., generates missing artifacts.

- **crear_cuaderno.sh** (Bash v1.3.0): Uses `notebooklm` CLI. By default generates report and mind-map (no daily limits). Optional flags for rate-limited artifacts: `--audio`, `--video`, `--slides`, `--infographic`, `--quiz`, `--flashcards`, `--todo`.

- **extraer_cookies_firefox.py** (v1.0.0): Extracts Google authentication cookies from Firefox and generates `storage_state.json` for notebooklm-py. Avoids need for `notebooklm login`. Supports WSL2, Windows, Linux, macOS (auto-detected). Firefox can remain open during extraction.

### Notebook Naming Convention

All tools use prefix `YT-{video_id}` to detect existing notebooks and avoid duplicates:
```
YT-dQw4w9WgXcQ - Video Title - 2024-01-15 - Channel Name
```

### NotebookLM Rate Limits

- **No limit**: report, mind-map
- **Daily limit**: audio, video, slides, infographic, quiz, flashcards

Slides and infographic share quota. main.py detects this and skips the second if first fails.

## Known Limitations

- **listar_cuadernos.py**: The `--idioma` filter doesn't work because NotebookLM API doesn't expose artifact language. The `--ordenar modificacion` option doesn't work because API only provides creation date.

## External Dependency

The `notebooklm-py` library has a skill file. Install with:
```bash
notebooklm skill install
```
This enables Claude Code to use NotebookLM commands directly via `/notebooklm` or natural language requests like "create a podcast about X".

## Authentication

### Option 1: Standard login (opens browser)
```bash
notebooklm login
```

### Option 2: Extract cookies from Firefox (recommended for WSL2)
If you have Firefox open with an active Google session, extract cookies without re-login:
```bash
python extraer_cookies_firefox.py                    # Uses default profile
python extraer_cookies_firefox.py --listar-perfiles  # List available profiles
python extraer_cookies_firefox.py --perfil Susana    # Use specific profile
python extraer_cookies_firefox.py --dry-run          # Preview without writing
```

Works on: WSL2, Windows (PowerShell), Linux, macOS. Platform auto-detected.

Verify authentication:
```bash
notebooklm auth check --test
```

### Credentials location
Stored in `~/.notebooklm/storage_state.json`.

## WSL2 Notes

**Git push**: SSH connections may hang in WSL2. Use HTTPS instead:
```bash
git remote set-url origin https://github.com/USER/REPO.git
```
