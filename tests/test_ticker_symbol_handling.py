import unittest
from unittest.mock import patch

import pytest

from cli.utils import normalize_ticker_symbol
from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.dataflows.a_stock import resolve_ticker, resolve_ticker_name
from web.components.report_viewer import _download_basename


@pytest.mark.unit
class TickerSymbolHandlingTests(unittest.TestCase):
    def test_normalize_ticker_symbol_preserves_exchange_suffix(self):
        self.assertEqual(normalize_ticker_symbol(" cnc.to "), "CNC.TO")

    def test_build_instrument_context_mentions_exact_symbol(self):
        context = build_instrument_context("7203.T")
        self.assertIn("7203.T", context)
        self.assertIn("exchange suffix", context)

    def test_resolve_ticker_accepts_a_stock_code_variants(self):
        self.assertEqual(resolve_ticker("300750"), "300750")
        self.assertEqual(resolve_ticker("SH688017"), "688017")
        self.assertEqual(resolve_ticker("688017.SH"), "688017")

    def test_resolve_ticker_rejects_non_stock_text(self):
        with self.assertRaisesRegex(ValueError, "不是有效的A股股票代码"):
            resolve_ticker("abc")

    def test_resolve_ticker_rejects_empty_input(self):
        with self.assertRaisesRegex(ValueError, "输入不能为空"):
            resolve_ticker("")

    def test_resolve_ticker_wraps_name_lookup_failure(self):
        with patch(
            "tradingagents.dataflows.a_stock._build_name_code_map",
            side_effect=ValueError("not enough values to unpack"),
        ), patch(
            "tradingagents.dataflows.a_stock._resolve_ticker_eastmoney",
            side_effect=ValueError("fallback failed"),
        ):
            with self.assertRaisesRegex(ValueError, "无法解析股票名称"):
                resolve_ticker("不是股票")

    def test_resolve_ticker_uses_eastmoney_fallback_for_names(self):
        with patch(
            "tradingagents.dataflows.a_stock._build_name_code_map",
            side_effect=ValueError("not enough values to unpack"),
        ), patch(
            "tradingagents.dataflows.a_stock._resolve_ticker_eastmoney",
            return_value="300750",
        ):
            self.assertEqual(resolve_ticker("宁德时代"), "300750")

    def test_resolve_ticker_name_uses_tencent_fallback(self):
        with patch(
            "tradingagents.dataflows.a_stock._build_name_code_map",
            side_effect=ValueError("not enough values to unpack"),
        ), patch(
            "tradingagents.dataflows.a_stock._tencent_quote",
            return_value={"300750": {"name": "宁德时代"}},
        ):
            self.assertEqual(resolve_ticker_name("300750"), "宁德时代")

    def test_download_basename_prefers_stock_name(self):
        with patch(
            "tradingagents.dataflows.a_stock.resolve_ticker_name",
            return_value="宁德时代",
        ):
            self.assertEqual(
                _download_basename("300750", "2026-06-16"),
                "TradingAgents-Astock_2026-06-16_宁德时代",
            )

    def test_download_basename_falls_back_to_code(self):
        with patch(
            "tradingagents.dataflows.a_stock.resolve_ticker_name",
            return_value=None,
        ):
            self.assertEqual(
                _download_basename("300750", "2026-06-16"),
                "TradingAgents-Astock_2026-06-16_300750",
            )


if __name__ == "__main__":
    unittest.main()
