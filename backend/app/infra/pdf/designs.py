"""Los diseños de CV en disco (A25): `templates/cv/<diseño>/` con `manifest.json`,
`template.html`, `style.css` y `fonts/`, y las etiquetas fijas por idioma en
`templates/cv/labels/<idioma>.json` (RF-106)."""

import json
from functools import cache
from pathlib import Path
from typing import Any

from app.domain.cv import CvDesign

CV_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "cv"
_LABELS_DIR = "labels"
_MANIFEST = "manifest.json"


class CvDesignCatalog:
    """Los diseños y etiquetas de una carpeta. Se leen una vez: cambian con un
    despliegue, no en marcha."""

    def __init__(self, root: Path = CV_TEMPLATES_DIR) -> None:
        self.root = root

    def designs(self) -> dict[str, CvDesign]:
        return _load_designs(self.root)

    def design_dir(self, key: str) -> Path:
        return self.root / key

    def labels(self, language: str) -> dict[str, Any]:
        return _load_labels(self.root, language)


@cache
def _load_designs(root: Path) -> dict[str, CvDesign]:
    designs: dict[str, CvDesign] = {}
    for manifest_path in sorted(root.glob(f"*/{_MANIFEST}")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        key = manifest_path.parent.name
        designs[key] = CvDesign(
            key=key,
            names=manifest["name"],
            descriptions=manifest["description"],
            languages=tuple(manifest["languages"]),
            ats_friendly=bool(manifest["ats_friendly"]),
        )
    return designs


@cache
def _load_labels(root: Path, language: str) -> dict[str, Any]:
    labels: dict[str, Any] = json.loads(
        (root / _LABELS_DIR / f"{language}.json").read_text(encoding="utf-8")
    )
    return labels
