"""Smoke tests for the intent classifier output parsing."""
from agents.intent_classifier import IntentClassifier, IntentResult


def test_parse_valid_json():
    text = '{"intent": "billing", "confidence": 0.92, "reasoning": "Refund question"}'
    r = IntentClassifier._parse(text)
    assert r.intent == "billing"
    assert r.confidence == 0.92


def test_parse_with_surrounding_text():
    text = 'Sure, here you go: {"intent": "sales", "confidence": 0.7, "reasoning": "Demo"} thanks'
    r = IntentClassifier._parse(text)
    assert r.intent == "sales"


def test_parse_falls_back_on_invalid():
    r = IntentClassifier._parse("not json at all")
    assert isinstance(r, IntentResult)
    assert r.intent == "support"
    assert r.confidence < 0.5
