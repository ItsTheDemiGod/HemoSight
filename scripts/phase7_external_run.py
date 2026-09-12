"""Phase 7 Task 3B - attempt to run the one external repository with released code.

SCOPE, STATED FIRST. The repository (mbedmutha/anemia-detection, cloned to
C:\\Users\\demia\\Desktop\\anemia-detection-main) is a three-person student project
with 18 commits, zero stars, self-described as "initial experiments". It is NOT a
published paper and is NOT evidence about the published literature. Its role here
is solely to test whether the harness's external path can ingest and audit released
code. Nothing below generalises.

RULES. The cloned repository is not modified. Each notebook is COPIED and executed in
an isolated environment (C:\\Users\\demia\\Desktop\\anemia-detection-env, not the
HemoSight venv) with exactly two kinds of change, both recorded per notebook:
  1. data-path repointing: string substitutions of the authors' local/Drive paths to
     this project's Eyes-Defy copy (and a directory junction so their relative path
     `dataset_anemia/` resolves to the dataset folder, whose real name has a space);
  2. Google-Colab `drive.mount` cells skipped, because the data now lives on local
     disk - this is treated as part of path repointing and is the ONLY cell-level
     allowance. No other line of their code is touched.
If a notebook fails, the first error is recorded and execution stops on that notebook.
Whether a released artefact runs is part of the availability finding.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(r"C:\Users\demia\Desktop\anemia-detection-main")
ENV_PY = Path(r"C:\Users\demia\Desktop\anemia-detection-env\Scripts\python.exe")
HS = Path(__file__).resolve().parents[1]
DATASET = HS / "data" / "raw" / "dataset anemia"
WORK = HS / "data" / "interim" / "phase7" / "external" / "anemia-detection"
TIMEOUT_S = 900

# Authors' paths -> this project's copy. Only these strings are substituted.
INDIA_XLSX = str(DATASET / "India" / "India.xlsx")
ITALY_XLSX = str(DATASET / "Italy" / "Italy.xlsx")
SUBS = [
    (r"/content/drive/MyDrive/Project/dataset_anemia/India/India.xlsx", INDIA_XLSX),
    (r"/content/drive/MyDrive/Spring 2022/Machine Learning for Physical Applications/Project/dataset_anemia/India/India.xlsx", INDIA_XLSX),
    (r"/home/ssaoji/228_Project/dataset_anemia/India/India.xlsx", INDIA_XLSX),
    # The authors load cleaned copies of the Italy sheet (Italy_new.xlsx, Italy_copy.xlsx)
    # that are not in the repository or the dataset; the dataset's own Italy.xlsx is the
    # nearest available file and is substituted, with the substitution recorded.
    (r"/content/drive/MyDrive/Project/TRIAL/Italy_new.xlsx", ITALY_XLSX),
    (r"/content/drive/MyDrive/Spring 2022/Machine Learning for Physical Applications/Project/TRIAL/Italy_new.xlsx", ITALY_XLSX),
    (r"/home/ssaoji/228_Project/dataset_anemia/Italy/Italy_copy.xlsx", ITALY_XLSX),
    (r"/content/drive/MyDrive/Project/dataset_anemia/India/", str(DATASET / "India") + "/"),
    (r"/content/drive/MyDrive/Project/dataset_anemia/Italy/", str(DATASET / "Italy") + "/"),
    (r"/content/drive/MyDrive/Spring 2022/Machine Learning for Physical Applications/Project/dataset_anemia/India/", str(DATASET / "India") + "/"),
    (r"/content/drive/MyDrive/Spring 2022/Machine Learning for Physical Applications/Project/dataset_anemia/Italy/", str(DATASET / "Italy") + "/"),
    # Their preprocessed arrays live beside the notebooks on the authors' machines; point
    # the directory at the working folder so a FileNotFoundError names the artefact.
    ("C:\\Users\\manas\\Documents\\Winter 2022\\Digital Health Systems\\Project\\anemia_detection\\", str(WORK / "authors_intermediates") + "/"),
    (r"/home/ssaoji/228_Project/Aug_Seg/Augmented_Segmented_data/", str(WORK / "authors_intermediates" / "Augmented_Segmented_data") + "/"),
]
NOTEBOOKS = ["baselines/hue_score_svm.ipynb", "baselines/mean_ann.ipynb",
             "experiments/visualize.ipynb", "experiments/xgboost_linreg.ipynb",
             "experiments/vanilla_cnn.ipynb", "experiments/transfer-learning/training.ipynb",
             "experiments/transfer-learning/learning.ipynb"]


def prepare(nb_rel: str) -> tuple[Path, dict]:
    src = json.loads((REPO / nb_rel).read_text(encoding="utf-8"))
    record = {"notebook": nb_rel, "substitutions": [], "skipped_cells": []}
    for i, c in enumerate(src["cells"]):
        if c["cell_type"] != "code":
            continue
        text = "".join(c["source"])
        for a, b in SUBS:
            if a in text:
                # Forward slashes: valid on Windows and safe inside non-raw string literals.
                text = text.replace(a, b.replace("\\", "/"))
                record["substitutions"].append({"cell": i, "from": a, "to": b})
        if "google.colab" in text or "drive.mount" in text:
            record["skipped_cells"].append({"cell": i, "reason": "Google Colab drive mount; data is local"})
            text = "# [skipped by the audit runner: Colab drive mount]\n"
        c["source"] = text
        c["outputs"] = []
        c["execution_count"] = None
    out = WORK / "runs" / nb_rel.replace("/", "__")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(src, indent=1), encoding="utf-8")
    return out, record


def execute(nb_path: Path, cwd: Path) -> dict:
    """Run with nbclient in the isolated env; return first error and where it happened."""
    runner = f'''
import json, sys, traceback
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError
import nbformat
nb = nbformat.read(r"{nb_path}", as_version=4)
client = NotebookClient(nb, timeout={TIMEOUT_S}, kernel_name="python3", allow_errors=False,
                        resources={{"metadata": {{"path": r"{cwd}"}}}})
res = {{"completed": False, "failed_cell": None, "error": None, "cells_run": 0}}
try:
    client.execute()
    res["completed"] = True
except CellExecutionError as e:
    s = str(e)
    res["error"] = s[-1500:]
except CellTimeoutError as e:
    res["error"] = "TIMEOUT: " + str(e)[-500:]
except Exception as e:
    res["error"] = "RUNNER: " + repr(e)[-800:]
# count executed cells and locate the failure from the notebook state
ran = 0; failed = None
for i, c in enumerate(nb.cells):
    if c.cell_type != "code": continue
    if c.get("execution_count"): ran += 1
    if any(o.get("output_type") == "error" for o in c.get("outputs", [])) and failed is None:
        failed = {{"index": i, "source": "".join(c.source)[:600],
                  "ename": [o for o in c.outputs if o.get("output_type") == "error"][0].get("ename"),
                  "evalue": [o for o in c.outputs if o.get("output_type") == "error"][0].get("evalue", "")[:600]}}
res["cells_run"] = ran; res["failed_cell"] = failed
nbformat.write(nb, r"{nb_path}")
print(json.dumps(res))
'''
    p = subprocess.run([str(ENV_PY), "-c", runner], capture_output=True, text=True,
                       timeout=TIMEOUT_S + 120, cwd=str(cwd))
    line = [l for l in p.stdout.splitlines() if l.startswith("{")]
    if not line:
        return {"completed": False, "error": "RUNNER produced no result: " + (p.stderr[-1500:] or p.stdout[-500:]),
                "failed_cell": None, "cells_run": 0}
    return json.loads(line[-1])


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "authors_intermediates").mkdir(exist_ok=True)   # deliberately EMPTY: nothing was released
    # Directory junction so the authors' relative `dataset_anemia/` resolves (path repoint).
    cwd = WORK / "cwd"
    cwd.mkdir(exist_ok=True)
    link = cwd / "dataset_anemia"
    if not link.exists():
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(DATASET)], capture_output=True)
    env_probe = subprocess.run([str(ENV_PY), "-c", "import torch,tensorflow,xgboost,sklearn,cv2;print('ok')"],
                               capture_output=True, text=True)
    results = {"scope": ("student repository, NOT a published paper; used only to test the "
                         "harness's external path; nothing generalises"),
               "environment": {"python": str(ENV_PY), "requirements_txt_installs_as_written": False,
                               "requirements_txt_failure": "pip: No matching distribution found for glob "
                                                           "(glob and pathlib are stdlib, not packages)",
                               "installed_subset_ok": env_probe.stdout.strip() == "ok",
                               "torch_cuda_available": False,
                               "note": "CPU torch; every notebook fails before any .cuda() call"},
               "rules": ["cloned repo untouched; copies executed", "data paths repointed only",
                         "Colab drive-mount cells skipped (the only cell-level allowance)",
                         "stop at the first error; no code repaired"],
               "notebooks": []}
    for rel in NOTEBOOKS:
        t0 = time.time()
        nb_path, rec = prepare(rel)
        r = execute(nb_path, cwd)
        rec.update(r)
        rec["seconds"] = round(time.time() - t0, 1)
        results["notebooks"].append(rec)
        fc = rec.get("failed_cell") or {}
        print(f"{rel}: completed={rec['completed']} cells_run={rec['cells_run']} "
              f"first_error={fc.get('ename')}: {str(fc.get('evalue', rec.get('error', '')))[:160]}")
    n = len(results["notebooks"]); done = sum(1 for r in results["notebooks"] if r["completed"])
    results["summary"] = {"notebooks": n, "ran_to_completion": done,
                          "produced_per_subject_predictions": 0 if done == 0 else None}
    (WORK / "run_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n{done} of {n} notebooks ran to completion. results -> {WORK / 'run_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
