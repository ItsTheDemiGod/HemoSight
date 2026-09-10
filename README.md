# HemoSight

Non-invasive anemia screening: estimating blood hemoglobin (g/dL) from ordinary
photographs of the palpebral conjunctiva, palm and fingernail, optionally fused
with fingertip PPG.

The core bet is that the photograph is a **spectroscopic measurement**, not pixels
for a CNN. HemoSight recovers a reflectance spectrum from RGB, unmixes it into
chromophore concentrations (hemoglobin, oxyhemoglobin, melanin), and reports
hemoglobin with a calibrated uncertainty interval.

> **This is a research project. It is a screening aid, not a diagnostic device,
> and it has never been clinically validated.**

## Source of truth

**[CLAUDE.md](CLAUDE.md) governs this repository.** It holds the novelty claims,
the hard constraints, the dataset inventory, the phase plan, and the decision and
results logs. Read it before doing any work here. Nothing in this README overrides it.

## Quick start (Windows)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Layout

| Path | Purpose |
| --- | --- |
| `data/raw/` | Public datasets, **read-only, never modified, never committed** |
| `data/interim/`, `data/processed/`, `data/synthetic/` | Derived data, all regenerable |
| `src/hemosight/` | Library code, one submodule per novelty claim |
| `configs/` | Experiment configuration |
| `scripts/` | Runnable entry points |
| `notebooks/` | Exploration only; findings graduate into `src/` and the logs |
| `reports/` | Figures and tables for the write-up |
| `web/` | FastAPI + React application (Phase 9) |
| `mobile/` | Flutter application (Phase 10) |
