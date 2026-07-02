"""
Winter AI - Decision Engine ("Scheme layer")
A small forward-chaining production rule system, inspired by Scheme/Lisp
`cond` expressions. Rules are plain data (JSON), loaded at startup, so the
"brain" can be retrained/extended by editing decision_rules.json without
touching any code.

Each rule is evaluated in order (like a Scheme `cond` clause list). The
first rule whose condition matches the input "fires" and determines the
conversational intent, which downstream layers use to decide how to answer.

We also render the decision as a literal S-expression string, e.g.:

    (cond
      ((matches? input '(hello hi hey)) 'greeting)
      ((matches? input '(thank thanks merci)) 'thanks)
      (else 'knowledge-query))
    => 'greeting

so the reasoning is inspectable, auditable, and genuinely symbolic rather
than a black box.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .retrieval import tokenize

POSITIVE_WORDS = {
    "good", "great", "awesome", "love", "excellent", "happy", "amazing",
    "bon", "bien", "génial", "super", "meza", "byiza", "murakoze",
}
NEGATIVE_WORDS = {
    "bad", "terrible", "hate", "angry", "sad", "broken", "awful",
    "mauvais", "mal", "triste", "mbi", "bibi",
}


@dataclass
class Rule:
    rule_id: str
    intent: str
    any_words: list[str]
    priority: int = 0
    is_default: bool = False


class DecisionEngine:
    def __init__(self, rules_path: Path):
        self.rules_path = rules_path
        self.rules: list[Rule] = []
        self.reload()

    def reload(self) -> None:
        raw = json.loads(self.rules_path.read_text(encoding="utf-8"))
        rules = []
        for r in raw:
            cond = r.get("if", {})
            rules.append(Rule(
                rule_id=r.get("id", "r?"),
                intent=r.get("intent", "unknown"),
                any_words=[w.lower() for w in cond.get("any_words", [])],
                priority=r.get("priority", 0),
                is_default=bool(cond.get("default", False)),
            ))
        # Sort by priority (desc), keep default rule(s) last regardless of priority
        rules.sort(key=lambda r: (r.is_default, -r.priority))
        self.rules = rules

    def sentiment(self, tokens: list[str]) -> str:
        toks = set(tokens)
        pos = len(toks & POSITIVE_WORDS)
        neg = len(toks & NEGATIVE_WORDS)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

    def infer(self, prompt: str) -> dict:
        """Forward-chain over the rule base and return the fired intent,
        plus a literal Scheme S-expression trace of the reasoning."""
        lower = prompt.lower()
        tokens = tokenize(prompt)

        sexpr_lines = ["(cond"]
        fired_rule: Rule | None = None

        for rule in self.rules:
            if rule.is_default:
                sexpr_lines.append("  (else 'knowledge-query))")
                continue
            word_list = " ".join(f"'{w.replace(' ', '-')}" for w in rule.any_words)
            clause = f"  ((matches? input '({word_list})) '{rule.intent})"
            sexpr_lines.append(clause)
            if fired_rule is None and any(w in lower for w in rule.any_words):
                fired_rule = rule

        if fired_rule is None:
            fired_rule = next((r for r in self.rules if r.is_default), None) \
                or Rule(rule_id="default", intent="knowledge_query", any_words=[])

        sexpr = "\n".join(sexpr_lines) + f"\n=> '{fired_rule.intent}"

        return {
            "intent": fired_rule.intent,
            "rule_id": fired_rule.rule_id,
            "sentiment": self.sentiment(tokens),
            "sexpr": sexpr,
            "tokens": tokens,
        }
