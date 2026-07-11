import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class PublicSiteExperienceTests(unittest.TestCase):
    def test_shared_experience_assets_exist(self):
        stylesheet = (SITE / "assets" / "gca-site.css").read_text()
        script = (SITE / "assets" / "gca-site.js").read_text()

        self.assertIn(".gca-menu-button", stylesheet)
        self.assertIn(".gca-back-to-top", stylesheet)
        self.assertIn("prefers-reduced-motion", stylesheet)
        self.assertIn("Skip to main content", script)
        self.assertIn("跳到主要内容", script)
        self.assertIn('viewer.searchParams.set("source", target.href)', script)
        self.assertIn('rel = "noopener noreferrer"', script)

    def test_public_pages_load_shared_experience_layer(self):
        missing = []
        for path in sorted(SITE.rglob("*.html")):
            relative = path.relative_to(SITE)
            if relative.as_posix() == "operator.html":
                continue

            depth = len(relative.parts) - 1
            prefix = "../" * depth
            page = path.read_text()
            expected_css = f'href="{prefix}assets/gca-site.css?v=20260711"'
            expected_js = f'src="{prefix}assets/gca-site.js?v=20260711" defer'
            if expected_css not in page or expected_js not in page:
                missing.append(relative.as_posix())

        self.assertEqual([], missing)

    def test_data_viewer_is_human_readable_and_does_not_publish_raw_json_href(self):
        page = (SITE / "data-viewer.html").read_text()

        self.assertIn("GCA Data Viewer", page)
        self.assertIn('id="dataRoot"', page)
        self.assertIn('id="readablePage"', page)
        self.assertIn('id="rawLink"', page)
        self.assertIn('["/project.json", "project-profile.html"]', page)
        self.assertIn('["/.well-known/gca-token.json", "trust.html"]', page)
        self.assertIn('["/.well-known/wallet-security.json", "token-safety.html"]', page)
        self.assertIn("relatedPages.get(source.pathname)", page)
        self.assertIn('textContent = String(value)', page)
        self.assertNotRegex(page, re.compile(r'href="[^"]+\.json"'))

    def test_global_navigation_keeps_primary_user_paths_small(self):
        script = (SITE / "assets" / "gca-site.js").read_text()

        for path in (
            "index.html",
            "verify.html",
            "buy.html",
            "product.html",
            "gca/member-access/",
            "trust.html",
            "zh-cn.html",
        ):
            self.assertIn(f'"{path}"', script)

        self.assertIn('navLinks.replaceChildren()', script)
        self.assertIn('aria-current", "page"', script)

    def test_member_access_restores_non_sensitive_device_snapshot(self):
        page = (SITE / "gca" / "member-access" / "index.html").read_text()

        self.assertIn('id="savedSnapshot"', page)
        self.assertIn('id="clearSnapshot"', page)
        self.assertIn('const SNAPSHOT_KEY = "gca_member_access_snapshot_v1"', page)
        self.assertIn("const SNAPSHOT_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000", page)
        self.assertIn("window.localStorage.setItem(SNAPSHOT_KEY", page)
        self.assertIn("window.localStorage.removeItem(SNAPSHOT_KEY)", page)
        self.assertIn("restoreSnapshot();", page)
        self.assertNotIn("email: email.value", page[page.index("function snapshotFromResponse"):page.index("function latestResponseLines")])

    def test_risk_calculator_is_client_side_and_has_no_execution_path(self):
        page = (SITE / "risk-calculator.html").read_text()
        product = (SITE / "product.json").read_text()
        credits = (SITE / "credits.json").read_text()

        for element_id in (
            "equity",
            "riskPercent",
            "entryPrice",
            "stopPrice",
            "targetPrice",
            "leverage",
            "feeBps",
            "slippageBps",
            "positionQuantity",
            "plannedLoss",
            "requiredMargin",
            "copyPlan",
        ):
            self.assertIn(f'id="{element_id}"', page)

        calculator = (SITE / "assets" / "risk-calculator.js").read_text()
        self.assertIn("const riskBudget = equity * (riskPercent / 100)", calculator)
        self.assertIn("const riskPerUnit = stopDistance + (entry * costRate)", calculator)
        self.assertIn("const positionQuantity = riskBudget / riskPerUnit", calculator)
        self.assertIn("const requiredMargin = positionNotional / leverage", calculator)
        self.assertIn('src="assets/risk-calculator.js"', page)
        self.assertIn("applyQueryParameters();", page)
        self.assertIn('["entry", fields.entry]', page)
        self.assertIn("does not connect to a wallet or exchange", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('"status": "public-client-side-preview-live"', product)
        self.assertIn('"url": "https://gcagochina.com/risk-calculator.html"', credits)

    def test_risk_calculator_formula_module(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "risk-calculator.js"
        script = (
            "const c=require(process.argv[1]);"
            "const p=c.calculatePositionPlan({equity:10000,riskPercent:1,entry:100,stop:95,target:110,leverage:2,feeBps:20,slippageBps:10});"
            "process.stdout.write(JSON.stringify(p));"
        )
        result = subprocess.run(
            [node, "-e", script, str(module_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        plan = json.loads(result.stdout)

        self.assertEqual(plan["direction"], "long")
        self.assertAlmostEqual(plan["riskBudget"], 100)
        self.assertAlmostEqual(plan["stopDistance"], 5)
        self.assertAlmostEqual(plan["riskPerUnit"], 5.3)
        self.assertAlmostEqual(plan["positionQuantity"], 100 / 5.3)
        self.assertAlmostEqual(plan["plannedLoss"], 100)
        self.assertAlmostEqual(plan["requiredMargin"], plan["positionNotional"] / 2)
        self.assertTrue(plan["targetOnCorrectSide"])

        invalid_script = (
            "const c=require(process.argv[1]);"
            "process.stdout.write(String(c.calculatePositionPlan({equity:0,riskPercent:1,entry:100,stop:95,leverage:1,feeBps:0,slippageBps:0})));"
        )
        invalid = subprocess.run(
            [node, "-e", invalid_script, str(module_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(invalid.stdout, "null")

    def test_entry_ready_review_is_transparent_and_client_side(self):
        page = (SITE / "entry-ready.html").read_text()
        engine = (SITE / "assets" / "entry-ready.js").read_text()
        product = (SITE / "product.json").read_text()
        credits = (SITE / "credits.json").read_text()

        for element_id in (
            "direction",
            "timeframe",
            "entry",
            "stop",
            "target",
            "riskPercent",
            "leverage",
            "orderType",
            "thesis",
            "positionSized",
            "maxLossAccepted",
            "invalidationDefined",
            "liquidityChecked",
            "costsIncluded",
            "volatilityReviewed",
            "noRevengeTrade",
            "noFomo",
            "exitPlanDefined",
            "status",
            "score",
            "calculatorLink",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn('status = blockers.length > 0 || score < 70', engine)
        self.assertIn('score >= 85 && warnings.length === 0', engine)
        self.assertIn('"NOT_READY"', engine)
        self.assertIn('"ENTRY_READY"', engine)
        self.assertIn('src="assets/entry-ready.js"', page)
        self.assertIn("result.priceStructureValid", page)
        self.assertIn("risk-calculator.html?", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('"publicUrl": "https://gcagochina.com/entry-ready.html"', product)
        self.assertIn('"url": "https://gcagochina.com/entry-ready.html"', credits)

    def test_entry_ready_engine_blocks_incomplete_and_passes_complete_plan(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "entry-ready.js"
        base = {
            "direction": "long",
            "entry": 100,
            "stop": 95,
            "target": 110,
            "riskPercent": 1,
            "leverage": 2,
            "thesis": "Breakout retest with defined invalidation below support.",
            "timeframe": "4h",
            "orderType": "limit",
            "positionSized": True,
            "maxLossAccepted": True,
            "invalidationDefined": True,
            "liquidityChecked": True,
            "costsIncluded": True,
            "volatilityReviewed": True,
            "noRevengeTrade": True,
            "noFomo": True,
            "exitPlanDefined": True,
        }
        script = (
            "const e=require(process.argv[1]);"
            "const input=JSON.parse(process.argv[2]);"
            "process.stdout.write(JSON.stringify(e.evaluate(input)));"
        )
        ready = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(base)],
            check=True,
            capture_output=True,
            text=True,
        )
        ready_result = json.loads(ready.stdout)
        self.assertEqual(ready_result["status"], "ENTRY_READY")
        self.assertEqual(ready_result["score"], 100)
        self.assertEqual(ready_result["blockers"], [])
        self.assertEqual(ready_result["warnings"], [])

        incomplete = {**base, "positionSized": False, "liquidityChecked": False}
        blocked = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(incomplete)],
            check=True,
            capture_output=True,
            text=True,
        )
        blocked_result = json.loads(blocked.stdout)
        self.assertEqual(blocked_result["status"], "NOT_READY")
        self.assertGreaterEqual(len(blocked_result["blockers"]), 2)

        wrong_side = {**base, "stop": 105, "target": 90}
        wrong = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(wrong_side)],
            check=True,
            capture_output=True,
            text=True,
        )
        wrong_result = json.loads(wrong.stdout)
        self.assertEqual(wrong_result["status"], "NOT_READY")
        self.assertFalse(wrong_result["priceStructureValid"])

    def test_liquidation_replay_is_transparent_and_client_side(self):
        page = (SITE / "liquidation-replay.html").read_text()
        engine = (SITE / "assets" / "liquidation-replay.js").read_text()
        product = (SITE / "product.json").read_text()
        credits = (SITE / "credits.json").read_text()

        for element_id in (
            "direction",
            "eventType",
            "accountEquity",
            "quantity",
            "entry",
            "exit",
            "plannedStop",
            "leverage",
            "fees",
            "funding",
            "positionPlanned",
            "stopRespected",
            "addedToLosing",
            "exitRuleFollowed",
            "journalComplete",
            "status",
            "netPnl",
            "accountImpact",
            "effectiveLeverage",
            "lossMultiple",
            "copyReplay",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn("const grossPnl = signedMove * quantity", engine)
        self.assertIn("const netPnl = grossPnl - totalCosts", engine)
        self.assertIn("const effectiveLeverage = positionNotional / accountEquity", engine)
        self.assertIn("const initialMargin = positionNotional / leverage", engine)
        self.assertIn('"CRITICAL_REVIEW"', engine)
        self.assertIn('"PROCESS_REVIEW"', engine)
        self.assertIn('"CONTROLLED"', engine)
        self.assertIn('src="assets/liquidation-replay.js"', page)
        self.assertIn("does not calculate an exchange-specific liquidation price", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('"publicUrl": "https://gcagochina.com/liquidation-replay.html"', product)
        self.assertIn('"url": "https://gcagochina.com/liquidation-replay.html"', credits)
        public_checker = (ROOT / "tools" / "check_public_site.py").read_text()
        self.assertIn('(\"/liquidation-replay.html\", validate_liquidation_replay_page)', public_checker)

    def test_liquidation_replay_engine_calculates_loss_and_escalates_risk(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "liquidation-replay.js"
        script = (
            "const r=require(process.argv[1]);"
            "const input=JSON.parse(process.argv[2]);"
            "process.stdout.write(JSON.stringify(r.replay(input)));"
        )
        controlled_input = {
            "direction": "long",
            "accountEquity": 10000,
            "entry": 100,
            "exit": 95,
            "quantity": 20,
            "leverage": 2,
            "fees": 0,
            "funding": 0,
            "plannedStop": 95,
            "positionPlanned": True,
            "stopRespected": True,
            "addedToLosing": False,
            "exitRuleFollowed": True,
            "journalComplete": True,
        }
        controlled = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(controlled_input)],
            check=True,
            capture_output=True,
            text=True,
        )
        replay = json.loads(controlled.stdout)
        self.assertEqual(replay["status"], "CONTROLLED")
        self.assertAlmostEqual(replay["grossPnl"], -100)
        self.assertAlmostEqual(replay["netPnl"], -100)
        self.assertAlmostEqual(replay["accountImpactPercent"], -1)
        self.assertAlmostEqual(replay["positionNotional"], 2000)
        self.assertAlmostEqual(replay["effectiveLeverage"], 0.2)
        self.assertAlmostEqual(replay["initialMargin"], 1000)
        self.assertAlmostEqual(replay["marginUtilizationPercent"], 10)
        self.assertAlmostEqual(replay["lossMultiple"], 1)

        critical_input = {
            **controlled_input,
            "accountEquity": 1000,
            "exit": 80,
            "quantity": 100,
            "leverage": 10,
            "stopRespected": False,
            "addedToLosing": True,
            "exitRuleFollowed": False,
        }
        critical = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(critical_input)],
            check=True,
            capture_output=True,
            text=True,
        )
        critical_replay = json.loads(critical.stdout)
        self.assertEqual(critical_replay["status"], "CRITICAL_REVIEW")
        self.assertAlmostEqual(critical_replay["netPnl"], -2000)
        self.assertAlmostEqual(critical_replay["accountImpactPercent"], -200)
        self.assertAlmostEqual(critical_replay["effectiveLeverage"], 10)
        self.assertGreaterEqual(len(critical_replay["flags"]), 4)

        invalid = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps({**controlled_input, "accountEquity": 0})],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(invalid.stdout, "null")

    def test_backtest_lab_is_transparent_and_client_side(self):
        page = (SITE / "backtest-lab.html").read_text()
        engine = (SITE / "assets" / "backtest-lab.js").read_text()
        product = (SITE / "product.json").read_text()
        credits = (SITE / "credits.json").read_text()

        for element_id in (
            "backtestForm",
            "startingEquity",
            "costPercent",
            "tradeReturns",
            "status",
            "finalEquity",
            "compoundedReturn",
            "tradeCount",
            "winRate",
            "expectancy",
            "profitFactor",
            "maxDrawdown",
            "lossStreak",
            "equityChart",
            "downloadCsv",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn("equity *= 1 + (netReturn / 100)", engine)
        self.assertIn("const profitFactor = totalLosses > 0 ? totalWins / totalLosses : null", engine)
        self.assertIn("maxDrawdownPercent = Math.max(maxDrawdownPercent, drawdownPercent)", engine)
        self.assertIn('"NEGATIVE_EXPECTANCY"', engine)
        self.assertIn('"INSUFFICIENT_SAMPLE"', engine)
        self.assertIn('"RESEARCH_READY"', engine)
        self.assertIn('src="assets/backtest-lab.js"', page)
        self.assertIn("does not test signals against candles or order books", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('"publicUrl": "https://gcagochina.com/backtest-lab.html"', product)
        self.assertIn('"url": "https://gcagochina.com/backtest-lab.html"', credits)
        public_checker = (ROOT / "tools" / "check_public_site.py").read_text()
        self.assertIn('(\"/backtest-lab.html\", validate_backtest_lab_page)', public_checker)

    def test_backtest_lab_engine_calculates_expectancy_and_drawdown(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "backtest-lab.js"
        script = (
            "const b=require(process.argv[1]);"
            "const input=JSON.parse(process.argv[2]);"
            "process.stdout.write(JSON.stringify(b.analyzeSequence(input)));"
        )
        sample = [value for _ in range(15) for value in (1, -0.5)]
        ready = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps({"startingEquity": 10000, "costPercent": 0, "tradeReturns": sample})],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(ready.stdout)
        self.assertEqual(result["status"], "RESEARCH_READY")
        self.assertEqual(result["tradeCount"], 30)
        self.assertEqual(result["wins"], 15)
        self.assertEqual(result["losses"], 15)
        self.assertAlmostEqual(result["winRatePercent"], 50)
        self.assertAlmostEqual(result["averageReturnPercent"], 0.25)
        self.assertAlmostEqual(result["profitFactor"], 2)
        self.assertEqual(result["maxConsecutiveLosses"], 1)
        self.assertAlmostEqual(result["finalEquity"], 10000 * ((1.01 * 0.995) ** 15))

        negative_sample = [value for _ in range(15) for value in (0.2, -1)]
        negative = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps({"startingEquity": 10000, "costPercent": 0, "tradeReturns": negative_sample})],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(negative.stdout)["status"], "NEGATIVE_EXPECTANCY")

        invalid = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps({"startingEquity": 10000, "costPercent": 0, "tradeReturns": [-100]})],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(invalid.stdout, "null")


if __name__ == "__main__":
    unittest.main()
