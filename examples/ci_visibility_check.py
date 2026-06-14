#!/usr/bin/env python3
"""Gate a deploy on AI visibility — three ways.

1) Inline assertion (raises VisibilityAssertionError -> non-zero exit):

    from promptbeacon import Beacon
    Beacon("Nike").scan().assert_visibility(min_score=50, min_share_of_voice=0.3)

2) pytest plugin (auto-registers; skips cleanly without API keys). Run this file
   with: `PROMPTBEACON_DEMO=1 pytest examples/ci_visibility_check.py`

       import pytest

       @pytest.mark.visibility(brand="Nike", competitors=["Adidas"], min_score=40)
       def test_brand_is_visible():
           ...

3) GitHub Action (in .github/workflows/geo.yml):

       - uses: yotambraun/promptbeacon@v1
         with:
           brand: "Nike"
           competitors: "Adidas Puma"
           min-share-of-voice: "0.3"
         env:
           OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

This script demonstrates form (1) in keyless demo mode.
"""

from promptbeacon import Beacon, VisibilityAssertionError


def main():
    report = (
        Beacon("Nike")
        .demo()
        .with_competitors("Adidas")
        .with_categories("running shoes")
        .with_prompt_count(6)
        .scan()
    )

    try:
        report.assert_visibility(min_score=10, min_share_of_voice=0.1)
        print(f"PASS — visibility {report.visibility_score}/100 meets the bar.")
    except VisibilityAssertionError as e:
        print(f"FAIL — {e}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
