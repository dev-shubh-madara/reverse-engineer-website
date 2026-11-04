from pathlib import Path

from PIL import Image

from sitere.verify import _verdict, similarity


def _solid(path: Path, color, size=(80, 60)):
    Image.new("RGB", size, color).save(path)


def test_identical_images_score_one(tmp_path):
    a, b, d = tmp_path / "a.png", tmp_path / "b.png", tmp_path / "d.png"
    _solid(a, (10, 120, 200))
    _solid(b, (10, 120, 200))
    assert similarity(a, b, d) == 1.0
    assert d.exists()


def test_opposite_images_score_low(tmp_path):
    a, b, d = tmp_path / "a.png", tmp_path / "b.png", tmp_path / "d.png"
    _solid(a, (0, 0, 0))
    _solid(b, (255, 255, 255))
    assert similarity(a, b, d) == 0.0


def test_similar_images_score_high(tmp_path):
    a, b, d = tmp_path / "a.png", tmp_path / "b.png", tmp_path / "d.png"
    _solid(a, (100, 100, 100))
    _solid(b, (110, 105, 100))
    assert 0.9 < similarity(a, b, d) < 1.0


def test_verdict_bands():
    assert "excellent" in _verdict(0.99)
    assert "good" in _verdict(0.92)
    assert "partial" in _verdict(0.80)
    assert "far" in _verdict(0.50)
