"""Phase 9B - literature methodology audit, widened to every full text obtained.

Writes data/interim/phase9b/literature_audit.json from the scoring in
`hemosight.audit.literature`, then regenerates reports/literature_gap.md through the
Phase 5 generator, which embeds the Phase 9B section. The scoring itself is data in the
module: seven full texts in data/raw/literature/, read in full on 2026-09-20.

    .\\.venv\\Scripts\\python.exe scripts\\literature_methodology_audit_phase9b.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hemosight.audit import literature as lit
from hemosight.io import paths


def main() -> int:
    out_dir = paths.INTERIM / "phase9b"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = lit.to_json()
    (out_dir / "literature_audit.json").write_text(json.dumps(data, indent=2),
                                                    encoding="utf-8")
    print(f"wrote {out_dir / 'literature_audit.json'}")
    c = data["counts"]
    ob = data["obtainability"]
    print(f"full texts read: {data['n_full_text']}; multi-site: {data['n_multi_site']}; "
          f"identified {ob['identified']}, obtained {ob['full_text_obtained']}")
    for k, v in c.items():
        print(f"  {k:24s} YES {v['YES']}  NOT REPORTED {v['NOT REPORTED']}  "
              f"UNKNOWN {v['UNKNOWN']}  N/A {v['NOT APPLICABLE']}")

    # Regenerate the report through the Phase 5 generator so there is one writer.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import dataset_manifest_and_literature_phase5  # noqa: E402
    return dataset_manifest_and_literature_phase5.main()


if __name__ == "__main__":
    raise SystemExit(main())
