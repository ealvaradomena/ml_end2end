# End-to-End Machine Learning — publication package

This is a focused maintenance update to the existing editorial design.

## Files
- `index.html` — generated publication
- `publication.css` — consolidated site/editorial styles, including the reading-interface refinements
- `notebook-base.css` — notebook exporter styles, regenerated from the notebook
- `site.js` — navigation, reading progress, and accessible code copying
- `build_site.py` — reproducible website generator
- `ml_end2end.ipynb` — original source notebook (not edited)

## Rebuild
From this folder, run `python build_site.py --notebook ml_end2end.ipynb --output .` with `nbformat`, `nbconvert`, and `beautifulsoup4` installed.

The contents heading and download link remain stationary while the chapter list scrolls. Copy buttons first use the Clipboard API, then a legacy clipboard fallback, and finally select the code for manual copying. The chapter spacing and navigation type were tuned without changing the design palette.

## Validation
Python and JavaScript syntax, source/HTML structure, notebook preservation, and regeneration are checked. Final browser layout and keyboard interaction should also be checked on your deployment environment.


## Persistent navigation update

The top navigation and bottom footer remain fixed to the viewport during scrolling.
The body reserves space for both to prevent content from being obscured.
Output panels now inherit the website paper background (`--paper`).
These styles live in `publication.css` and survive HTML regeneration.
