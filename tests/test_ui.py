"""Headless smoke test of the Streamlit UI using Streamlit's AppTest harness."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    return at


def test_app_boots_without_exceptions():
    at = _app()
    assert not at.exception, [str(x.value) for x in at.exception]
    assert len(at.tabs) == 5


def test_safety_sample_flow():
    at = _app()
    next(c for c in at.checkbox if c.key == "safety_sample").check()
    at.run()
    next(b for b in at.button if b.key == "run_safety").click()
    at.run()
    assert not at.exception, [str(x.value) for x in at.exception]
    assert at.session_state["safety_report"] is not None
    assert at.session_state["safety_report"].analysis_mode == "demo"


def test_crack_sample_flow():
    at = _app()
    next(c for c in at.checkbox if c.key == "crack_sample").check()
    at.run()
    next(b for b in at.button if b.key == "run_crack").click()
    at.run()
    assert not at.exception, [str(x.value) for x in at.exception]
    assert at.session_state["crack_report"].estimated_width_mm > 0


def test_valuation_and_weather_update_state():
    at = _app()
    assert at.session_state["valuation"]["inputs"]["completion_pct"] == 45
    next(s for s in at.slider if s.key == "pl_completion").set_value(80)
    at.run()
    assert at.session_state["valuation"]["inputs"]["completion_pct"] == 80
    next(r for r in at.radio if r.key == "weather_radio").set_value("Heavy Rain")
    at.run()
    assert at.session_state["weather_condition"] == "Heavy Rain"
    assert not at.exception, [str(x.value) for x in at.exception]


def test_chat_offline_answer():
    at = _app()
    at.chat_input[0].set_value("How long should concrete be cured?").run()
    assert not at.exception, [str(x.value) for x in at.exception]
    history = at.session_state["chat_history"]
    assert history[-1]["role"] == "assistant" and "7 days" in history[-1]["content"]
