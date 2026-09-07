from core.tokens import estimated_tokens_saved


def test_avoiding_llm_saves_baseline() -> None:
    estimated, saved = estimated_tokens_saved(llm_used=False, actual_tokens=0, baseline=1200)
    assert estimated == 1200
    assert saved == 1200


def test_llm_path_saves_the_difference() -> None:
    estimated, saved = estimated_tokens_saved(llm_used=True, actual_tokens=400, baseline=1200)
    assert estimated == 1200
    assert saved == 800
