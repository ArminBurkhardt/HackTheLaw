"""FORMEX XML → :Provision rows.

EUR-Lex serves legislative texts in FORMEX 4 format. This module
extracts articles (ARTICLE elements with TITRE/TI.ART headings) and
their plain text content.

Runtime rule: ingest-only. Runtime agents never import this module.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProvisionRow:
    celex: str
    provision_id: str
    article_no: str
    heading: str
    text: str


def extract_provisions(celex: str, formex_path: Path) -> list[ProvisionRow]:
    """Parse a FORMEX XML file and return a list of ProvisionRows."""
    try:
        from lxml import etree  # type: ignore[import]
    except ImportError as e:
        raise ImportError("lxml is required for FORMEX parsing: pip install lxml") from e

    tree = etree.parse(str(formex_path))
    root = tree.getroot()

    # FORMEX namespace varies; strip it when matching
    def _tag(el) -> str:
        return el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag

    rows: list[ProvisionRow] = []
    for art in root.iter():
        if _tag(art) not in ("ARTICLE", "ARTICLE.TBL"):
            continue

        # Article number from NUM or TI.ART child
        article_no = ""
        heading = ""
        for child in art:
            t = _tag(child)
            if t == "NUM":
                article_no = (child.text or "").strip()
            elif t in ("TI.ART", "TITRE"):
                heading = "".join(child.itertext()).strip()

        if not article_no:
            continue

        text = " ".join(art.itertext()).strip()
        # Deduplicate whitespace
        import re
        text = re.sub(r"\s+", " ", text)

        provision_id = f"{celex}-{article_no.replace(' ', '_').replace('(', '').replace(')', '')}"
        rows.append(ProvisionRow(
            celex=celex,
            provision_id=provision_id,
            article_no=article_no,
            heading=heading,
            text=text,
        ))

    return rows
