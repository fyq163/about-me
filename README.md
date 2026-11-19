# About Me

My resume source and generated Markdown version.

[Download the latest one-page PDF from Releases](https://github.com/fyq163/about-me/releases/latest).

## Convert the resume to Markdown

The converter reads the structured LaTeX resume and keeps its section, position, and bullet hierarchy.

```bash
python3 latex_to_markdown.py
```

By default, it reads `main.tex` beside the script and writes `main.md` in the same directory. Input and output paths can also be supplied:

```bash
python3 latex_to_markdown.py input.tex output.md
```

## Build the PDF on GitHub

Open **Actions → Build resume PDF → Run workflow** and choose the branch to build. The workflow compiles the selected revision, checks that the PDF is one page, and publishes it as `Resume.pdf` in a new GitHub Release. It runs only when manually triggered.

You can also start it from the command line:

```bash
gh workflow run build-resume.yml --ref main
```

## Render the PDF locally

With `latexmk` and a LaTeX distribution installed, run:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
```
