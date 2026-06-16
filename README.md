# Unified Manga-to-Video Research Repository

This repository is the consolidated root for the three existing project folders:

- AnimeGen
- Manga_evaluation
- Post-Processing

The goal is to keep one GitHub-ready structure for code, evaluation, and post-processing while preserving the original project folders as the source of truth during migration.

## Unified layout

```text
CV/
├── src/
│   ├── preprocessing/   # dataset parsing, XML, panel cleanup, CLI helpers
│   ├── inference/       # inference wrappers and routing logic
│   ├── evaluation/      # metrics and evaluation utilities
│   └── utils/           # path, device, logging helpers
├── tools/
│   └── streamlit/       # Streamlit UI and evaluator interface
├── scripts/
│   ├── local/           # FFmpeg / RIFE / smoothing helpers
│   └── kaggle/          # notebook-ready export cells and ablations
├── configs/             # YAML / JSON configuration
├── data/
│   └── samples/         # small example inputs only
├── docs/                # setup, usage, migration notes
├── tests/               # unit tests and regression checks
├── requirements/
│   ├── base.txt
│   ├── streamlit.txt
│   └── dev.txt
└── README.md
```

## Current migration approach

1. Keep the existing project folders intact for now.
2. Use the new root folders as the unified entry point for future development.
3. Move or reference heavy assets such as:
   - Post-Processing/rife_engine/
   - data/videos/    # Contains video input folders (Akuhamu, OL_lunch, TetsuSan, etc.)
   - large raw datasets
   only after the codebase is verified.

## Quick start

```bash
pip install -r requirements/base.txt
```

For the local UI / evaluator path:

```bash
pip install -r requirements/streamlit.txt
```

For development tools:

```bash
pip install -r requirements/dev.txt
```

## Notes

- The original folders remain available for reference while the unified structure is being populated.
- Large binaries and output videos should stay out of GitHub by using the ignore rules below.
- Use the docs in this folder as the canonical migration guide.
