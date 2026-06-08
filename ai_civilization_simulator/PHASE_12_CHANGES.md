# Phase 12 — Professional Packaging & Strategic Map Overhaul

This version is built from the Phase 10 stable project and includes the Phase 10 `run_simulation.clear()` bug fix.

## Included upgrades

- Fixed `run_simulation.clear()` by using Streamlit cache clearing safely.
- Clearer scenario controls in the sidebar.
- Strategic map views: Territory, Terrain, Resources, War, Religion, Economy and Technology.
- Final report section with exportable Markdown.
- Cleaner ZIP without `__pycache__` files.
- README prepared for GitHub publishing.

## How to run

```bash
pip3 install -r requirements.txt
streamlit run app.py
```
