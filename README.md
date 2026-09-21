# HemoSight

**A negative-results study.** HemoSight asked whether blood haemoglobin can be estimated
from an ordinary photograph of the eyelid, or from fingertip PPG, well enough to screen
for anaemia. **Six representations across two modalities were tested against thresholds
declared before each experiment ran. None produced a usable estimator.**

> **The benchmark that beat every one of them is a single binary variable: the subject's
> sex, MAE 0.831 g/dL.**

The project's contribution is that body of negative results, the measured mechanism
behind each one, and a reusable audit harness that applies the same checks to anyone
else's screening model.

> ⚠️ **Research only. Nothing here is a diagnostic device and nothing here has been
> clinically validated.** All evaluation is retrospective, on public datasets.

## What was found

| # | modality | representation | verdict | key number |
| --- | --- | --- | --- | --- |
| 1 | Imaging | Sclera as an absolute white reference | **REFUTED** | 7.43 dE2000 vs grey-world's 6.08 |
| 2 | Imaging | Corneal specular highlight | **REFUTED** | no better than the sclera, p = 0.29 |
| 3 | Imaging | Absolute colorimetric Hb inversion | **NOT RECOVERABLE** | 3.89 g/dL, 95% [2.37, 8.02], against a 2.0 g/dL gate |
| 4 | Imaging | Illuminant-free within-image ratio | **REFUTED** | 10.04 g/dL equivalent |
| 5 | PPG | AC/DC + ratio-of-ratios features | **NOT VIABLE** | R² −0.025; permutation p = 0.978 |
| 6 | PPG | Raw waveform, 3 deep architectures | **NOT VIABLE** | best MAE 1.113 vs sex alone at 0.831 |
| 7 | Imaging | Conventional CNN baseline (the comparison arm) | **MARGINAL** | MAE 1.301; site + sex + age alone 1.273 |

**One genuine positive, precisely bounded.** A spectrogram CNN on raw 660 nm PPG is
distinguishable from chance — z = −4.96, empirical p ≤ 0.0041 — and improves on
predicting a constant by about **0.05 g/dL**. Real, significant, and clinically useless.
Writing "deep learning found nothing" would be false; writing "deep learning worked"
would be far more false.

**Two findings worth more than the verdicts.** Re-scored as the referral decision a
product actually makes, the image *does* beat demographics **within a site** (+0.192
specificity at matched sensitivity) — and then collapses **across** sites, flagging 27
of 68 anaemic subjects and missing 41. And a demographics-only baseline, which **0 of
the 7 papers we read full-text report**, is what separates a haemoglobin estimator from
a sex classifier.

**What we could and could not have detected.** The regression arms are adequately
powered (MDE 0.18 and 0.14 g/dL against a 1.0 g/dL clinical band), so those negatives
are informative. The cross-site comparison — the project's most load-bearing finding —
is its least powered. Both are stated plainly rather than only the convenient one.

Full detail: **[`reports/final_results.md`](reports/final_results.md)**. Every metric,
including the failures, is in [`docs/archive/results_log.md`](docs/archive/results_log.md).

## What ships

**HemoSight Audit** — not an estimator, but the methodological audit harness the gates
above were run with, generalised to operate on any claimed screening model's predictions.
Give it a predictions table and it returns eight checks, each PASS / FAIL / **INSUFFICIENT
DATA**, with the measured quantity and a plain-language explanation.

* Library: [`src/hemosight/audit/`](src/hemosight/audit/) · Application: [`app/`](app/)
  (FastAPI + React) · Report: [`reports/phase6_audit_harness.md`](reports/phase6_audit_harness.md)

## Source of truth

**[CLAUDE.md](CLAUDE.md) governs this repository** — the claims, the hard constraints,
the dataset inventory, the phase plan and the current state. The evidentiary record (every
decision, every result, every correction and every pre-declaration, verbatim and
append-only) is in **[`docs/archive/`](docs/archive/)**. Nothing in this README overrides
either.

## Setup (Windows, Python 3.12)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# PyTorch MUST come from the CUDA index. The default PyPI index serves a CPU-only
# wheel on Windows, which silently disables the GPU.
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

pip install -e ".[dev]"
python scripts\check_gpu.py   # must report cuda.is_available() = True
pytest                        # 235 tests
```

If `pip install -e ".[dev]"` reports that `torch==2.14.0+cu126` cannot be found, the CUDA
step above was skipped. That failure is deliberate — see the comment in `pyproject.toml`.

## Getting the data

**No data is in this repository and none ever will be.** `data/` is gitignored and a test
([`test_no_dataset_files_are_tracked_by_git`](tests/test_phase5.py)) fails the suite if a
dataset file is ever staged.

**[`reports/dataset_manifest.md`](reports/dataset_manifest.md)** lists all ten sources
with a download URL, the verified licence status and how to obtain each one — **38.1 GB
across 40,831 files**. Read it before downloading: **none of the ten ships a licence
file**, four are CC BY 4.0, two are custom agreements that forbid redistribution and
require a signed access form, and two state no licence at all. Place each under
`data/raw/` using the folder names the manifest gives; `src/hemosight/io/paths.py`
resolves everything from the repository root.

## Reproducing the results

```powershell
.\.venv\Scripts\python.exe scripts\reproduce_all.py --list   # the plan, with runtimes
.\.venv\Scripts\python.exe scripts\reproduce_all.py --fast   # ~10 min, skips slow stages
.\.venv\Scripts\python.exe scripts\reproduce_all.py          # ~12 h, everything
```

Every stage is deterministic given the frozen seed (20260911), with two documented
exceptions the script names. Verified after a clean `--fast` run: the Phase 3 gate MAE
(3.893), the PPG four-wavelength MAE (1.190), the sex-alone baseline (0.831) and the
permutation p (0.978) all reproduce exactly.

## Layout

| Path | Purpose |
| --- | --- |
| `CLAUDE.md` | Governs the repository: claims, constraints, phase plan, current state |
| `docs/archive/` | The evidentiary record — decision log, results log, corrections, superseded claims, pre-declarations |
| `data/` | Datasets and derived artefacts. **Gitignored in full; `data/raw/` is read-only** |
| `src/hemosight/` | Library code — calibration, simulation, ppg, evaluation, audit |
| `scripts/` | Runnable entry points, one or more per phase; `reproduce_all.py` runs them in order |
| `reports/` | Every report, generated from the artefacts so the numbers cannot drift. `reports/figures/` is gitignored |
| `app/` | HemoSight Audit — FastAPI backend and React front end |
| `configs/`, `tests/`, `notebooks/` | Configuration, 235 tests, exploration |

## Licence

Code is **MIT** — see [LICENSE](LICENSE). **The licence covers this project's code only.**
Every dataset remains under its own terms, several of which are unverified or forbid
redistribution, and **no dataset is redistributed here**. See
[`reports/dataset_manifest.md`](reports/dataset_manifest.md) and
[`reports/phase1_dataset_licences.md`](reports/phase1_dataset_licences.md).
