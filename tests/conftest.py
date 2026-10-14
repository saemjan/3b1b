import pytest
from manim import tempconfig


@pytest.fixture(autouse=True)
def isolate_manim_media(tmp_path):
    media_dir = tmp_path / "manim-media"
    with tempconfig({"media_dir": str(media_dir)}):
        yield