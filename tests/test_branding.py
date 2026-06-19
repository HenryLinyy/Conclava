from conclava.server import MODELS_LIST, app


def test_public_branding_is_conclava():
    model_ids = {model["id"] for model in MODELS_LIST["data"]}

    assert app.title == "Conclava"
    assert "conclava-fast" in model_ids
    assert "claude-conclava-fast" in model_ids
    legacy_prefix = "-".join(("local", "fusion"))
    assert all(legacy_prefix not in model_id for model_id in model_ids)
