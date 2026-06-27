"""SECV runtime wiring — connect verify_citation to the debrief.

Two jobs:
  1. extract_user_citations: find the legal authorities a trainee actually
     cited in their turns (matched to the playbook where possible, otherwise
     reconstructed so misattributed/fabricated cites can be caught).
  2. verify_authority / verify_debrief_citations: run SECV on those plus the
     coach's recommended authorities, sourcing provision text from CELLAR first
     and falling back to Perplexity (current-context commentary, score-capped).

SECV is expensive, so this runs ONLY at debrief — never inside a live turn
(spec §7.3). If neither CELLAR nor Perplexity is configured, verification is
skipped entirely (checks stay None) rather than emitting noisy "unverifiable"
verdicts.
"""
from __future__ import annotations
import re

from crucible.agents.base import ModelClient
from crucible.grounding.cellar.graph_store import GraphStore, InMemoryGraphStore
from crucible.grounding.perplexity import FakePerplexityClient, PerplexityClient
from crucible.grounding.source_policy import SourcePolicy
from crucible.schemas import Authority, CitationCheck, Debrief, Playbook
from crucible.verify.entailment import EntailmentOracle
from crucible.verify.secv import verify_citation


_GDPR_CELEX = "32016R0679"

# Corpus keywords → CELEX. Extend as the grounded sub-corpus grows.
_KEYWORD_CELEX: dict[str, str] = {
    "gdpr": _GDPR_CELEX,
    "dsgvo": _GDPR_CELEX,
}

# A legal citation: a marker (§ / Sec. / Art.) followed by a number, with an
# optional "(3)" subsection and optional "No. 7" component.
_CITATION_RE = re.compile(
    r"""
    (?P<marker>§{1,2}|art(?:icle|\.)?|sec(?:tion|\.)?)
    \s*
    (?P<num>\d+[a-z]?)
    (?:\s*\(\s*(?P<sub>\d+[a-z]?)\s*\))?
    (?:\s*no\.?\s*(?P<no>\d+))?
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Placeholder store for the Perplexity (celex=None) path, where verify_citation
# never touches the graph but still requires a store argument.
_EMPTY_STORE = InMemoryGraphStore()


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _known_authorities(playbook: Playbook) -> list[Authority]:
    seen: set[tuple[str | None, str | None]] = set()
    out: list[Authority] = []
    pools = [playbook.authorities] + [item.authorities for item in playbook.items]
    for pool in pools:
        for auth in pool:
            key = (auth.celex, auth.pinpoint)
            if key in seen:
                continue
            seen.add(key)
            out.append(auth)
    return out


def _authority_numbers(auth: Authority) -> set[str]:
    """The numeric signature of an authority's pinpoint, e.g. {'28', '28(3)'}."""
    if not auth.pinpoint:
        return set()
    m = re.search(r"(\d+[a-z]?)(?:\s*\(\s*(\d+[a-z]?)\s*\))?", auth.pinpoint)
    if not m:
        return set()
    main, sub = m.group(1), m.group(2)
    keys = {main}
    if sub:
        keys.add(f"{main}({sub})")
    return keys


def _candidate_keys(num: str, sub: str | None) -> set[str]:
    keys = {num}
    if sub:
        keys.add(f"{num}({sub})")
    return keys


def _corpus_celex(text: str, marker: str) -> str | None:
    low = text.lower()
    for keyword, celex in _KEYWORD_CELEX.items():
        if keyword in low:
            return celex
    return None


def _pinpoint_str(marker: str, num: str, sub: str | None, no: str | None) -> str:
    german = marker.startswith("§") or marker.lower().startswith("sec")
    head = "Sec." if german else "Art."
    s = f"{head} {num}"
    if sub:
        s += f"({sub})"
    if no:
        s += f" No. {no}"
    return s


def _match_known(known: list[Authority], num: str, sub: str | None) -> Authority | None:
    keys = _candidate_keys(num, sub)
    for auth in known:
        if _authority_numbers(auth) & keys:
            return auth
    return None


def extract_user_citations(
    transcript: list[dict],
    playbook: Playbook,
) -> list[tuple[Authority, str]]:
    """Find legal authorities the trainee cited, paired with the claim sentence.

    Cites that match a playbook authority reuse that (richer) Authority; cites
    that don't are reconstructed as bare Authorities so SECV can still flag a
    fabricated identifier or a misattributed pinpoint.
    """
    known = _known_authorities(playbook)
    results: list[tuple[Authority, str]] = []
    seen: set[tuple[str | None, str | None]] = set()

    for msg in transcript:
        if msg.get("role") != "user":
            continue
        text = str(msg.get("content", "")).strip()
        # Match over the whole message: legal abbreviations ("Sec.", "Art.",
        # "No.") would otherwise be split mid-citation by sentence boundaries.
        for m in _CITATION_RE.finditer(text):
            num = m.group("num")
            sub = m.group("sub")
            no = m.group("no")
            marker = m.group("marker")

            auth = _match_known(known, num, sub)
            if auth is None:
                celex = _corpus_celex(text, marker)
                pinpoint = _pinpoint_str(marker, num, sub, no)
                auth = Authority(
                    title=f"Cited authority — {pinpoint}",
                    celex=celex,
                    pinpoint=pinpoint,
                    source="cellar" if celex else "firm_playbook",
                )

            key = (auth.celex, auth.pinpoint)
            if key in seen:
                continue
            seen.add(key)
            results.append((auth, text))

    return results


# ---------------------------------------------------------------------------
# Provision-text sourcing + verification
# ---------------------------------------------------------------------------

def _has_perplexity(client: PerplexityClient | None) -> bool:
    return client is not None and not isinstance(client, FakePerplexityClient)


def _provision_text_via_perplexity(
    auth: Authority,
    perplexity: PerplexityClient,
    policy: SourcePolicy | None,
) -> str | None:
    label = auth.pinpoint or auth.title
    query = (
        f"Quote the full official text of {label} ({auth.title}). "
        "Return the verbatim statutory wording only."
    )
    if policy:
        query += " Use only official legal sources from: " + ", ".join(policy.allowed_domains)
    try:
        results = perplexity.search(query, max_results=3)
    except Exception:
        return None
    snippets = [
        r.snippet for r in results
        if r.snippet and (policy.allows(r.url) if policy else True)
    ]
    text = "\n".join(snippets).strip()
    return text or None


def verify_authority(
    auth: Authority,
    claim: str,
    *,
    store: GraphStore | None = None,
    perplexity: PerplexityClient | None = None,
    policy: SourcePolicy | None = None,
    model_client: ModelClient,
    model: str,
    entailment_oracle: EntailmentOracle | None = None,
    M: int = 4,
    theta_high: float = 0.7,
    cache: dict[str, CitationCheck] | None = None,
) -> CitationCheck:
    """Verify one authority, sourcing provision text from CELLAR then Perplexity.

    CELLAR is authoritative (black-letter law). If CELLAR resolves the work but
    has no provision text and Perplexity is available, fall back to it. Non-CELEX
    authorities go straight to Perplexity (verify_citation caps their score).
    """
    common = dict(
        model_client=model_client,
        model=model,
        entailment_oracle=entailment_oracle,
        M=M,
        theta_high=theta_high,
        cache=cache,
    )

    if auth.celex and store is not None:
        check = verify_citation(claim, auth.celex, auth.pinpoint, store=store, **common)
        if (
            check.status == "weak"
            and "no provision text" in check.note
            and _has_perplexity(perplexity)
        ):
            text = _provision_text_via_perplexity(auth, perplexity, policy)  # type: ignore[arg-type]
            if text:
                return verify_citation(
                    claim, None, auth.pinpoint,
                    store=_EMPTY_STORE, provision_text_override=text, **common,
                )
        return check

    text = (
        _provision_text_via_perplexity(auth, perplexity, policy)  # type: ignore[arg-type]
        if _has_perplexity(perplexity)
        else None
    )
    return verify_citation(
        claim, None, auth.pinpoint,
        store=_EMPTY_STORE, provision_text_override=text, **common,
    )


def verify_debrief_citations(
    debrief: Debrief,
    transcript: list[dict],
    playbook: Playbook,
    *,
    store: GraphStore | None = None,
    perplexity: PerplexityClient | None = None,
    policy: SourcePolicy | None = None,
    model_client: ModelClient,
    model: str,
    entailment_oracle: EntailmentOracle | None = None,
    M: int = 4,
) -> None:
    """Populate Authority.check on the debrief's recommended authorities and on
    the trainee's own citations. Mutates `debrief` in place.

    No-ops when no verification source is configured, so an unconfigured demo
    shows clean (unbadged) authorities rather than "unverifiable" everywhere.
    """
    if store is None and not _has_perplexity(perplexity):
        return

    cache: dict[str, CitationCheck] = {}
    common = dict(
        store=store, perplexity=perplexity, policy=policy,
        model_client=model_client, model=model,
        entailment_oracle=entailment_oracle, M=M, cache=cache,
    )

    for auth in debrief.stronger_move_authorities:
        try:
            auth.check = verify_authority(auth, debrief.stronger_move, **common)
        except Exception:
            pass  # a single bad citation must never sink the debrief

    user_citations: list[Authority] = []
    for auth, claim in extract_user_citations(transcript, playbook):
        try:
            auth.check = verify_authority(auth, claim, **common)
        except Exception:
            pass
        user_citations.append(auth)
    debrief.user_citations = user_citations
