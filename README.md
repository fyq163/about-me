# About Me

My resume source and generated Markdown version.

[Download the one-page PDF](main.pdf).

## Convert the resume to Markdown

The converter reads the structured LaTeX resume and keeps its section, position, and bullet hierarchy.

```bash
python3 latex_to_markdown.py
```

By default, it reads `main.tex` beside the script and writes `main.md` in the same directory. Input and output paths can also be supplied:

```bash
python3 latex_to_markdown.py input.tex output.md
```

## Render the PDF

With `latexmk` and a LaTeX distribution installed, run:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
```
