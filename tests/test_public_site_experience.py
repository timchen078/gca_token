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
            "tools.html",
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
        self.assertIn('["entry", fields.entry, false]', page)
        self.assertIn('["equity", fields.equity, false]', page)
        self.assertIn("window.location.hash", page)
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
        self.assertIn("risk-calculator.html#", page)
        self.assertIn("function applyPlanParameters()", page)
        self.assertIn("window.location.hash", page)
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
            "tradeDate",
            "market",
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
            "completedTradeConfirmed",
            "status",
            "netPnl",
            "accountImpact",
            "effectiveLeverage",
            "lossMultiple",
            "copyReplay",
            "planScenario",
            "saveReplayToJournal",
            "journalSaveStatus",
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
        self.assertIn('src="assets/trade-journal.js"', page)
        self.assertIn("function journalTrade(result, id)", page)
        self.assertIn("window.localStorage.setItem(window.GcaTradeJournal.STORAGE_KEY", page)
        self.assertIn('fields.completedTradeConfirmed.checked = false', page)
        self.assertIn("function applyPlanParameters()", page)
        self.assertIn("window.location.hash", page)
        self.assertIn("planned-stop simulation", page)
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
            "planImportNotice",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn("equity *= 1 + (netReturn / 100)", engine)
        self.assertIn("const profitFactor = totalLosses > 0 ? totalWins / totalLosses : null", engine)
        self.assertIn("maxDrawdownPercent = Math.max(maxDrawdownPercent, drawdownPercent)", engine)
        self.assertIn('"NEGATIVE_EXPECTANCY"', engine)
        self.assertIn('"INSUFFICIENT_SAMPLE"', engine)
        self.assertIn('"RESEARCH_READY"', engine)
        self.assertIn('src="assets/backtest-lab.js"', page)
        self.assertIn('src="assets/trade-journal.js"', page)
        self.assertIn("function applyPlanParameters()", page)
        self.assertIn("window.location.hash", page)
        self.assertIn("Account equity was imported", page)
        self.assertIn('id="journalImportNotice"', page)
        self.assertIn('read("source") === "journal"', page)
        self.assertIn("window.GcaTradeJournal.filterTrades", page)
        self.assertIn('market:read("market")', page)
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

    def test_risk_warning_review_is_transparent_and_client_side(self):
        page = (SITE / "risk-warning.html").read_text()
        engine = (SITE / "assets" / "risk-warning.js").read_text()
        product = (SITE / "product.json").read_text()
        credits = (SITE / "credits.json").read_text()

        for element_id in (
            "riskWarningForm",
            "exposurePercent",
            "leverage",
            "riskPercent",
            "stopDistancePercent",
            "slippagePercent",
            "volatilityPercent",
            "liquidityCoverage",
            "fundingPercent",
            "correlatedPositions",
            "stopDefined",
            "exitPlanDefined",
            "liquidityChecked",
            "dataFresh",
            "eventRisk",
            "revengeTrade",
            "fomo",
            "status",
            "score",
            "accountScore",
            "marketScore",
            "processScore",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn("const score = account + market + process", engine)
        self.assertIn('status = "DO_NOT_PROCEED"', engine)
        self.assertIn('status = "HIGH_RISK"', engine)
        self.assertIn('status = "ELEVATED_REVIEW"', engine)
        self.assertIn('"STANDARD_REVIEW"', engine)
        self.assertIn('src="assets/risk-warning.js"', page)
        self.assertIn("function applyPlanParameters()", page)
        self.assertIn("window.location.hash", page)
        self.assertIn("does not fetch prices or liquidity", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('"publicUrl": "https://gcagochina.com/risk-warning.html"', product)
        self.assertIn('"url": "https://gcagochina.com/risk-warning.html"', credits)
        public_checker = (ROOT / "tools" / "check_public_site.py").read_text()
        self.assertIn('(\"/risk-warning.html\", validate_risk_warning_page)', public_checker)

    def test_risk_warning_engine_scores_standard_and_blocked_setups(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "risk-warning.js"
        script = (
            "const r=require(process.argv[1]);"
            "const input=JSON.parse(process.argv[2]);"
            "process.stdout.write(JSON.stringify(r.review(input)));"
        )
        standard_input = {
            "exposurePercent": 20,
            "leverage": 2,
            "riskPercent": 1,
            "stopDistancePercent": 5,
            "slippagePercent": 0.1,
            "volatilityPercent": 3,
            "liquidityCoverage": 15,
            "fundingPercent": 0.01,
            "correlatedPositions": 0,
            "stopDefined": True,
            "exitPlanDefined": True,
            "liquidityChecked": True,
            "dataFresh": True,
            "eventRisk": False,
            "revengeTrade": False,
            "fomo": False,
        }
        standard = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(standard_input)],
            check=True,
            capture_output=True,
            text=True,
        )
        standard_result = json.loads(standard.stdout)
        self.assertEqual(standard_result["status"], "STANDARD_REVIEW")
        self.assertEqual(standard_result["score"], 2)
        self.assertEqual(standard_result["categories"], {"account": 0, "market": 2, "process": 0})
        self.assertEqual(standard_result["blockers"], [])

        blocked_input = {
            **standard_input,
            "exposurePercent": 150,
            "leverage": 25,
            "riskPercent": 5,
            "stopDistancePercent": 1,
            "slippagePercent": 3,
            "volatilityPercent": 20,
            "liquidityCoverage": 0.5,
            "fundingPercent": 0.2,
            "correlatedPositions": 4,
            "stopDefined": False,
            "exitPlanDefined": False,
            "liquidityChecked": False,
            "dataFresh": False,
            "eventRisk": True,
            "revengeTrade": True,
            "fomo": True,
        }
        blocked = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(blocked_input)],
            check=True,
            capture_output=True,
            text=True,
        )
        blocked_result = json.loads(blocked.stdout)
        self.assertEqual(blocked_result["status"], "DO_NOT_PROCEED")
        self.assertEqual(blocked_result["score"], 100)
        self.assertEqual(blocked_result["categories"], {"account": 40, "market": 35, "process": 25})
        self.assertGreaterEqual(len(blocked_result["blockers"]), 6)

        invalid = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps({**standard_input, "leverage": 0})],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(invalid.stdout, "null")

    def test_risk_tools_workspace_unifies_all_public_tools(self):
        page = (SITE / "tools.html").read_text()
        engine = (SITE / "assets" / "risk-tools.js").read_text()
        product = (SITE / "product.json").read_text()
        credits = (SITE / "credits.json").read_text()

        for mode in ("prepare", "research", "review", "all"):
            self.assertIn(f'data-mode="{mode}"', page)
        for tool_id, url in (
            ("risk-calculator", "risk-calculator.html"),
            ("risk-warning", "risk-warning.html"),
            ("entry-ready", "entry-ready.html"),
            ("backtest-lab", "backtest-lab.html"),
            ("liquidation-replay", "liquidation-replay.html"),
        ):
            self.assertIn(f'data-tool="{tool_id}"', page)
            self.assertIn(f'href="{url}"', page)

        self.assertIn('id="workflowSteps"', page)
        for element_id in (
            "tradePlanForm",
            "planDirection",
            "planEquity",
            "planRisk",
            "planLeverage",
            "planEntry",
            "planStop",
            "planTarget",
            "planExposure",
            "planFees",
            "planSlippage",
            "planVolatility",
            "planLiquidity",
            "planStatus",
            "planCalculator",
            "planWarning",
            "planEntryReady",
            "planBacktest",
            "planReplay",
        ):
            self.assertIn(f'id="{element_id}"', page)
        self.assertIn('src="assets/risk-tools.js"', page)
        self.assertIn('const key="gca_risk_tools_mode_v1"', page)
        self.assertIn("window.localStorage.setItem(key,workflow.mode)", page)
        self.assertNotIn("email", page.lower())
        self.assertNotIn("walletAddress", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn("Plan data stays in the URL fragment", page)
        self.assertIn("The workspace does not save these plan values", page)
        self.assertIn("five plan-aware", page)
        self.assertIn("Six Risk Tools", page)
        self.assertIn('data-tool="trade-journal"', page)
        self.assertIn('"riskToolsWorkspace": "https://gcagochina.com/tools.html"', product)
        self.assertIn('"riskToolsWorkspace": "https://gcagochina.com/tools.html"', credits)
        self.assertIn('["Tools", "tools.html"]', (SITE / "assets" / "gca-site.js").read_text())
        public_checker = (ROOT / "tools" / "check_public_site.py").read_text()
        self.assertIn('(\"/tools.html\", validate_risk_tools_page)', public_checker)
        self.assertIn("prepare:", engine)
        self.assertIn("research:", engine)
        self.assertIn("review:", engine)

    def test_risk_tools_workflow_engine_returns_expected_order(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "risk-tools.js"
        script = (
            "const w=require(process.argv[1]);"
            "process.stdout.write(JSON.stringify(w.getWorkflow(process.argv[2])));"
        )
        expectations = {
            "prepare": ["risk-calculator", "risk-warning", "entry-ready"],
            "research": ["trade-journal", "backtest-lab", "risk-warning", "entry-ready"],
            "review": ["liquidation-replay", "trade-journal", "risk-calculator", "risk-warning", "entry-ready"],
            "all": ["risk-calculator", "risk-warning", "entry-ready", "backtest-lab", "liquidation-replay", "trade-journal"],
        }
        for mode, expected in expectations.items():
            completed = subprocess.run(
                [node, "-e", script, str(module_path), mode],
                check=True,
                capture_output=True,
                text=True,
            )
            workflow = json.loads(completed.stdout)
            self.assertEqual(workflow["mode"], mode)
            self.assertEqual([item["id"] for item in workflow["tools"]], expected)
            self.assertEqual([item["order"] for item in workflow["tools"]], list(range(1, len(expected) + 1)))

        fallback = subprocess.run(
            [node, "-e", script, str(module_path), "unknown"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(fallback.stdout)["mode"], "prepare")

    def test_risk_tools_trade_plan_builds_fragment_only_handoffs(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "risk-tools.js"
        script = (
            "const w=require(process.argv[1]);"
            "const input=JSON.parse(process.argv[2]);"
            "process.stdout.write(JSON.stringify(w.buildPlanLinks(input)));"
        )
        plan = {
            "direction": "long",
            "equity": 10000,
            "risk": 1,
            "entry": 100,
            "stop": 95,
            "target": 110,
            "leverage": 2,
            "exposure": 20,
            "slippage": 0.1,
            "fees": 0.2,
            "volatility": 3,
            "liquidity": 15,
        }
        completed = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(plan)],
            check=True,
            capture_output=True,
            text=True,
        )
        links = json.loads(completed.stdout)
        self.assertAlmostEqual(links["plan"]["stopDistance"], 5)
        self.assertAlmostEqual(links["plan"]["riskBudget"], 100)
        self.assertAlmostEqual(links["plan"]["riskPerUnit"], 5.3)
        self.assertAlmostEqual(links["plan"]["quantity"], 100 / 5.3)
        self.assertAlmostEqual(links["plan"]["scenarioExit"], 94.9)
        for key in ("calculator", "riskWarning", "entryReady", "backtest", "replay"):
            self.assertIn(".html#", links[key])
            self.assertNotIn(".html?", links[key])
        self.assertIn("equity=10000", links["calculator"])
        self.assertIn("feeBps=20", links["calculator"])
        self.assertIn("slippageBps=10", links["calculator"])
        self.assertIn("stopDistance=5", links["riskWarning"])
        self.assertIn("direction=long", links["entryReady"])
        self.assertIn("startingEquity=10000", links["backtest"])
        self.assertIn("source=plan", links["backtest"])
        self.assertIn("accountEquity=10000", links["replay"])
        self.assertIn("plannedStop=95", links["replay"])
        self.assertIn("source=plan", links["replay"])

        short_plan = {**plan, "direction": "short", "stop": 105, "target": 90}
        short_completed = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(short_plan)],
            check=True,
            capture_output=True,
            text=True,
        )
        short_links = json.loads(short_completed.stdout)
        self.assertAlmostEqual(short_links["plan"]["scenarioExit"], 105.1)
        self.assertIn("direction=short", short_links["replay"])

        invalid = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps({**plan, "stop": 105})],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(invalid.stdout, "null")

        invalid_fees = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps({**plan, "fees": 11})],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(invalid_fees.stdout, "null")

    def test_trade_journal_is_local_and_connected_to_backtest(self):
        page = (SITE / "trade-journal.html").read_text()
        engine = (SITE / "assets" / "trade-journal.js").read_text()
        product = json.loads((SITE / "product.json").read_text())
        credits = json.loads((SITE / "credits.json").read_text())

        for element_id in (
            "journalForm",
            "tradeDate",
            "market",
            "direction",
            "returnPercent",
            "setup",
            "notes",
            "saveTrade",
            "resetTrade",
            "cancelEdit",
            "journalStatus",
            "tradeCount",
            "winRate",
            "averageReturn",
            "maxLossStreak",
            "sampleQuality",
            "compoundedReturn",
            "journalMaxDrawdown",
            "equityTitle",
            "journalEquityChart",
            "emptyEquity",
            "analyzeJournal",
            "exportJson",
            "exportCsv",
            "importJson",
            "importCsv",
            "clearJournal",
            "journalRows",
            "journalFilters",
            "filterMarket",
            "filterDirection",
            "filterSetup",
            "filterFrom",
            "filterTo",
            "resetFilters",
            "filterStatus",
            "breakdownTitle",
            "breakdownDimension",
            "breakdownRows",
            "emptyBreakdown",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn('src="assets/trade-journal.js"', page)
        self.assertIn('src="assets/backtest-lab.js"', page)
        self.assertIn("backtest.analyzeSequence({startingEquity:100,costPercent:0,tradeReturns:summary.returns})", page)
        self.assertIn("drawEquityCurve(currentCurve)", page)
        self.assertIn("assumes no deposits, withdrawals, or per-trade costs", page)
        self.assertIn("window.localStorage.setItem(engine.STORAGE_KEY", page)
        self.assertIn("window.localStorage.removeItem(engine.STORAGE_KEY)", page)
        self.assertIn('href="backtest-lab.html#source=journal"', page)
        self.assertIn("engine.filterTrades(trades,filters())", page)
        self.assertIn("gca-trade-journal-filtered.csv", page)
        self.assertIn("engine.parseCsv(await file.text())", page)
        self.assertIn("CSV restored:", page)
        self.assertIn("function restoreImported(imported)", page)
        self.assertIn("if(merged.size>engine.MAX_TRADES)", page)
        self.assertIn("Import would contain", page)
        self.assertIn("engine.groupPerformance(visibleTrades,breakdownDimension.value)", page)
        self.assertIn("let editingId = null", page)
        self.assertIn("edit.dataset.editId=trade.id", page)
        self.assertIn("Update Trade / 更新记录", page)
        self.assertIn("createdAt:existing?.createdAt||new Date().toISOString()", page)
        self.assertIn("Simple total adds account returns without compounding", page)
        self.assertIn("does not upload trades", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('const STORAGE_KEY = "gca_trade_journal_v1"', engine)
        self.assertEqual(product["positioning"]["publicRiskToolPreviewsLive"], 6)
        self.assertEqual(product["officialLinks"]["tradeJournal"], "https://gcagochina.com/trade-journal.html")
        self.assertEqual(credits["officialLinks"]["tradeJournal"], "https://gcagochina.com/trade-journal.html")

    def test_trade_journal_engine_normalizes_summarizes_and_backs_up(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "trade-journal.js"
        script = (
            "const j=require(process.argv[1]);"
            "const trades=JSON.parse(process.argv[2]);"
            "const summary=j.summarizeTrades(trades);"
            "const backup=j.buildBackup(trades,'2026-07-11T00:00:00Z');"
            "const csv=j.toCsv(trades);"
            "const legacy='date,market,direction,return_percent,setup,notes\\n2026-07-04,btc/usdt,long,0.5,breakout,legacy note';"
            "process.stdout.write(JSON.stringify({summary,backup,parsed:j.parseBackup(JSON.stringify(backup)),csv,parsedCsv:j.parseCsv(csv),legacyCsv:j.parseCsv(legacy),filtered:j.filterTrades(trades,{market:'BTC/USDT',direction:'long'}),dateFiltered:j.filterTrades(trades,{from:'2026-07-02',to:'2026-07-03'}),directionGroups:j.groupPerformance(trades,'direction'),setupGroups:j.groupPerformance(trades,'setup'),qualities:[j.sampleQuality(0),j.sampleQuality(29),j.sampleQuality(30),j.sampleQuality(99),j.sampleQuality(100)]}));"
        )
        trades = [
            {"id": "b", "date": "2026-07-02", "market": "eth/usdt", "direction": "short", "returnPercent": -0.5, "setup": "retest", "notes": "stopped", "createdAt": "2026-07-02T01:00:00Z"},
            {"id": "a", "date": "2026-07-01", "market": "btc/usdt", "direction": "long", "returnPercent": 1.0, "setup": "breakout", "notes": "followed, \"plan\"", "createdAt": "2026-07-01T01:00:00Z"},
            {"id": "c", "date": "2026-07-03", "market": "sol/usdt", "direction": "long", "returnPercent": -0.25, "setup": "range", "notes": "early entry", "createdAt": "2026-07-03T01:00:00Z"},
        ]
        completed = subprocess.run(
            [node, "-e", script, str(module_path), json.dumps(trades)],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        summary = result["summary"]
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["wins"], 1)
        self.assertEqual(summary["losses"], 2)
        self.assertAlmostEqual(summary["winRatePercent"], 100 / 3)
        self.assertAlmostEqual(summary["averageReturnPercent"], 0.25 / 3)
        self.assertEqual(summary["maxConsecutiveLosses"], 2)
        self.assertEqual(summary["sampleQuality"]["code"], "INSUFFICIENT_SAMPLE")
        self.assertEqual([trade["id"] for trade in summary["trades"]], ["a", "b", "c"])
        self.assertEqual(len(result["parsed"]["trades"]), 3)
        self.assertIn('"BTC/USDT"', result["csv"])
        self.assertIn('"followed, ""plan"""', result["csv"])
        self.assertEqual(result["parsedCsv"]["trades"][0]["notes"], 'followed, "plan"')
        self.assertIn("id,created_at", result["csv"].splitlines()[0])
        self.assertEqual([trade["id"] for trade in result["parsedCsv"]["trades"]], ["a", "b", "c"])
        self.assertEqual(result["parsedCsv"]["source"], "current-csv")
        self.assertEqual(result["legacyCsv"]["source"], "legacy-csv")
        self.assertEqual(result["legacyCsv"]["trades"][0]["market"], "BTC/USDT")
        self.assertTrue(result["legacyCsv"]["trades"][0]["id"].startswith("csv-"))
        self.assertEqual([trade["id"] for trade in result["filtered"]], ["a"])
        self.assertEqual([trade["id"] for trade in result["dateFiltered"]], ["b", "c"])
        direction_groups = {group["label"]: group for group in result["directionGroups"]}
        self.assertEqual(direction_groups["long"]["count"], 2)
        self.assertEqual(direction_groups["short"]["count"], 1)
        self.assertAlmostEqual(direction_groups["long"]["averageReturnPercent"], 0.375)
        self.assertAlmostEqual(direction_groups["long"]["totalReturnPercent"], 0.75)
        self.assertEqual(direction_groups["long"]["sampleQuality"]["code"], "INSUFFICIENT_SAMPLE")
        self.assertEqual([group["label"] for group in result["setupGroups"]], ["breakout", "range", "retest"])
        self.assertEqual([quality["code"] for quality in result["qualities"]], [
            "INSUFFICIENT_SAMPLE",
            "INSUFFICIENT_SAMPLE",
            "EARLY_SAMPLE",
            "EARLY_SAMPLE",
            "LARGER_SAMPLE",
        ])

        invalid_script = (
            "const j=require(process.argv[1]);"
            "const duplicate=['date,market,direction,return_percent,setup,notes,id,created_at','2026-07-01,BTC/USDT,long,1,x,n,same,2026-07-01T00:00:00Z','2026-07-02,ETH/USDT,long,1,x,n,same,2026-07-02T00:00:00Z'].join('\\n');"
            "const tooMany=['date,market,direction,return_percent,setup,notes',...Array.from({length:501},(_,i)=>`2026-07-01,BTC/USDT,long,1,x,${i}`)].join('\\n');"
            "process.stdout.write(JSON.stringify([j.normalizeTrade({date:'2026-02-31',market:'BTC/USDT',direction:'long',returnPercent:1}),j.normalizeTrade({date:'2026-07-01',market:'BTC/USDT',direction:'long',returnPercent:-100}),j.parseBackup('{}'),j.parseCsv('bad,header\\n1,2'),j.parseCsv('date,market,direction,return_percent,setup,notes\\n2026-07-01,BTC/USDT,side,1,x,n'),j.parseCsv('date,market,direction,return_percent,setup,notes\\n2026-07-01,BTC/USDT,long,1,x,\"open'),j.parseCsv(duplicate),j.parseCsv(tooMany)]));"
        )
        invalid = subprocess.run(
            [node, "-e", invalid_script, str(module_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(invalid.stdout), [None, None, None, None, None, None, None, None])


if __name__ == "__main__":
    unittest.main()
