"""LaTeX masking regressions: math, commands, tables, comments, verbatim."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import latex_clean  # noqa: E402


class LatexMaskTest(unittest.TestCase):
    def test_protected_regions_unchanged(self) -> None:
        for text in (
            "$$x_1=y_1$$",
            "$x_1+y_2$",
            r"\(x_1\)",
            r"\[x_1\]",
            r"\cite{model_v1}",
            r"\ref{sec:a_b}",
            r"\label{fig:model_v1}",
            r"\url{https://example.com/a_b}",
            r"\verb|a_b|",
            "\\begin{align}\na_1 &= b_1\n\\end{align}",
            "\\begin{equation*}\nx_1 = y_2\n\\end{equation*}",
            "% comment with 50% and a_b",
        ):
            with self.subTest(text=text):
                self.assertEqual(latex_clean.escape_latex(text), text)

    def test_prose_specials_escaped(self) -> None:
        fixed, counts = latex_clean.escape_report("50% 的样本 & 5 个变量")
        self.assertEqual(fixed, "50\\% 的样本 \\& 5 个变量")
        self.assertEqual(counts, {"%": 1, "&": 1})

    def test_table_alignment_preserved_but_cell_text_escaped(self) -> None:
        text = "\\begin{tabular}{cc}\na_1 & b_2 \\\\\n\\end{tabular}"
        fixed = latex_clean.escape_latex(text)
        self.assertIn("a\\_1 & b\\_2", fixed)
        self.assertIn("\\begin{tabular}{cc}", fixed)

    def test_math_inside_document_preserved(self) -> None:
        text = "\\begin{document}\n$x_1$ and 50%\n\\end{document}"
        fixed = latex_clean.escape_latex(text)
        self.assertIn("$x_1$", fixed)
        self.assertIn("50\\%", fixed)

    def test_check_has_no_false_positive_for_protected_regions(self) -> None:
        for text in (
            r"\cite{model_v1}",
            "$$x_1=y_1$$",
            "\\begin{align}\na_1 &= b_1\n\\end{align}",
            r"\url{https://example.com/a%20b}",
        ):
            with self.subTest(text=text):
                self.assertEqual(latex_clean.check_latex(text), [])


if __name__ == "__main__":
    unittest.main()
