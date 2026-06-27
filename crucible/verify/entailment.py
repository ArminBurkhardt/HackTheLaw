"""Bidirectional entailment oracle for SECV.

EntailmentOracle is a Protocol — injectable for testing.
ModelEntailmentOracle is the production implementation (Gemini Flash via ModelClient).
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from crucible.agents.base import ModelClient


_SYSTEM = """\
You are a strict legal entailment judge specialising in EU law.
Answer YES if the premise legally entails the hypothesis — meaning if the premise is true,
the hypothesis must also be true under EU law. Answer NO otherwise.
Be strict and literal. Respond with exactly one word: YES or NO.

Examples:
Premise: Art. 28(3) GDPR requires processing by a processor to be governed by a binding contract.
Hypothesis: There must be a written or electronic contract between controller and processor.
Answer: YES

Premise: Art. 28(3) GDPR governs processor contracts.
Hypothesis: Art. 28(3) GDPR requires data breach notification within 72 hours.
Answer: NO

Premise: Directive 95/46/EC was repealed by Regulation (EU) 2016/679 (GDPR).
Hypothesis: Directive 95/46/EC is no longer in force.
Answer: YES"""


@runtime_checkable
class EntailmentOracle(Protocol):
    def entails(self, premise: str, hypothesis: str) -> bool: ...


class ModelEntailmentOracle:
    """Calls ModelClient.generate for each entailment pair (strict few-shot prompt)."""

    def __init__(self, client: ModelClient, model: str) -> None:
        self._client = client
        self._model = model

    def entails(self, premise: str, hypothesis: str) -> bool:
        reply = self._client.generate(
            model=self._model,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Premise: {premise}\nHypothesis: {hypothesis}\nAnswer:",
            }],
        )
        return reply.strip().upper().startswith("YES")
