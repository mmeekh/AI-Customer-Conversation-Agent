"""Smoke tests for sentiment urgency keyword detection."""
from agents.sentiment_analyzer import SentimentAnalyzer


def test_critical_urgency():
    assert SentimentAnalyzer._detect_urgency("I will sue you. My lawyer will call.") == "critical"


def test_high_urgency():
    assert SentimentAnalyzer._detect_urgency("This is urgent, the system is down!") == "high"


def test_low_urgency():
    assert SentimentAnalyzer._detect_urgency("Hi, just had a quick question.") == "low"
