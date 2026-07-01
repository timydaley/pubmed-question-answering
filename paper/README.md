# PubMedQA v1 local evidence baseline report

This directory uses the ICML 2026 LaTeX template files copied from:

`/Users/timothydaley/personal_projects/mtga_cube_draft_finetune/paper/`

Build:

```bash
/Library/TeX/texbin/pdflatex -interaction=nonstopmode pubmedqa_v4_baseline_icml2026.tex
/Library/TeX/texbin/bibtex pubmedqa_v4_baseline_icml2026
/Library/TeX/texbin/pdflatex -interaction=nonstopmode pubmedqa_v4_baseline_icml2026.tex
/Library/TeX/texbin/pdflatex -interaction=nonstopmode pubmedqa_v4_baseline_icml2026.tex
```

Primary output:

`pubmedqa_v4_baseline_icml2026.pdf`

Note: the filename is retained for continuity with the earlier v4 draft, but the paper content now describes the current v1-oriented citation+recency retrieval, Evidence basis answer benchmark, build-integrity reporting, and release gates.
