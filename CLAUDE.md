# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI tools to automate Google NotebookLM tasks: create notebooks from YouTube videos, generate artifacts (reports, audio, slides, etc.), and list notebooks.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
notebooklm login  # Authenticate with Google account
```

For Bash script, also install `jq`:
```bash
sudo apt install jq  # Linux/WSL
```

## Key Commands

```bash
# Create notebook from YouTube video (Python)
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
python main.py "URL" --idioma en --debug

# Create notebook from YouTube video (Bash, Spanish only)
./crear_cuaderno.sh "URL"
./crear_cuaderno.sh "URL" --audio --slides  # Add rate-limited artifacts
./crear_cuaderno.sh "URL" --todo            # All artifacts

# List notebooks
python listar_cuadernos.py
python listar_cuadernos.py --ordenar creacion --desc
```

## Architecture

### Two Implementations

- **main.py** (Python): Uses `notebooklm` Python API with asyncio. Generates report, audio, slides, infographic. Has smart quota handling (detects rate limits, skips related artifacts).

- **crear_cuaderno.sh** (Bash): Uses `notebooklm` CLI. By default only generates artifacts without daily limits (report, mind-map). Optional flags for rate-limited artifacts.

### Notebook Naming Convention

All tools use prefix `YT-{video_id}` to detect existing notebooks and avoid duplicates:
```
YT-dQw4w9WgXcQ - Video Title - 2024-01-15 - Channel Name
```

### NotebookLM Rate Limits

- **No limit**: report, mind-map
- **Daily limit**: audio, video, slides, infographic, quiz, flashcards

Slides and infographic share quota. main.py detects this and skips the second if first fails.

## External Dependency

The `notebooklm-py` library has a skill file at:
```
~/.local/lib/python3.10/site-packages/notebooklm/data/SKILL.md
```
Contains complete CLI reference for `notebooklm` commands.

## WSL2 Note

Credentials are stored in `~/.notebooklm/`. If authenticating from Windows PowerShell but running from WSL2:
```bash
cp /mnt/c/Users/USERNAME/.notebooklm/storage_state.json ~/.notebooklm/
```
