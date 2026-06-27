"""Stream CELLAR RDF/N-Triples dump → (node_row, edge_row) iterators.

Uses lxml iterparse for low-memory streaming (the CELLAR sector-3 dump
is multi-GB). Handles both NTriples (.nt) and RDF/XML (.rdf / .xml).

Runtime rule: this module is INGEST-ONLY. Runtime agents never import it.
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# Row types (plain dicts — no Pydantic overhead at ingest time)
# ---------------------------------------------------------------------------

WorkRow = dict  # keys: cellar_uuid, celex, eli, title, type, sector, date_document
EdgeRow = dict  # keys: from_celex, to_celex, edge_type


def stream_ntriples(path: Path) -> Iterator[tuple[str, str, str]]:
    """Yield (subject, predicate, object) triples from an .nt file.

    Handles <URI> and "literal"^^type forms. Skips malformed lines.
    """
    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(" ."):
                line = line[:-2].strip()
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            s, p, o = parts[0], parts[1], parts[2]
            # Strip angle brackets from URIs
            s = s.strip("<>")
            p = p.strip("<>")
            o = o.strip()
            yield s, p, o


def stream_rdf_xml(path: Path) -> Iterator[tuple[str, str, str]]:
    """Yield (subject, predicate, object) triples from an RDF/XML file.

    Uses lxml iterparse to avoid loading the entire file into memory.
    Only imports lxml inside this function so it is optional at test time.
    """
    try:
        from lxml import etree  # type: ignore[import]
    except ImportError as e:
        raise ImportError("lxml is required for RDF/XML parsing: pip install lxml") from e

    RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    context = etree.iterparse(str(path), events=("end",), tag=f"{{{RDF}}}Description")
    for _event, elem in context:
        subject = elem.get(f"{{{RDF}}}about") or elem.get(f"{{{RDF}}}nodeID", "")
        for child in elem:
            predicate = child.tag  # Clark notation {ns}local
            # Normalise Clark → URI
            predicate_uri = (
                predicate.replace("{", "").replace("}", "/")
                if predicate.startswith("{")
                else predicate
            )
            obj_uri = child.get(f"{{{RDF}}}resource")
            if obj_uri:
                yield subject, predicate_uri, obj_uri
            elif child.text and child.text.strip():
                yield subject, predicate_uri, child.text.strip()
        elem.clear()


def triples_to_work_rows(
    triples: Iterator[tuple[str, str, str]],
    scope_celexes: set[str] | None = None,
) -> Iterator[WorkRow]:
    """Fold CDM triples about a subject into WorkRow dicts.

    Buffers triples by subject; emits a WorkRow when the buffer for a
    CELEX-bearing subject is complete. scope_celexes filters output to
    only the requested CELEX numbers (None = all).
    """
    from crucible.grounding.cellar.cdm_mapping import predicate_to_edge_type

    _CDM = "http://publications.europa.eu/ontology/cdm#"
    _CELEX_PRED = f"{_CDM}work_has_resource-type_eurovoc_concept.0.identifier"
    _ELI_PRED = f"{_CDM}work_id_document_eli"
    _TITLE_PRED = "http://purl.org/dc/terms/title"
    _TYPE_PRED = f"{_CDM}work_has_resource-type.0.identifier"
    _DATE_PRED = f"{_CDM}work_date_document"
    _UUID_PRED = "http://publications.europa.eu/ontology/cdm#uuid"

    buf: dict[str, dict] = {}

    def _flush(subj: str) -> WorkRow | None:
        d = buf.pop(subj, {})
        celex = d.get("celex")
        if not celex:
            return None
        if scope_celexes and celex not in scope_celexes:
            return None
        return {
            "cellar_uuid": d.get("uuid", subj),
            "celex": celex,
            "eli": d.get("eli"),
            "title": d.get("title", ""),
            "type": d.get("type", ""),
            "sector": celex[0] if celex else "",
            "date_document": d.get("date_document", ""),
        }

    prev_subj = None
    for subj, pred, obj in triples:
        if subj != prev_subj:
            if prev_subj is not None and prev_subj in buf:
                row = _flush(prev_subj)
                if row:
                    yield row
            prev_subj = subj

        entry = buf.setdefault(subj, {})
        if _CELEX_PRED in pred or "celex" in pred.lower():
            entry["celex"] = obj
        elif _ELI_PRED in pred or "eli" in pred.lower():
            entry["eli"] = obj
        elif _TITLE_PRED in pred:
            entry.setdefault("title", obj)
        elif _TYPE_PRED in pred or "resource-type" in pred.lower():
            entry.setdefault("type", obj.rsplit("/", 1)[-1])
        elif _DATE_PRED in pred:
            entry["date_document"] = obj[:10]
        elif _UUID_PRED in pred:
            entry["uuid"] = obj

    if prev_subj and prev_subj in buf:
        row = _flush(prev_subj)
        if row:
            yield row
