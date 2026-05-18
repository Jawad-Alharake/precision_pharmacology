# Precision Pharmacology

An end-to-end data engineering pipeline for drug repurposing. Uses Python and SQL to mine 1M+ LINCS genetic signatures, isolating precision leads. Features temporal pharmacodynamics to classify clinical profiles and a custom PubMed web scraper to verify the commercial novelty and IP status of discovered compounds.

Key improvements and best-practices added to this repository:

- Centralized configuration: `config.py`
- `.gitignore` tuned for large data files and notebooks
- `requirements.txt` pinning common runtime and dev dependencies
- Automated CI: GitHub Actions workflow (`.github/workflows/ci.yml`) to run tests and lint checks
- Pre-commit hooks: Black, isort, flake8 and nbstripout configured to keep notebooks clean
- Tests: Lightweight smoke tests that validate repository structure and configuration
- Tools: `tools/clean_notebooks.py` utility to strip outputs from notebooks safely
- Documentation: `CONTRIBUTING.md` and other guidance files

Quick start
----------

1. Clone the repository

   git clone https://github.com/Jawad-Alharake/precision_pharmacology.git
   cd precision_pharmacology

2. Create a virtual environment and install dependencies

   python -m venv .venv
   source .venv/bin/activate   # on Linux/macOS
   .\.venv\Scripts\activate  # on Windows
   pip install -r requirements.txt

3. Run lightweight tests

   pytest -q

4. Clean notebooks (optional but recommended before committing)

   python tools/clean_notebooks.py

Notes about the notebooks
-------------------------
- The notebooks (phase_1..phase_5) operate on very large LINCS GCTX files (data files are ~20GB). Do not attempt to run them on environments without sufficient disk and memory.
- For reproducible runs, download files listed in `data_sources.txt` and place them alongside the notebooks or update file paths in `config.py`.

Contributing
------------
See CONTRIBUTING.md for details on how to contribute and submit pull requests.

License
-------
This repository is released under the MIT License. See LICENSE for details.
