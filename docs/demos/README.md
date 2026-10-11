# Interactive demos

These static walkthroughs are designed for GitHub Pages and require no build step:

- `dipole-from-scratch/`: autonomous 5 T-class dipole construction, matching, and accepted-power-normalized B1⁺ validation;
- `paper-reproduction/`: 7 T fractionated-dipole paper translation, parameter studies, quantitative comparison, and evidence-bounded conclusions.

Serve the repository root locally before review:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/docs/`. Configure GitHub Pages to deploy from the `main` branch and `/docs` directory.

The source MP4 recordings are intentionally ignored by Git. Upload them as GitHub Release assets; the tracked 1280 × 720 GIFs in `docs/assets/` are optimized README previews. Publication-derived comparison panels must retain their bibliographic attribution and be redistributed only when permitted by the applicable source terms.
