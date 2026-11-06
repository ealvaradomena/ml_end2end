import re, shutil, argparse, json
from pathlib import Path
import nbformat
from nbconvert import HTMLExporter
from bs4 import BeautifulSoup
from html import escape
from urllib.parse import unquote, quote
from copy import deepcopy

parser = argparse.ArgumentParser(description="Rebuild the custom GitHub Pages website from a Jupyter notebook")
parser.add_argument("--notebook", default="ml_end2end.ipynb", help="Source notebook path")
parser.add_argument("--output", default=".", help="Output directory containing publication.css and site.js")
args = parser.parse_args()
notebook = Path(args.notebook).expanduser().resolve()
site = Path(args.output).expanduser().resolve()
site.mkdir(parents=True, exist_ok=True)
if not notebook.is_file():
    parser.error(f"Notebook not found: {notebook}")
if not all((site / name).exists() for name in ("publication.css", "site.js")):
    parser.error("Output directory must contain publication.css and site.js from the website package")
nb=nbformat.read(notebook,as_version=4)
html,_=HTMLExporter(template_name='classic').from_notebook_node(nb)
soup=BeautifulSoup(html,'html.parser')
original_css='\n'.join(s.get_text() for s in soup.head.find_all('style'))
(site/'notebook-base.css').write_text(original_css)
container=soup.select_one('#notebook-container')
# Website-only presentation: leave the source notebook untouched.
# Neutralize identifying local paths in rendered text and code, including saved outputs.
# Use a consistent project-root placeholder so examples remain intelligible.
private_roots = set()
for node in container.find_all(string=True):
    text = str(node)
    # Recognize both macOS and common Linux absolute user-home paths
    for m in re.finditer(r'/(?:Users|home)/[^/\s<>"\']+', text):
        private_roots.add(m.group(0))
for node in list(container.find_all(string=True)):
    raw = str(node)
    cleaned = raw
    for root in sorted(private_roots, key=len, reverse=True):
        cleaned = cleaned.replace(root + '/Documents/GitHub/ml_end2end', '~/projects/ml_end2end')
        cleaned = cleaned.replace(root + '/miniforge3', '~/miniforge3')
        cleaned = cleaned.replace(root, '~')
    if cleaned != raw:
        node.replace_with(cleaned)
# Normalize any remaining local absolute paths not preceded by a recognized home prefix

# Normalize exporter-generated percent escapes and make repeated headings unique
seen_ids = {}
for element in container.select('[id]'):
    original = unquote(element['id'])
    count = seen_ids.get(original, 0)
    seen_ids[original] = count + 1
    element['id'] = original if count == 0 else f'{original}-{count + 1}'
# Short navigation labels are editorial metadata; original notebook headings remain intact.
NAV_LABELS = {
  0: 'Environment setup', 1: 'Load the dataset', 2: 'Inspect the data',
  3: 'Categorical variables', 4: 'Cholesterol distribution',
  5: 'Missing values and duplicates', 6: 'Summary statistics',
  7: 'Predictors and data split', 8: 'Leakage-safe imputation',
  9: 'Age distribution', 10: 'Min–max scaling', 11: 'Standardization',
  12: 'Compare transformations', 13: 'Methods reference',
  14: 'Feature selection', 15: 'SVC imports', 16: 'SVC data split',
  17: 'Train and predict with SVC', 18: 'MLflow tracking',
  19: 'K-fold splitting', 20: 'Confusion matrix',
  21: 'Cross-validation', 22: 'Inference tests',
  23: 'Feast entity and schema', 24: 'Feast feature registration',
  25: 'Prediction monitoring', 26: 'Drift detection', 27: 'Feedback loops',
}
NAV_GROUPS = [(0, 'Environment'), (2, 'Exploration'), (5, 'Data preparation'), (14, 'Modeling'), (18, 'Evaluation'), (23, 'Operations and monitoring')]
nav=[]
last_heading = 'Notebook visualization'
image_index = 0
for cell in container.select(':scope > .cell'):
    for p in cell.select('.prompt'):
        p.decompose()
    for anchor in cell.select('.anchor-link'):
        anchor.decompose()
    for h in cell.select('h1,h2,h3'):
        title=h.get_text(' ',strip=True)
        last_heading = title
        if h.name=='h1':
            h['class']=h.get('class',[])+['chapter-heading']
            # The notebook contains two redundant unnumbered H1 transitions.
            # Represent these as editorial dividers without modifying the notebook.
            if title in ('Data Preparation', 'Case Study: Predicting Heart Disease'):
                h.name = 'h2'
                h['class'] = ['editorial-divider']
        if title == 'Part II — Preparing the Data':
            h.name = 'p'
            h['class'] = ['part-marker']
        if title == 'Model-Based Feature Selection: Training-Derived Decisions':
            h['class'] = h.get('class',[]) + ['transition-heading']
        elif h.name=='h2' and re.match(r'^\d+\.\s',title):
            h['class']=h.get('class',[])+['chapter-heading']
            nav.append((h.get('id',''),title))
        if 'EXPLORE FURTHER' in title:
            cell['class']=cell.get('class',[])+['explore-cell']
            h['class']=h.get('class',[])+['explore-heading']
    if 'code_cell' in cell.get('class',[]):
        input_area=cell.select_one('.input_area')
        if input_area:
            toolbar=soup.new_tag('div',attrs={'class':'code-toolbar'})
            tag=soup.new_tag('span',attrs={'class':'code-label'});tag.string='Python'
            btn=soup.new_tag('button',attrs={'class':'copy-code','type':'button','aria-label':'Copy Python code'});btn.string='Copy code'
            toolbar.append(tag);toolbar.append(btn)
            input_area.insert_before(toolbar)
            cell['class'] = cell.get('class',[]) + ['execution-cell']
            source = input_area.select_one('pre')
            if source:
                # Preserve exact source text for copying, independent of syntax-highlighted DOM.
                btn['data-source'] = json.dumps(source.get_text(), ensure_ascii=False)[1:-1]
                btn['data-json-encoded'] = 'true'
        outputs=cell.select_one('.output_wrapper')
        if outputs and outputs.get_text(' ',strip=True):
            outputs['class']=outputs.get('class',[])+['output-panel']
            label=soup.new_tag('div',attrs={'class':'output-label'});label.string='Output'
            outputs.insert(0,label)
    # Distinguish terminal examples (Markdown-rendered shell snippets) from Python cells.
    for pre in cell.select('.text_cell_render .highlight pre'):
        wrapper = pre.find_parent('div', class_='highlight')
        if wrapper:
            wrapper['class'] = wrapper.get('class', []) + ['terminal-block']
            label = soup.new_tag('div', attrs={'class': 'terminal-caption'})
            label.string = 'Terminal · shell command'
            wrapper.insert(0, label)
    # Give notebook figures descriptive, non-speculative accessible names.
    for img in cell.select('img'):
        image_index += 1
        previous_alt = img.get('alt', '').strip()
        if not previous_alt or 'No description has been provided' in previous_alt:
            img['alt'] = f'Notebook figure {image_index}, associated with {last_heading}'
        img['loading'] = 'lazy'
        img['decoding'] = 'async'
    # remove internal notebook cell IDs with '=' which aren't useful
    if cell.get('id','').startswith('cell-id='):del cell['id']

# Add previous/next section links at the END of each numbered section.
# Sections are split at their first heading, not at arbitrary cell boundaries.
for i, (section_id, title) in enumerate(nav):
    heading = container.find(id=section_id)
    if heading is None: continue
    parent_cell = heading.find_parent('div', class_='cell')
    if parent_cell is None: continue
    next_heading = container.find(id=nav[i+1][0]) if i + 1 < len(nav) else None
    next_cell = next_heading.find_parent('div', class_='cell') if next_heading else None
    if next_cell is None:
        following = [c for c in container.select(':scope > .cell') if c is parent_cell or c.find_previous_sibling('div', class_='cell')]
        end_cell = container.select(':scope > .cell')[-1]
    else:
        end_cell = next_cell.find_previous_sibling('div', class_='cell')
    if end_cell is None: continue
    navbox = soup.new_tag('nav', attrs={'class':'section-pager', 'aria-label':f'Navigation for section {i}'})
    if i > 0:
        a = soup.new_tag('a', href='#'+quote(nav[i-1][0],safe='-._~'))
        a.string = '←  '+NAV_LABELS.get(i-1,nav[i-1][1])
        navbox.append(a)
    if i + 1 < len(nav):
        a = soup.new_tag('a', href='#'+quote(nav[i+1][0],safe='-._~'))
        a.string = NAV_LABELS.get(i+1,nav[i+1][1])+'  →'
        navbox.append(a)
    end_cell.insert_after(navbox)
# Ensure heading links remain stable, and use them for toc
sections = ''
for i, (k, title) in enumerate(nav):
    for start, group in NAV_GROUPS:
        if i == start:
            sections += f'<p class="toc-group">{escape(group)}</p>'
    label = NAV_LABELS.get(i, re.sub(r'^\d+\.\s*', '', title))
    href = escape(quote(k, safe='-._~'), quote=True)
    sections += (f'<a class="toc-link" href="#{href}" title="{escape(title, quote=True)}">'
                 f'<span class="toc-number">{i}</span><span>{escape(label)}</span></a>')

page=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#5e0d32"><meta name="description" content="A documented, end-to-end machine learning case study using Python, scikit-learn, MLflow, Feast and model monitoring.">
<title>End-to-End Machine Learning | An Applied Notebook</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="notebook-base.css"><link rel="stylesheet" href="publication.css">
</head><body>
<a class="skip-link" href="#main-content">Skip to notebook</a><div class="reading-progress" aria-hidden="true"><span></span></div>
<header class="site-header"><a class="wordmark" href="#top">End-to-End<span> </span>Machine Learning</a>
<nav class="top-links" aria-label="Primary navigation"><a href="#overview">Overview</a><a href="#contents">Contents</a><a class="download-link" href="ml_end2end.ipynb" download>Source notebook ↗</a></nav>
<button class="mobile-toc-toggle" type="button" aria-controls="contents" aria-expanded="false" aria-label="Open notebook contents">Contents <span aria-hidden="true">☰</span></button></header>
<section class="hero" id="top"><div class="hero-inner"><p class="eyebrow">FIELD NOTES <span> / </span> PROGRAMMING DRILLS</p>
<h1>End-to-End the<br><em>Machine Learning</em></h1>
<div class="hero-bottom"><p>A documented Python study of heart-disease classification: from reading a CSV file and preparing features to evaluating models, tracking experiments, and introducing monitoring.</p>
<a class="hero-action" href="#content">Open the notebook <span aria-hidden="true">↘</span></a></div>
<div class="hero-foot"><span>PYTHON · SCIKIT-LEARN · MLFLOW · FEAST</span><span>{len(nav)} CHAPTERS · READ IN SEQUENCE OR EXPLORE</span></div></div></section>
<section class="overview" id="overview"><div class="overview-inner"><div><p class="section-kicker">PROJECT OVERVIEW</p><h2>Methods, decisions,<br><em>and documentation</em></h2></div><div class="overview-copy"><p>This notebook works through the decisions behind a machine learning pipeline: inspecting a dataset, handling missingness, separating training from evaluation, and interpreting model results.</p><p>It retains intermediate investigations and instructional exercises, including optional infrastructure demonstrations. The dataset is used for education, not clinical decision-making.</p><p class="scope-note">Includes exploratory analysis, feature selection, classification, cross-validation, MLflow, Feast, and introductory drift monitoring.</p></div></div></section>
<div class="reading-layout" id="content"><aside class="toc" id="contents" aria-label="Notebook table of contents"><div class="toc-inner"><p class="toc-kicker">NOTEBOOK / INDEX</p><h2>Contents</h2><div class="toc-scroll">{sections}</div><a class="toc-source" href="ml_end2end.ipynb" download>↓ Download .ipynb</a></div></aside>
<main class="notebook-main" id="main-content"><div class="notebook-preface"><p class="section-kicker">THE NOTEBOOK</p><p>Read the original explanations, Python code, and saved results. Select a chapter from the index to jump directly to it.</p></div><article class="notebook-article" aria-label="Rendered Jupyter notebook">{str(container)}</article>
<div class="end-note"><span>END OF NOTEBOOK</span><p>Continue exploring in the editable Jupyter source.</p><a href="ml_end2end.ipynb" download>Download the notebook ↗</a></div></main></div>
<footer class="site-footer"><span>END-TO-END MACHINE LEARNING</span><a class="portfolio-link" href="https://alvaradocss.com" target="_blank" rel="noopener noreferrer">Visit AlvaradoCSS.com <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 5h6v6M19 5l-9 9"/><path d="M19 13v6H5V5h6"/></svg></a><a href="#top">Back to top ↑</a></footer>
<script src="site.js" defer></script></body></html>'''
(site / "index.html").write_text(page, encoding="utf-8")
if notebook != site / 'ml_end2end.ipynb':
    shutil.copy2(notebook, site / 'ml_end2end.ipynb')
print('HTML size',len(page),'chapters',len(nav))
