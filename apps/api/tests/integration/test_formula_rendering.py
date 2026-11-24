from pathlib import Path

import pytest

from app.adapters.renderer.formulas import (
    FormulaAssetTooLarge,
    FormulaRenderer,
    PrivateFormulaAssetStore,
)


@pytest.mark.parametrize(
    ("latex", "expected_text"),
    [
        (r"\frac{a}{b}", "(a)/(b)"),
        (r"\sqrt{x}", "√(x)"),
        (r"\int_{0}^{3} 2x\,dx", "∫₀³ 2x dx"),
        (r"x_{i}^{2}", "xᵢ²"),
        (r"\Delta T + \alpha", "ΔT + α"),
        (r"\lim_{x \to 0} x", "lim_(x →0) x"),
    ],
)
def test_supported_formula_is_rendered_to_private_svg(
    tmp_path: Path,
    latex: str,
    expected_text: str,
) -> None:
    store = PrivateFormulaAssetStore(tmp_path / "formula-assets")
    rendered = FormulaRenderer(store).render(
        latex=latex,
        fallback_text="fallback expression",
        alt_text="Accessible formula description",
    )

    assert rendered.rendered is True
    assert rendered.plain_text == expected_text
    assert rendered.alt_text == "Accessible formula description"
    assert rendered.asset_key is not None
    asset_path = store.path_for(rendered.asset_key)
    assert asset_path.is_file()
    assert asset_path.stat().st_mode & 0o777 == 0o600
    svg = asset_path.read_text(encoding="utf-8")
    assert "<svg" in svg
    assert expected_text in svg


def test_unsupported_latex_uses_text_fallback_without_asset(tmp_path: Path) -> None:
    store = PrivateFormulaAssetStore(tmp_path / "formula-assets")
    rendered = FormulaRenderer(store).render(
        latex=r"\unknowncommand{x}",
        fallback_text="x with a custom operator",
        alt_text="Exercise formula in text",
    )

    assert rendered.rendered is False
    assert rendered.asset_key is None
    assert rendered.plain_text == "x with a custom operator"
    assert list((tmp_path / "formula-assets").glob("*.svg")) == []


def test_formula_assets_are_bounded_and_keys_are_path_safe(tmp_path: Path) -> None:
    store = PrivateFormulaAssetStore(tmp_path / "formula-assets", max_bytes=16)

    with pytest.raises(FormulaAssetTooLarge):
        store.store(b"x" * 17)
    with pytest.raises(ValueError):
        store.path_for("../../outside.svg")
