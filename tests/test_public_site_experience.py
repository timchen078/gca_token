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

    def test_member_workspace_is_local_and_builds_manual_request_packets(self):
        page = (SITE / "member-workspace.html").read_text()
        engine = (SITE / "assets" / "member-workspace.js").read_text()
        product = json.loads((SITE / "product.json").read_text())
        credits = json.loads((SITE / "credits.json").read_text())
        sitemap = (SITE / "sitemap.xml").read_text()

        for element_id in (
            "workspaceState",
            "workspaceWallet",
            "workspaceBalance",
            "workspaceCredits",
            "workspaceMember",
            "journalTradeCount",
            "journalWinRate",
            "journalAverage",
            "journalQuality",
            "trainingSummaryTitle",
            "trainingAttemptCount",
            "trainingLatest",
            "trainingBest",
            "trainingReadyCount",
            "trainingSavedAt",
            "researchSummaryTitle",
            "researchNoteCount",
            "researchActiveCount",
            "researchSourcedCount",
            "researchDueCount",
            "researchSavedAt",
            "tradePlanSummaryTitle",
            "tradePlanSummaryCount",
            "tradePlanSummaryActive",
            "tradePlanSummaryReady",
            "tradePlanSummaryBlocked",
            "tradePlanSummarySavedAt",
            "portfolioSummaryTitle",
            "portfolioSummaryCount",
            "portfolioSummaryStatus",
            "portfolioSummaryRisk",
            "portfolioSummaryExposure",
            "portfolioSummarySavedAt",
            "serviceGrid",
            "serviceRequestForm",
            "serviceId",
            "contactEmail",
            "requestTitle",
            "requestSummary",
            "marketContext",
            "preferredLanguage",
            "buildServicePacket",
            "requestStatus",
            "requestPacket",
            "copyServicePacket",
            "downloadServicePacket",
            "emailServicePacket",
            "requestActivity",
            "requestActivityTitle",
            "requestHistoryCount",
            "requestHistoryList",
            "exportRequestHistory",
            "importRequestHistory",
            "requestBackupStatus",
            "clearRequestHistory",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn('src="assets/member-workspace.js"', page)
        self.assertIn('src="assets/trade-journal.js"', page)
        self.assertIn('src="assets/risk-training.js"', page)
        self.assertIn('src="assets/research-notes.js"', page)
        self.assertIn('src="assets/trade-plans.js"', page)
        self.assertIn('src="assets/portfolio-risk.js"', page)
        self.assertIn("engine.parseMemberSnapshot", page)
        self.assertIn("engine.summarizeJournal", page)
        self.assertIn("engine.summarizeTraining", page)
        self.assertIn("engine.summarizeResearchNotes", page)
        self.assertIn("engine.summarizeTradePlans", page)
        self.assertIn("engine.summarizePortfolioRisk", page)
        self.assertIn("trainingStatusLabel", page)
        self.assertIn("engine.buildServiceRequest", page)
        self.assertIn("engine.createRequestReceipt", page)
        self.assertIn("engine.markRequestAction", page)
        self.assertIn("engine.removeRequestReceipt", page)
        self.assertIn("engine.buildRequestHistoryBackup", page)
        self.assertIn("engine.parseRequestHistoryBackup", page)
        self.assertIn("engine.mergeRequestHistoryBackup", page)
        self.assertIn("await file.text()", page)
        self.assertIn("navigator.clipboard.writeText", page)
        self.assertIn("URL.createObjectURL", page)
        self.assertIn("mailto:support@gcagochina.com", page)
        self.assertIn("does not deduct credits", page)
        self.assertIn("does not read protected D1 ledgers", page)
        self.assertIn("does not prove that support received", page)
        self.assertIn("it is not uploaded by this page", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('const SNAPSHOT_KEY = "gca_member_access_snapshot_v1"', engine)
        self.assertIn('const JOURNAL_KEY = "gca_trade_journal_v1"', engine)
        self.assertIn('const TRAINING_HISTORY_KEY = "gca_risk_training_history_v1"', engine)
        self.assertIn('const RESEARCH_NOTES_KEY = "gca_research_notes_v1"', engine)
        self.assertIn('const TRADE_PLANS_KEY = "gca_trade_plans_v1"', engine)
        self.assertIn('const PORTFOLIO_RISK_KEY = "gca_portfolio_risk_v1"', engine)
        self.assertIn('const REQUEST_HISTORY_KEY = "gca_member_service_request_history_v1"', engine)
        self.assertIn('const REQUEST_BACKUP_SCHEMA = "gca-member-request-history-backup-v1"', engine)
        self.assertIn("SENSITIVE_RE", engine)
        workspace = next(item for item in product["productModules"] if item["id"] == "gca-member-workspace")
        self.assertEqual(workspace["status"], "public-browser-local-workspace-live-account-ledger-intake-live")
        self.assertEqual(workspace["publicUrl"], "https://gcagochina.com/member-workspace.html")
        self.assertTrue(workspace["browserLocalRequestReceipts"])
        self.assertTrue(workspace["portableRequestReceiptBackup"])
        self.assertFalse(workspace["requestReceiptBackupContainsIdentityData"])
        self.assertFalse(workspace["requestReceiptBackupContainsRequestContent"])
        self.assertEqual(product["officialLinks"]["memberWorkspace"], "https://gcagochina.com/member-workspace.html")
        self.assertEqual(product["officialLinks"]["researchNotes"], "https://gcagochina.com/research-notes.html")
        self.assertEqual(product["officialLinks"]["tradePlanLedger"], "https://gcagochina.com/trade-plans.html")
        self.assertEqual(product["officialLinks"]["portfolioRiskMap"], "https://gcagochina.com/portfolio-risk.html")
        catalog_units = {item["id"]: item["creditUnit"] for item in credits["serviceCatalog"]}
        for service_id, credit_unit in (
            ("position-size-calculator", 5),
            ("portfolio-risk-map", 15),
            ("risk-warning-review", 10),
            ("entry-ready-review", 15),
            ("backtest-lab-run", 20),
            ("liquidation-replay-report", 30),
            ("risk-control-training", 10),
            ("member-research-notes", 20),
            ("support-review-queue", 0),
        ):
            self.assertEqual(catalog_units[service_id], credit_unit)
        self.assertIn("https://gcagochina.com/member-workspace.html", sitemap)
        self.assertIn("https://gcagochina.com/research-notes.html", sitemap)
        self.assertIn("https://gcagochina.com/trade-plans.html", sitemap)
        self.assertIn("https://gcagochina.com/portfolio-risk.html", sitemap)

    def test_member_workspace_engine_validates_snapshot_journal_and_request(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "member-workspace.js"
        journal_path = SITE / "assets" / "trade-journal.js"
        training_path = SITE / "assets" / "risk-training.js"
        research_path = SITE / "assets" / "research-notes.js"
        script = (
            "const w=require(process.argv[1]);const j=require(process.argv[2]);const t=require(process.argv[3]);const r=require(process.argv[4]);"
            "const raw=JSON.stringify({version:1,savedAt:'2026-07-14T00:00:00Z',walletAddress:'0x1111111111111111111111111111111111111111',gcaBalance:'1000000',holderBonusEligible:true,gcaMemberEligible:true,holdingPeriodDaysVerified:31,creditAmount:100,remainingCredits:75,creditStatus:'ledger_recorded',memberStatus:'active',memberBenefitClaimStatus:'pending_manual_reserve_transfer'});"
            "const snapshot=w.parseMemberSnapshot(raw,Date.parse('2026-07-14T12:00:00Z'));"
            "const requestInput={serviceId:'backtest-lab-run',email:'Member@Example.com',title:'Review completed sample',summary:'Review this completed trade sample for drawdown and execution discipline.',marketContext:'BTC/USDT 4h completed trades',preferredLanguage:'zh-CN'};"
            "const request=w.buildServiceRequest(requestInput,snapshot,'2026-07-14T12:30:00Z','gca_local_req_test1234');"
            "const receipt=w.createRequestReceipt(request,requestInput,'2026-07-14T12:31:00Z');"
            "const history=w.upsertRequestHistory('[]',receipt);"
            "const copied=w.markRequestAction(history,request.requestId,'packet_copied','2026-07-14T12:32:00Z');"
            "const backup=w.buildRequestHistoryBackup(copied,'2026-07-14T12:33:00Z');"
            "const parsedBackup=w.parseRequestHistoryBackup(JSON.stringify(backup));"
            "const invalidBackup=w.parseRequestHistoryBackup({...backup,receipts:[{...backup.receipts[0],contactEmail:'private@example.com'}]});"
            "const duplicateBackup=w.parseRequestHistoryBackup({...backup,receipts:[...backup.receipts,backup.receipts[0]]});"
            "const currentNewer=w.markRequestAction(copied,request.requestId,'packet_downloaded','2026-07-14T12:35:00Z');"
            "const olderMerge=w.mergeRequestHistoryBackup(currentNewer,backup);"
            "const importedNewer=w.markRequestAction(copied,request.requestId,'email_client_opened','2026-07-14T12:36:00Z');"
            "const secondRequest=w.buildServiceRequest({...requestInput,serviceId:'risk-control-training'},snapshot,'2026-07-14T12:37:00Z','gca_local_req_second123');"
            "const secondReceipt=w.createRequestReceipt(secondRequest,requestInput,'2026-07-14T12:38:00Z');"
            "const newerBackup=w.buildRequestHistoryBackup([secondReceipt,...importedNewer],'2026-07-14T12:39:00Z');"
            "const newerMerge=w.mergeRequestHistoryBackup(currentNewer,newerBackup);"
            "const fullHistory=w.parseRequestHistory(Array.from({length:25},(_,i)=>({...receipt,requestId:`gca_local_req_current${String(i).padStart(3,'0')}`,createdAt:new Date(Date.parse('2026-07-15T00:00:00Z')+i*1000).toISOString(),updatedAt:new Date(Date.parse('2026-07-15T00:00:00Z')+i*1000).toISOString()})));"
            "const cappedMerge=w.mergeRequestHistoryBackup(fullHistory,backup);"
            "const removed=w.removeRequestReceipt(copied,request.requestId);"
            "const sensitive=w.buildServiceRequest({serviceId:'backtest-lab-run',email:'member@example.com',title:'Review sample',summary:'My private key should never be included here.',marketContext:''},snapshot,'2026-07-14T12:30:00Z');"
            "const expired=w.parseMemberSnapshot(raw,Date.parse('2026-08-14T00:00:01Z'));"
            "const journalRows=[{id:'a',date:'2026-07-01',market:'BTC/USDT',direction:'long',returnPercent:2,setup:'breakout',notes:'plan',createdAt:'2026-07-01T00:00:00Z'},{id:'b',date:'2026-07-02',market:'ETH/USDT',direction:'short',returnPercent:-1,setup:'retest',notes:'stop',createdAt:'2026-07-02T00:00:00Z'}];"
            "const journal=w.summarizeJournal(JSON.stringify(j.buildBackup(journalRows,'2026-07-14T12:39:00Z')),j);"
            "const trainingAnswers=Object.fromEntries(t.questions.map(q=>[q.id,q.correctOptionId]));"
            "const trainingResult=t.evaluateAnswers(trainingAnswers);"
            "const trainingReceipt=t.createAttemptReceipt(trainingResult,'2026-07-14T12:40:00Z','gca_training_member123');"
            "const training=w.summarizeTraining(JSON.stringify([trainingReceipt]),t);"
            "const researchNote=r.normalizeNote({version:1,id:'gca_note_member1234',observedOn:'2026-07-13',reviewOn:'2026-07-14',title:'China infrastructure research',theme:'Infrastructure',status:'active-research',horizon:'medium-term',evidenceState:'developing',tags:['China','Base'],thesis:'A sufficiently detailed thesis for the local member workspace summary.',evidence:'Public evidence remains under review.',catalyst:'A measurable adoption milestone.',invalidation:'Adoption evidence weakens for two review cycles.',riskNotes:'Liquidity and execution conditions remain uncertain.',sourceUrl:'https://example.com/research',createdAt:'2026-07-13T10:00:00Z',updatedAt:'2026-07-14T10:00:00Z'});"
            "const researchBackup=r.buildBackup([researchNote],'2026-07-14T12:41:00Z');"
            "const research=w.summarizeResearchNotes(JSON.stringify(researchBackup),r,Date.parse('2026-07-14T12:42:00Z'));"
            "process.stdout.write(JSON.stringify({snapshot,request,receipt,history,copied,backup,parsedBackup,invalidBackup,duplicateBackup,olderMerge,newerMerge,cappedMerge,backupStored:JSON.stringify(backup),removed,stored:JSON.stringify(copied),sensitive,expired,journal,training,research,masked:w.maskWallet(snapshot.walletAddress),services:w.SERVICE_CATALOG,backupSchema:w.REQUEST_BACKUP_SCHEMA,researchKey:w.RESEARCH_NOTES_KEY}));"
        )
        completed = subprocess.run(
            [node, "-e", script, str(module_path), str(journal_path), str(training_path), str(research_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(result["snapshot"]["remainingCredits"], 75)
        self.assertEqual(result["snapshot"]["memberStatus"], "active")
        self.assertEqual(result["masked"], "0x111111...111111")
        self.assertTrue(result["request"]["ok"])
        self.assertEqual(result["request"]["service"]["creditUnit"], 20)
        self.assertEqual(result["request"]["creditCheck"]["status"], "credits-available")
        self.assertEqual(result["request"]["requestId"], "gca_local_req_test1234")
        self.assertIn("gca_local_req_test1234", result["request"]["packet"])
        self.assertIn("request creation does not deduct credits", result["request"]["packet"])
        self.assertEqual(result["receipt"]["localAction"], "packet_created")
        self.assertEqual(result["receipt"]["deviceCreditsAvailable"], 75)
        self.assertEqual(len(result["history"]), 1)
        self.assertEqual(result["copied"][0]["localAction"], "packet_copied")
        self.assertEqual(result["backupSchema"], "gca-member-request-history-backup-v1")
        self.assertEqual(result["backup"]["schema"], "gca-member-request-history-backup-v1")
        self.assertEqual(result["parsedBackup"], result["backup"])
        self.assertIsNone(result["invalidBackup"])
        self.assertIsNone(result["duplicateBackup"])
        self.assertEqual(result["olderMerge"]["updatedReceiptCount"], 0)
        self.assertEqual(result["olderMerge"]["receipts"][0]["localAction"], "packet_downloaded")
        self.assertEqual(result["newerMerge"]["addedReceiptCount"], 1)
        self.assertEqual(result["newerMerge"]["updatedReceiptCount"], 1)
        self.assertEqual(len(result["newerMerge"]["receipts"]), 2)
        self.assertEqual(result["cappedMerge"]["addedReceiptCount"], 0)
        self.assertEqual(len(result["cappedMerge"]["receipts"]), 25)
        for forbidden in (
            "contactEmail",
            "walletAddress",
            "requestTitle",
            "requestSummary",
            "marketContext",
            "requestPacket",
            "private@example.com",
            "0x1111111111111111111111111111111111111111",
            "Review completed sample",
            "drawdown and execution discipline",
            "BTC/USDT",
        ):
            self.assertNotIn(forbidden, result["backupStored"])
        self.assertEqual(result["removed"], [])
        self.assertNotIn("member@example.com", result["stored"].lower())
        self.assertNotIn("Review completed sample", result["stored"])
        self.assertNotIn("drawdown and execution discipline", result["stored"])
        self.assertNotIn("BTC/USDT", result["stored"])
        self.assertNotIn("0x1111111111111111111111111111111111111111", result["stored"])
        self.assertEqual(result["sensitive"], {"ok": False, "error": "sensitive-content"})
        self.assertIsNone(result["expired"])
        self.assertEqual(result["journal"]["count"], 2)
        self.assertAlmostEqual(result["journal"]["winRatePercent"], 50)
        self.assertAlmostEqual(result["journal"]["averageReturnPercent"], 0.5)
        self.assertEqual(result["training"]["count"], 1)
        self.assertEqual(result["training"]["latestPercent"], 100)
        self.assertEqual(result["training"]["bestPercent"], 100)
        self.assertEqual(result["training"]["foundationReadyCount"], 1)
        self.assertEqual(result["training"]["latestMissedQuestionIds"], [])
        self.assertEqual(result["researchKey"], "gca_research_notes_v1")
        self.assertEqual(result["research"]["count"], 1)
        self.assertEqual(result["research"]["activeCount"], 1)
        self.assertEqual(result["research"]["sourcedCount"], 1)
        self.assertEqual(result["research"]["dueReviewCount"], 1)
        self.assertEqual(len(result["services"]), 9)
        self.assertEqual({item["id"]: item["creditUnit"] for item in result["services"]}["support-review-queue"], 0)
        training_service = next(item for item in result["services"] if item["id"] == "risk-control-training")
        self.assertEqual(training_service["previewUrl"], "risk-training.html")
        self.assertEqual(training_service["stage"], "public-preview")
        research_service = next(item for item in result["services"] if item["id"] == "member-research-notes")
        self.assertEqual(research_service["previewUrl"], "research-notes.html")
        self.assertEqual(research_service["stage"], "public-preview")
        portfolio_service = next(item for item in result["services"] if item["id"] == "portfolio-risk-map")
        self.assertEqual(portfolio_service["creditUnit"], 15)
        self.assertEqual(portfolio_service["previewUrl"], "portfolio-risk.html")
        self.assertEqual(portfolio_service["stage"], "public-preview")

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

    def test_risk_training_is_bilingual_transparent_and_client_side(self):
        page = (SITE / "risk-training.html").read_text()
        engine = (SITE / "assets" / "risk-training.js").read_text()
        product = json.loads((SITE / "product.json").read_text())
        credits = json.loads((SITE / "credits.json").read_text())

        for element_id in (
            "trainingForm",
            "questionList",
            "answeredCount",
            "scorePercent",
            "trainingStatus",
            "checkTraining",
            "resetTraining",
            "trainingResult",
            "statusBadge",
            "categoryResults",
            "reviewPlan",
            "draftStatus",
            "attemptHistory",
            "attemptHistoryTitle",
            "attemptHistoryCount",
            "latestAttemptScore",
            "bestAttemptScore",
            "foundationReadyCount",
            "attemptHistoryList",
            "exportTrainingBackup",
            "importTrainingBackup",
            "trainingBackupStatus",
            "clearAttemptHistory",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn("Risk Discipline Training", page)
        self.assertIn("风控纪律训练", page)
        self.assertIn('src="assets/risk-training.js"', page)
        self.assertIn("engine.evaluateAnswers", page)
        self.assertIn("engine.buildReviewPlan", page)
        self.assertIn("engine.createTrainingDraft", page)
        self.assertIn("engine.createAttemptReceipt", page)
        self.assertIn("engine.summarizeAttemptHistory", page)
        self.assertIn("engine.buildTrainingBackup", page)
        self.assertIn("engine.parseTrainingBackup", page)
        self.assertIn("engine.mergeTrainingBackup", page)
        self.assertIn("URL.createObjectURL", page)
        self.assertIn("await file.text()", page)
        self.assertIn('const DRAFT_KEY = "gca_risk_training_draft_v1"', engine)
        self.assertIn('const HISTORY_KEY = "gca_risk_training_history_v1"', engine)
        self.assertIn('const BACKUP_SCHEMA = "gca-risk-training-backup-v1"', engine)
        self.assertIn("const HISTORY_LIMIT = 20", engine)
        self.assertIn('percent >= 75', engine)
        self.assertIn('"NOT_COMPLETE"', engine)
        self.assertIn('"REVIEW_REQUIRED"', engine)
        self.assertIn('"FOUNDATION_READY"', engine)
        self.assertIn("does not fetch prices", page)
        self.assertIn("does not", page)
        self.assertIn("certification", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)

        module = next(item for item in product["productModules"] if item["id"] == "risk-control-training")
        self.assertEqual(module["status"], "public-client-side-preview-live")
        self.assertEqual(module["publicUrl"], "https://gcagochina.com/risk-training.html")
        self.assertFalse(module["issuesCertification"])
        self.assertTrue(module["browserLocalDraft"])
        self.assertTrue(module["browserLocalAttemptHistory"])
        self.assertFalse(module["storesSelectedAnswersInHistory"])
        self.assertFalse(module["storesOnServer"])
        self.assertTrue(module["portableJsonBackup"])
        self.assertFalse(module["backupContainsIdentityData"])
        self.assertTrue(module["backupMayContainUnfinishedOptionIds"])
        service = next(item for item in credits["serviceCatalog"] if item["id"] == "risk-control-training")
        self.assertEqual(service["publicPreview"]["url"], "https://gcagochina.com/risk-training.html")
        self.assertFalse(service["publicPreview"]["deductsCredits"])
        self.assertFalse(service["publicPreview"]["issuesCertification"])
        self.assertTrue(service["publicPreview"]["browserLocalDraft"])
        self.assertTrue(service["publicPreview"]["browserLocalAttemptHistory"])
        self.assertFalse(service["publicPreview"]["storesSelectedAnswersInHistory"])
        self.assertFalse(service["publicPreview"]["storesOnServer"])
        self.assertTrue(service["publicPreview"]["portableJsonBackup"])
        self.assertFalse(service["publicPreview"]["backupContainsIdentityData"])
        self.assertTrue(service["publicPreview"]["backupMayContainUnfinishedOptionIds"])

    def test_risk_training_engine_scores_threshold_and_builds_review_plan(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "risk-training.js"
        script = (
            "const e=require(process.argv[1]);"
            "const correct=Object.fromEntries(e.questions.map(q=>[q.id,q.correctOptionId]));"
            "const wrongFor=q=>q.options.find(o=>o.id!==q.correctOptionId).id;"
            "const partial={[e.questions[0].id]:e.questions[0].correctOptionId};"
            "const five=Object.fromEntries(e.questions.map((q,i)=>[q.id,i<5?q.correctOptionId:wrongFor(q)]));"
            "const six=Object.fromEntries(e.questions.map((q,i)=>[q.id,i<6?q.correctOptionId:wrongFor(q)]));"
            "const results={partial:e.evaluateAnswers(partial),review:e.evaluateAnswers(five),threshold:e.evaluateAnswers(six),perfect:e.evaluateAnswers(correct)};"
            "results.plans=Object.fromEntries(Object.entries(results).map(([k,v])=>[k,e.buildReviewPlan(v)]));"
            "const draft=e.createTrainingDraft({...partial,unknown:'ignored'},'2026-07-15T00:00:00Z');"
            "const parsedDraft=e.parseTrainingDraft(JSON.stringify(draft));"
            "const receipt=e.createAttemptReceipt(results.review,'2026-07-15T01:00:00Z','gca_training_review123');"
            "const perfectReceipt=e.createAttemptReceipt(results.perfect,'2026-07-15T02:00:00Z','gca_training_perfect1');"
            "const history=e.upsertAttemptHistory([receipt],perfectReceipt);"
            "const duplicate=e.upsertAttemptHistory(history,{...receipt,completedAt:'2026-07-15T03:00:00Z'});"
            "const capped=e.parseAttemptHistory(Array.from({length:22},(_,i)=>({...perfectReceipt,attemptId:`gca_training_attempt${String(i).padStart(3,'0')}`,completedAt:new Date(Date.parse('2026-07-01T00:00:00Z')+i*1000).toISOString()})));"
            "const invalid=e.parseAttemptHistory([{...receipt,missedQuestionIds:['unknown']}]);"
            "const backup=e.buildTrainingBackup(history,draft,'2026-07-15T04:00:00Z');"
            "const parsedBackup=e.parseTrainingBackup(JSON.stringify(backup));"
            "const invalidBackup=e.parseTrainingBackup({...backup,draft:{...draft,answers:{...draft.answers,unknown:'invalid'}}});"
            "const duplicateBackup=e.parseTrainingBackup({...backup,history:[...backup.history,backup.history[0]]});"
            "const currentDraft=e.createTrainingDraft({[e.questions[0].id]:wrongFor(e.questions[0])},'2026-07-15T00:30:00Z');"
            "const olderMerge=e.mergeTrainingBackup([perfectReceipt],currentDraft,backup);"
            "const newerDraft=e.createTrainingDraft({[e.questions[1].id]:e.questions[1].correctOptionId},'2026-07-15T05:00:00Z');"
            "const newerBackup=e.buildTrainingBackup([receipt],newerDraft,'2026-07-15T06:00:00Z');"
            "const newerMerge=e.mergeTrainingBackup([perfectReceipt],currentDraft,newerBackup);"
            "const fullCurrent=e.parseAttemptHistory(Array.from({length:20},(_,i)=>({...perfectReceipt,attemptId:`gca_training_current${String(i).padStart(3,'0')}`,completedAt:new Date(Date.parse('2026-07-15T10:00:00Z')+i*1000).toISOString()})));"
            "const droppedBackup=e.buildTrainingBackup([receipt],null,'2026-07-15T12:00:00Z');"
            "const cappedMerge=e.mergeTrainingBackup(fullCurrent,null,droppedBackup);"
            "results.persistence={draft,parsedDraft,receipt,history,duplicate,capped,invalid,summary:e.summarizeAttemptHistory(history),stored:JSON.stringify(history),keys:[e.DRAFT_KEY,e.HISTORY_KEY,e.BACKUP_SCHEMA,e.HISTORY_LIMIT],backup,parsedBackup,invalidBackup,duplicateBackup,olderMerge,newerMerge,cappedMerge,backupStored:JSON.stringify(backup)};"
            "process.stdout.write(JSON.stringify(results));"
        )
        completed = subprocess.run(
            [node, "-e", script, str(module_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(result["partial"]["status"], "NOT_COMPLETE")
        self.assertEqual(result["partial"]["answeredCount"], 1)
        self.assertEqual(len(result["plans"]["partial"]), 7)
        self.assertEqual(result["review"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["review"]["correctCount"], 5)
        self.assertEqual(result["review"]["percent"], 63)
        self.assertEqual(len(result["plans"]["review"]), 3)
        self.assertEqual(result["threshold"]["status"], "FOUNDATION_READY")
        self.assertEqual(result["threshold"]["percent"], 75)
        self.assertEqual(result["perfect"]["status"], "FOUNDATION_READY")
        self.assertEqual(result["perfect"]["percent"], 100)
        self.assertEqual(result["plans"]["perfect"], [])
        persistence = result["persistence"]
        self.assertEqual(
            persistence["keys"],
            ["gca_risk_training_draft_v1", "gca_risk_training_history_v1", "gca-risk-training-backup-v1", 20],
        )
        self.assertEqual(persistence["draft"]["answers"], {"position-size": "risk-budget"})
        self.assertEqual(persistence["parsedDraft"], persistence["draft"])
        self.assertEqual(persistence["receipt"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(persistence["receipt"]["missedQuestionIds"], ["journal-review", "api-security", "simulation-first"])
        self.assertEqual(len(persistence["history"]), 2)
        self.assertEqual(persistence["history"][0]["attemptId"], "gca_training_perfect1")
        self.assertEqual(len(persistence["duplicate"]), 2)
        self.assertEqual(persistence["duplicate"][0]["attemptId"], "gca_training_review123")
        self.assertEqual(len(persistence["capped"]), 20)
        self.assertEqual(persistence["invalid"], [])
        self.assertEqual(persistence["summary"]["count"], 2)
        self.assertEqual(persistence["summary"]["latestPercent"], 100)
        self.assertEqual(persistence["summary"]["bestPercent"], 100)
        self.assertEqual(persistence["summary"]["foundationReadyCount"], 1)
        for forbidden in ("selectedOptionId", "correctOptionId", '"answers"', "wallet", "email"):
            self.assertNotIn(forbidden, persistence["stored"])
        self.assertEqual(persistence["backup"]["schema"], "gca-risk-training-backup-v1")
        self.assertEqual(persistence["backup"]["version"], 1)
        self.assertEqual(persistence["parsedBackup"], persistence["backup"])
        self.assertIsNone(persistence["invalidBackup"])
        self.assertIsNone(persistence["duplicateBackup"])
        self.assertFalse(persistence["olderMerge"]["importedDraftApplied"])
        self.assertEqual(persistence["olderMerge"]["draft"]["savedAt"], "2026-07-15T00:30:00.000Z")
        self.assertTrue(persistence["newerMerge"]["importedDraftApplied"])
        self.assertEqual(persistence["newerMerge"]["draft"]["savedAt"], "2026-07-15T05:00:00.000Z")
        self.assertEqual(persistence["newerMerge"]["addedHistoryCount"], 1)
        self.assertEqual(len(persistence["newerMerge"]["history"]), 2)
        self.assertEqual(persistence["cappedMerge"]["addedHistoryCount"], 0)
        self.assertEqual(len(persistence["cappedMerge"]["history"]), 20)
        self.assertIn('"answers"', persistence["backupStored"])
        for forbidden in ("wallet", "email", "market", "order", "selectedOptionId", "correctOptionId"):
            self.assertNotIn(forbidden, persistence["backupStored"])

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

        for mode in ("learn", "prepare", "research", "review", "all"):
            self.assertIn(f'data-mode="{mode}"', page)
        for tool_id, url in (
            ("risk-calculator", "risk-calculator.html"),
            ("risk-warning", "risk-warning.html"),
            ("entry-ready", "entry-ready.html"),
            ("backtest-lab", "backtest-lab.html"),
            ("liquidation-replay", "liquidation-replay.html"),
            ("risk-training", "risk-training.html"),
            ("research-notes", "research-notes.html"),
            ("trade-plans", "trade-plans.html"),
            ("portfolio-risk", "portfolio-risk.html"),
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
        self.assertIn("Ten Risk and Research Tools", page)
        self.assertIn('data-tool="trade-journal"', page)
        self.assertIn('"riskToolsWorkspace": "https://gcagochina.com/tools.html"', product)
        self.assertIn('"riskToolsWorkspace": "https://gcagochina.com/tools.html"', credits)
        self.assertIn('["Tools", "tools.html"]', (SITE / "assets" / "gca-site.js").read_text())
        public_checker = (ROOT / "tools" / "check_public_site.py").read_text()
        self.assertIn('(\"/tools.html\", validate_risk_tools_page)', public_checker)
        self.assertIn("prepare:", engine)
        self.assertIn("research:", engine)
        self.assertIn("review:", engine)
        self.assertIn("learn:", engine)

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
            "learn": ["risk-training", "risk-calculator", "risk-warning", "entry-ready", "trade-journal"],
            "prepare": ["trade-plans", "risk-calculator", "portfolio-risk", "risk-warning", "entry-ready"],
            "research": ["research-notes", "trade-plans", "risk-calculator", "portfolio-risk", "risk-warning", "entry-ready", "trade-journal", "backtest-lab"],
            "review": ["liquidation-replay", "trade-journal", "trade-plans", "risk-calculator", "portfolio-risk", "risk-warning", "entry-ready"],
            "all": ["risk-training", "research-notes", "trade-plans", "risk-calculator", "portfolio-risk", "risk-warning", "entry-ready", "backtest-lab", "liquidation-replay", "trade-journal"],
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

    def test_research_notes_is_local_structured_and_portable(self):
        page = (SITE / "research-notes.html").read_text()
        engine = (SITE / "assets" / "research-notes.js").read_text()
        product = json.loads((SITE / "product.json").read_text())
        credits = json.loads((SITE / "credits.json").read_text())

        for element_id in (
            "researchForm",
            "observedOn",
            "reviewOn",
            "noteTitle",
            "noteTheme",
            "noteStatus",
            "noteHorizon",
            "evidenceState",
            "noteTags",
            "noteThesis",
            "noteEvidence",
            "noteCatalyst",
            "noteInvalidation",
            "noteRisks",
            "sourceUrl",
            "saveNote",
            "resetNote",
            "cancelEdit",
            "researchStatus",
            "researchFilters",
            "filterQuery",
            "filterStatus",
            "filterHorizon",
            "filterEvidence",
            "filterTag",
            "filterDueOnly",
            "resetResearchFilters",
            "filterResearchStatus",
            "researchNoteCount",
            "researchActiveCount",
            "researchSourcedCount",
            "researchDueCount",
            "exportResearchJson",
            "importResearchJson",
            "clearResearchNotes",
            "researchRows",
            "emptyResearch",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn('src="assets/research-notes.js"', page)
        self.assertIn("window.localStorage.setItem(engine.STORAGE_KEY", page)
        self.assertIn("window.localStorage.removeItem(engine.STORAGE_KEY)", page)
        self.assertIn("engine.normalizeNote", page)
        self.assertIn("engine.filterNotes", page)
        self.assertIn("engine.summarizeNotes", page)
        self.assertIn("engine.buildBackup", page)
        self.assertIn("engine.parseBackup", page)
        self.assertIn("engine.mergeBackup", page)
        self.assertIn("engine.buildTradePlanHandoff(note)", page)
        self.assertIn("it never saves a plan automatically", page)
        self.assertIn("URL.createObjectURL", page)
        self.assertIn("await file.text()", page)
        self.assertIn('source.target = "_blank"', page)
        self.assertIn('source.rel = "noopener noreferrer"', page)
        self.assertIn("textContent = note.title", page)
        self.assertIn("browser localStorage only", page)
        self.assertIn("does not upload research", page)
        self.assertIn("Do not enter private keys", page)
        self.assertNotIn("innerHTML", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('const STORAGE_KEY = "gca_research_notes_v1"', engine)
        self.assertIn('const SCHEMA = "gca-research-notes-v1"', engine)
        self.assertIn("const MAX_NOTES = 200", engine)

        module = next(item for item in product["productModules"] if item["id"] == "member-research-notes")
        self.assertEqual(module["status"], "public-client-side-preview-live")
        self.assertEqual(module["publicUrl"], "https://gcagochina.com/research-notes.html")
        self.assertTrue(module["browserLocalNotes"])
        self.assertTrue(module["portableJsonBackup"])
        self.assertTrue(module["backupContainsUserEnteredResearchContent"])
        self.assertTrue(module["tradePlanHandoff"])
        self.assertTrue(module["handoffUsesUrlFragment"])
        self.assertFalse(module["handoffAutoSavesPlan"])
        self.assertFalse(module["handoffIncludesSourceUrl"])
        self.assertFalse(module["storesOnServer"])
        self.assertFalse(module["collectsIdentityFields"])
        service = next(item for item in credits["serviceCatalog"] if item["id"] == "member-research-notes")
        self.assertEqual(service["publicPreview"]["url"], "https://gcagochina.com/research-notes.html")
        self.assertFalse(service["publicPreview"]["deductsCredits"])
        self.assertEqual(product["officialLinks"]["researchNotes"], "https://gcagochina.com/research-notes.html")
        self.assertEqual(credits["officialLinks"]["researchNotes"], "https://gcagochina.com/research-notes.html")

    def test_research_notes_engine_validates_filters_and_merges_backups(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "research-notes.js"
        script = (
            "const r=require(process.argv[1]);"
            "const base={version:1,id:'gca_note_alpha1234',observedOn:'2026-07-10',reviewOn:'2026-07-15',title:'China infrastructure thesis',theme:'Infrastructure',status:'active-research',horizon:'medium-term',evidenceState:'developing',tags:['China','Base'],thesis:'A sufficiently detailed thesis for validation and scheduled review.',evidence:'Public adoption evidence is developing.',catalyst:'A measurable product adoption milestone.',invalidation:'Adoption evidence weakens across two review cycles.',riskNotes:'Liquidity, execution, and policy uncertainty remain material.',sourceUrl:'https://example.com/source#section',createdAt:'2026-07-10T10:00:00Z',updatedAt:'2026-07-10T10:00:00Z'};"
            "const first=r.normalizeNote(base);"
            "const second=r.normalizeNote({...base,id:'gca_note_beta12345',reviewOn:'',title:'Education access thesis',theme:'Education',status:'watching',horizon:'long-term',evidenceState:'unverified',tags:['China','Education'],sourceUrl:'',createdAt:'2026-07-11T10:00:00Z',updatedAt:'2026-07-11T10:00:00Z'});"
            "const notes=r.orderNotes([first,second]);"
            "const summary=r.summarizeNotes(notes,Date.parse('2026-07-16T00:00:00Z'));"
            "const backup=r.buildBackup(notes,'2026-07-16T01:00:00Z');"
            "const parsed=r.parseBackup(JSON.stringify(backup));"
            "const newer={...first,evidenceState:'supported',updatedAt:'2026-07-17T10:00:00.000Z'};"
            "const imported=r.buildBackup([newer,r.normalizeNote({...base,id:'gca_note_gamma1234',title:'Base adoption evidence',theme:'Adoption',status:'needs-review',horizon:'short-term',evidenceState:'conflicting',tags:['Base'],createdAt:'2026-07-12T10:00:00Z',updatedAt:'2026-07-12T10:00:00Z'})],'2026-07-17T11:00:00Z');"
            "const merged=r.mergeBackup(notes,imported);"
            "const invalidSecret=r.normalizeNote({...base,thesis:'Store my private key here for later use.'});"
            "const invalidSource=r.normalizeNote({...base,sourceUrl:'http://example.com/private'});"
            "const invalidExtra=r.parseBackup({...backup,unexpected:true});"
            "const duplicate=r.parseBackup({...backup,notes:[backup.notes[0],backup.notes[0]]});"
            "process.stdout.write(JSON.stringify({first,notes,summary,backup,parsed,merged,invalidSecret,invalidSource,invalidExtra,duplicate,query:r.filterNotes(notes,{query:'education'}),tag:r.filterNotes(notes,{tag:'base'}),due:r.filterNotes(notes,{dueOnly:true},Date.parse('2026-07-16T00:00:00Z'))}));"
        )
        completed = subprocess.run(
            [node, "-e", script, str(module_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(result["first"]["sourceUrl"], "https://example.com/source")
        self.assertEqual(len(result["notes"]), 2)
        self.assertEqual(result["summary"]["count"], 2)
        self.assertEqual(result["summary"]["activeCount"], 2)
        self.assertEqual(result["summary"]["sourcedCount"], 1)
        self.assertEqual(result["summary"]["dueReviewCount"], 1)
        self.assertEqual(result["backup"]["schema"], "gca-research-notes-v1")
        self.assertEqual(result["parsed"], result["backup"])
        self.assertEqual(result["merged"]["addedNoteCount"], 1)
        self.assertEqual(result["merged"]["updatedNoteCount"], 1)
        self.assertEqual(result["merged"]["droppedNewNoteCount"], 0)
        self.assertEqual(len(result["merged"]["notes"]), 3)
        self.assertEqual(result["merged"]["notes"][0]["evidenceState"], "supported")
        self.assertIsNone(result["invalidSecret"])
        self.assertIsNone(result["invalidSource"])
        self.assertIsNone(result["invalidExtra"])
        self.assertIsNone(result["duplicate"])
        self.assertEqual(len(result["query"]), 1)
        self.assertEqual(len(result["tag"]), 1)
        self.assertEqual(len(result["due"]), 1)

    def test_trade_plan_ledger_is_local_structured_and_portable(self):
        page = (SITE / "trade-plans.html").read_text()
        engine = (SITE / "assets" / "trade-plans.js").read_text()
        product = json.loads((SITE / "product.json").read_text())
        credits = json.loads((SITE / "credits.json").read_text())

        for element_id in (
            "tradePlanForm",
            "planSymbol",
            "planDirection",
            "planTimeframe",
            "planWorkflowStatus",
            "planPlannedFor",
            "planOrderType",
            "planThesis",
            "planInvalidation",
            "planEntry",
            "planStop",
            "planTarget",
            "planEquity",
            "planRiskPercent",
            "planLeverage",
            "planFeeBps",
            "planSlippageBps",
            "planExposureLimit",
            "planVolatility",
            "planLiquidityCoverage",
            "positionSized",
            "maxLossAccepted",
            "liquidityChecked",
            "volatilityReviewed",
            "noRevengeTrade",
            "noFomo",
            "exitPlanDefined",
            "simulationReviewed",
            "saveTradePlan",
            "resetTradePlan",
            "cancelTradePlanEdit",
            "tradePlanStatus",
            "planReadiness",
            "planRiskBudget",
            "planQuantity",
            "planNotional",
            "planPlannedLoss",
            "planMargin",
            "planExposure",
            "planRewardRisk",
            "planFindings",
            "handoffCalculator",
            "handoffPortfolio",
            "handoffWarning",
            "handoffEntryReady",
            "handoffReplay",
            "handoffJournal",
            "tradePlanCount",
            "activePlanCount",
            "readyPlanCount",
            "blockedPlanCount",
            "duePlanCount",
            "tradePlanFilters",
            "filterPlanQuery",
            "filterPlanStatus",
            "filterPlanReadiness",
            "filterPlanDue",
            "resetPlanFilters",
            "exportTradePlans",
            "importTradePlans",
            "clearTradePlans",
            "filterPlanStatusText",
            "tradePlanRows",
            "emptyTradePlans",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn('src="assets/trade-plans.js"', page)
        self.assertIn("window.localStorage.setItem(engine.STORAGE_KEY", page)
        self.assertIn("window.localStorage.removeItem(engine.STORAGE_KEY)", page)
        self.assertIn("engine.normalizePlan", page)
        self.assertIn("engine.analyzePlan", page)
        self.assertIn("engine.summarizePlans", page)
        self.assertIn("engine.filterPlans", page)
        self.assertIn("engine.buildHandoffLinks", page)
        self.assertIn("engine.parseResearchHandoff", page)
        self.assertIn("applyResearchHandoff", page)
        self.assertIn("no plan was saved automatically", page)
        self.assertIn("never supplies realized return", page)
        self.assertIn("engine.buildBackup", page)
        self.assertIn("engine.parseBackup", page)
        self.assertIn("engine.mergeBackup", page)
        self.assertIn("URL.createObjectURL", page)
        self.assertIn("await file.text()", page)
        self.assertIn("not a trading signal", page)
        self.assertIn("may remain in browser history", page)
        self.assertIn("Do not enter private keys", page)
        self.assertNotIn("innerHTML", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('const STORAGE_KEY = "gca_trade_plans_v1"', engine)
        self.assertIn('const SCHEMA = "gca-trade-plans-v1"', engine)
        self.assertIn("const MAX_PLANS = 100", engine)

        module = next(item for item in product["productModules"] if item["id"] == "trade-plan-ledger")
        self.assertEqual(module["status"], "public-client-side-preview-live")
        self.assertEqual(module["publicUrl"], "https://gcagochina.com/trade-plans.html")
        self.assertTrue(module["browserLocalPlans"])
        self.assertTrue(module["portableJsonBackup"])
        self.assertTrue(module["backupContainsUserEnteredPlanDetails"])
        self.assertTrue(module["researchHandoff"])
        self.assertTrue(module["completedPlanJournalHandoff"])
        self.assertTrue(module["handoffUsesUrlFragment"])
        self.assertFalse(module["handoffAutoSavesData"])
        for field in ("storesOnServer", "connectsWallet", "connectsExchange", "fetchesMarketData", "placesOrders", "deductsCredits"):
            self.assertFalse(module[field])

        self.assertEqual(product["officialLinks"]["tradePlanLedger"], "https://gcagochina.com/trade-plans.html")
        self.assertEqual(credits["officialLinks"]["tradePlanLedger"], "https://gcagochina.com/trade-plans.html")
        self.assertNotIn("trade-plan-ledger", {item["id"] for item in credits["serviceCatalog"]})

    def test_trade_plan_engine_calculates_readiness_handoffs_and_backups(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "trade-plans.js"
        workspace_path = SITE / "assets" / "member-workspace.js"
        script = (
            "const t=require(process.argv[1]);const w=require(process.argv[2]);"
            "const base={version:1,id:'gca_plan_ready1234',createdAt:'2026-07-18T00:00:00Z',updatedAt:'2026-07-18T00:00:00Z',plannedFor:'2026-07-18',symbol:'btc/usdt',direction:'long',timeframe:'4h',workflowStatus:'under-review',thesis:'A sufficiently detailed manual trade thesis for risk review.',invalidation:'Close below the defined structural level.',entry:100,stop:95,target:112,equity:10000,riskPercent:1,leverage:2,feeBps:20,slippageBps:10,exposureLimitPercent:50,volatilityPercent:3,liquidityCoverage:15,orderType:'limit',positionSized:true,maxLossAccepted:true,liquidityChecked:true,volatilityReviewed:true,noRevengeTrade:true,noFomo:true,exitPlanDefined:true,simulationReviewed:true};"
            "const ready=t.normalizePlan(base);"
            "const blocked=t.normalizePlan({...base,id:'gca_plan_blocked1234',updatedAt:'2026-07-18T00:01:00Z',workflowStatus:'draft',thesis:'A distinct blocked setup retained for deterministic risk review.',riskPercent:4,leverage:25,exposureLimitPercent:10,positionSized:false,maxLossAccepted:false,liquidityChecked:false,volatilityReviewed:false,noRevengeTrade:false,noFomo:false,exitPlanDefined:false,simulationReviewed:false});"
            "const archived=t.normalizePlan({...base,id:'gca_plan_archive1234',updatedAt:'2026-07-18T00:02:00Z',plannedFor:'2026-07-17',symbol:'eth/usdt',workflowStatus:'completed'});"
            "const plans=t.orderPlans([ready,blocked,archived]);"
            "const readyAnalysis=t.analyzePlan(ready);const blockedAnalysis=t.analyzePlan(blocked);const archivedAnalysis=t.analyzePlan(archived);"
            "const summary=t.summarizePlans(plans,Date.parse('2026-07-19T00:00:00Z'));"
            "const backup=t.buildBackup(plans,'2026-07-18T01:00:00Z');const parsed=t.parseBackup(JSON.stringify(backup));"
            "const invalidExtra=t.parseBackup({...backup,unexpected:true});const duplicate=t.parseBackup({...backup,plans:[backup.plans[0],backup.plans[0]]});"
            "const sensitive=t.normalizePlan({...base,id:'gca_plan_secret1234',thesis:'Store the private key inside this detailed trade thesis.'});"
            "const invalidStop=t.normalizePlan({...base,id:'gca_plan_badstop1234',stop:101});"
            "const newerReady=t.normalizePlan({...ready,updatedAt:'2026-07-18T02:00:00Z',thesis:'An updated and sufficiently detailed manual trade thesis for review.'});"
            "const added=t.normalizePlan({...ready,id:'gca_plan_added12345',createdAt:'2026-07-18T02:01:00Z',updatedAt:'2026-07-18T02:01:00Z',plannedFor:'2026-07-20',symbol:'sol/usdt'});"
            "const imported=t.buildBackup([newerReady,added],'2026-07-18T03:00:00Z');const merged=t.mergeBackup(plans,imported);"
            "const links=t.buildHandoffLinks(ready);"
            "const filters={ready:t.filterPlans(plans,{readiness:'READY_FOR_REVIEW'},Date.parse('2026-07-19T00:00:00Z')),completed:t.filterPlans(plans,{workflowStatus:'completed'},Date.parse('2026-07-19T00:00:00Z')),due:t.filterPlans(plans,{dueOnly:true},Date.parse('2026-07-19T00:00:00Z')),search:t.filterPlans(plans,{query:'eth'},Date.parse('2026-07-19T00:00:00Z'))};"
            "const workspace=w.summarizeTradePlans(JSON.stringify(backup),t,Date.parse('2026-07-19T00:00:00Z'));"
            "process.stdout.write(JSON.stringify({ready,readyAnalysis,blockedAnalysis,archivedAnalysis,summary,backup,parsed,invalidExtra,duplicate,sensitive,invalidStop,merged,links,filters,workspace,emptyWorkspace:w.summarizeTradePlans('{}',t,Date.parse('2026-07-19T00:00:00Z')),removed:t.removePlan(plans,ready.id)}));"
        )
        completed = subprocess.run(
            [node, "-e", script, str(module_path), str(workspace_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(result["ready"]["symbol"], "BTC/USDT")
        self.assertEqual(result["readyAnalysis"]["status"], "READY_FOR_REVIEW")
        self.assertEqual(result["readyAnalysis"]["blockerCount"], 0)
        self.assertEqual(result["readyAnalysis"]["warningCount"], 0)
        self.assertAlmostEqual(result["readyAnalysis"]["riskBudget"], 100)
        self.assertAlmostEqual(result["readyAnalysis"]["positionQuantity"], 18.8679245283)
        self.assertAlmostEqual(result["readyAnalysis"]["plannedLoss"], 100)
        self.assertAlmostEqual(result["readyAnalysis"]["exposurePercent"], 18.8679245283)
        self.assertAlmostEqual(result["readyAnalysis"]["rewardRisk"], 2.2641509434)
        self.assertEqual(result["blockedAnalysis"]["status"], "NOT_READY")
        self.assertGreaterEqual(result["blockedAnalysis"]["blockerCount"], 8)
        self.assertIn("RISK_ABOVE_HARD_LIMIT", {item["code"] for item in result["blockedAnalysis"]["findings"]})
        self.assertIn("EXPOSURE_LIMIT_EXCEEDED", {item["code"] for item in result["blockedAnalysis"]["findings"]})
        self.assertEqual(result["archivedAnalysis"]["status"], "COMPLETED")
        self.assertEqual(result["summary"]["count"], 3)
        self.assertEqual(result["summary"]["activeCount"], 2)
        self.assertEqual(result["summary"]["readyForReviewCount"], 1)
        self.assertEqual(result["summary"]["blockedCount"], 1)
        self.assertEqual(result["summary"]["archivedCount"], 1)
        self.assertEqual(result["summary"]["dueCount"], 2)
        self.assertEqual(result["backup"]["schema"], "gca-trade-plans-v1")
        self.assertEqual(result["parsed"], result["backup"])
        self.assertIsNone(result["invalidExtra"])
        self.assertIsNone(result["duplicate"])
        self.assertIsNone(result["sensitive"])
        self.assertIsNone(result["invalidStop"])
        self.assertEqual(result["merged"]["addedPlanCount"], 1)
        self.assertEqual(result["merged"]["updatedPlanCount"], 1)
        self.assertEqual(len(result["merged"]["plans"]), 4)
        self.assertIn("source=trade-plan", result["links"]["calculator"])
        self.assertIn("source=trade-plan", result["links"]["portfolio"])
        self.assertIn("source=trade-plan", result["links"]["warning"])
        self.assertIn("source=trade-plan", result["links"]["entryReady"])
        self.assertIn("source=trade-plan", result["links"]["replay"])
        self.assertEqual(len(result["filters"]["ready"]), 1)
        self.assertEqual(len(result["filters"]["completed"]), 1)
        self.assertEqual(len(result["filters"]["due"]), 2)
        self.assertEqual(len(result["filters"]["search"]), 1)
        self.assertEqual(result["workspace"]["count"], 3)
        self.assertEqual(result["workspace"]["readyForReviewCount"], 1)
        self.assertEqual(result["workspace"]["blockedCount"], 1)
        self.assertEqual(result["emptyWorkspace"]["count"], 0)
        self.assertEqual(len(result["removed"]), 2)

    def test_research_plan_journal_handoffs_are_bounded_and_manual(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        script = (
            "const r=require(process.argv[1]);const p=require(process.argv[2]);const j=require(process.argv[3]);"
            "const note=r.normalizeNote({version:1,id:'gca_note_flow12345',observedOn:'2026-07-18',reviewOn:'',title:'China infrastructure thesis',theme:'Infrastructure',status:'active-research',horizon:'medium-term',evidenceState:'developing',tags:['China'],thesis:'A sufficiently detailed thesis for a structured research to plan handoff.',evidence:'Public evidence remains under review.',catalyst:'A measurable adoption milestone.',invalidation:'Adoption evidence weakens across two review cycles.',riskNotes:'Liquidity and execution uncertainty remain material.',sourceUrl:'https://example.com/source',createdAt:'2026-07-18T00:00:00Z',updatedAt:'2026-07-18T00:00:00Z'});"
            "const noteLink=r.buildTradePlanHandoff(note);const noteFragment=noteLink.split('#')[1];const draft=p.parseResearchHandoff(noteFragment);"
            "const planBase={version:1,id:'gca_plan_flow12345',createdAt:'2026-07-18T00:00:00Z',updatedAt:'2026-07-18T00:00:00Z',plannedFor:'2026-07-18',symbol:'btc/usdt',direction:'long',timeframe:'4h',workflowStatus:'completed',thesis:draft.thesis,invalidation:draft.invalidation,entry:100,stop:95,target:112,equity:10000,riskPercent:1,leverage:2,feeBps:20,slippageBps:10,exposureLimitPercent:50,volatilityPercent:3,liquidityCoverage:15,orderType:'limit',positionSized:true,maxLossAccepted:true,liquidityChecked:true,volatilityReviewed:true,noRevengeTrade:true,noFomo:true,exitPlanDefined:true,simulationReviewed:true};"
            "const completed=p.normalizePlan(planBase);const completedLinks=p.buildHandoffLinks(completed);const activeLinks=p.buildHandoffLinks({...completed,workflowStatus:'under-review'});const journalFragment=completedLinks.journal.split('#')[1];"
            "const journalDraft=j.parseTradePlanHandoff(journalFragment);const secretResearch=new URLSearchParams({source:'research-note',title:'Valid title',theme:'Theme',thesis:'A sufficiently detailed private key research thesis.',invalidation:'A valid invalidation condition.',riskNotes:'A sufficiently detailed risk statement.'}).toString();"
            "const unicodeNote=r.normalizeNote({...note,id:'gca_note_unicode123',title:'中国基础设施研究计划',theme:'基础设施',thesis:'这是一个用于验证中文研究内容交接是否完整有效的详细核心论点。'.repeat(12),invalidation:'连续两次公开数据复核均显示采用趋势明显减弱。'.repeat(6),riskNotes:'流动性、执行条件和政策变化仍然存在不确定性。'.repeat(6)});const unicodeDraft=p.parseResearchHandoff(r.buildTradePlanHandoff(unicodeNote).split('#')[1]);"
            "const unicodePlan=p.normalizePlan({...completed,id:'gca_plan_unicode123',thesis:'这是一个用于验证中文计划日志交接的详细交易逻辑。'.repeat(24),invalidation:'价格结构和公开证据同时失效时取消计划。'.repeat(10)});const unicodeJournalDraft=j.parseTradePlanHandoff(p.buildHandoffLinks(unicodePlan).journal.split('#')[1]);"
            "const longResearch=new URLSearchParams({source:'research-note',title:'Valid title',theme:'Theme',thesis:'x'.repeat(401),invalidation:'A valid invalidation condition.',riskNotes:'A sufficiently detailed risk statement.'}).toString();const longJournal=new URLSearchParams({source:'trade-plan',symbol:'BTC/USDT',direction:'long',setup:'4h plan',notes:'x'.repeat(501)}).toString();"
            "process.stdout.write(JSON.stringify({noteLink,draft,completedLinks,activeLinks,journalDraft,unicodeDraft,unicodeJournalDraft,invalidResearchExtra:p.parseResearchHandoff(noteFragment+'&extra=x'),invalidResearchDuplicate:p.parseResearchHandoff(noteFragment+'&title=duplicate'),invalidResearchSecret:p.parseResearchHandoff(secretResearch),invalidResearchLong:p.parseResearchHandoff(longResearch),invalidJournalExtra:j.parseTradePlanHandoff(journalFragment+'&returnPercent=4'),invalidJournalDuplicate:j.parseTradePlanHandoff(journalFragment+'&symbol=ETH%2FUSDT'),invalidJournalSecret:j.parseTradePlanHandoff(new URLSearchParams({source:'trade-plan',symbol:'BTC/USDT',direction:'long',setup:'4h plan',notes:'Store a private key in these completed plan notes.'}).toString()),invalidJournalLong:j.parseTradePlanHandoff(longJournal)}));"
        )
        completed = subprocess.run(
            [
                node,
                "-e",
                script,
                str(SITE / "assets" / "research-notes.js"),
                str(SITE / "assets" / "trade-plans.js"),
                str(SITE / "assets" / "trade-journal.js"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)

        self.assertTrue(result["noteLink"].startswith("trade-plans.html#source=research-note"))
        self.assertNotIn("sourceUrl", result["noteLink"])
        self.assertEqual(result["draft"]["timeframe"], "other")
        self.assertEqual(result["draft"]["workflowStatus"], "draft")
        self.assertIn("Risk context:", result["draft"]["thesis"])
        self.assertIsNone(result["activeLinks"]["journal"])
        self.assertTrue(result["completedLinks"]["journal"].startswith("trade-journal.html#source=trade-plan"))
        self.assertNotIn("return", result["completedLinks"]["journal"].lower())
        self.assertNotIn("date=", result["completedLinks"]["journal"])
        self.assertEqual(result["journalDraft"]["market"], "BTC/USDT")
        self.assertEqual(result["journalDraft"]["direction"], "long")
        self.assertIn("中国基础设施研究计划", result["unicodeDraft"]["thesis"])
        self.assertEqual(result["unicodeJournalDraft"]["market"], "BTC/USDT")
        self.assertIn("中文计划日志交接", result["unicodeJournalDraft"]["notes"])
        for key in (
            "invalidResearchExtra",
            "invalidResearchDuplicate",
            "invalidResearchSecret",
            "invalidResearchLong",
            "invalidJournalExtra",
            "invalidJournalDuplicate",
            "invalidJournalSecret",
            "invalidJournalLong",
        ):
            self.assertIsNone(result[key])

    def test_portfolio_risk_map_is_local_structured_and_portable(self):
        page = (SITE / "portfolio-risk.html").read_text()
        engine = (SITE / "assets" / "portfolio-risk.js").read_text()
        product = json.loads((SITE / "product.json").read_text())
        credits = json.loads((SITE / "credits.json").read_text())
        access = json.loads((SITE / "access.json").read_text())

        for element_id in (
            "portfolioControls",
            "accountEquity",
            "portfolioRiskBudget",
            "grossExposureLimit",
            "marginLimit",
            "scenarioShock",
            "portfolioCostBps",
            "resetPortfolioLimits",
            "positionForm",
            "positionSymbol",
            "positionSide",
            "positionQuantity",
            "positionEntry",
            "positionStop",
            "positionLeverage",
            "positionLabel",
            "savePosition",
            "resetPosition",
            "cancelPositionEdit",
            "portfolioStatus",
            "portfolioState",
            "portfolioPositionCount",
            "portfolioPlannedRisk",
            "portfolioGrossExposure",
            "portfolioMarginUse",
            "portfolioWorstStress",
            "portfolioRiskBudgetUsed",
            "portfolioNetExposure",
            "portfolioDirectionConcentration",
            "portfolioLargestAsset",
            "portfolioStressDown",
            "portfolioStressUp",
            "portfolioFindings",
            "exportPortfolio",
            "importPortfolio",
            "clearPortfolio",
            "portfolioRows",
            "emptyPortfolio",
        ):
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn('src="assets/portfolio-risk.js"', page)
        self.assertIn("window.localStorage.setItem(engine.STORAGE_KEY", page)
        self.assertIn("window.localStorage.removeItem(engine.STORAGE_KEY)", page)
        self.assertIn("engine.normalizeConfig", page)
        self.assertIn("engine.normalizePosition", page)
        self.assertIn("engine.analyzePortfolio", page)
        self.assertIn("engine.buildBackup", page)
        self.assertIn("engine.parseBackup", page)
        self.assertIn("URL.createObjectURL", page)
        self.assertIn("await file.text()", page)
        self.assertIn("same percentage at the same time", page)
        self.assertIn("Do not enter private keys", page)
        self.assertNotIn("innerHTML", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('const STORAGE_KEY = "gca_portfolio_risk_v1"', engine)
        self.assertIn('const SCHEMA = "gca-portfolio-risk-v1"', engine)
        self.assertIn("const MAX_POSITIONS = 20", engine)

        module = next(item for item in product["productModules"] if item["id"] == "portfolio-risk-map")
        self.assertEqual(module["status"], "public-client-side-preview-live")
        self.assertEqual(module["publicUrl"], "https://gcagochina.com/portfolio-risk.html")
        self.assertTrue(module["browserLocalPortfolio"])
        self.assertTrue(module["portableJsonBackup"])
        self.assertTrue(module["backupContainsUserEnteredPositionDetails"])
        for field in ("storesOnServer", "connectsWallet", "connectsExchange", "fetchesMarketData", "placesOrders", "deductsCredits"):
            self.assertFalse(module[field])

        service = next(item for item in credits["serviceCatalog"] if item["id"] == "portfolio-risk-map")
        self.assertEqual(service["creditUnit"], 15)
        self.assertEqual(service["publicPreview"]["status"], "live-client-side-preview")
        self.assertEqual(service["publicPreview"]["url"], "https://gcagochina.com/portfolio-risk.html")
        self.assertTrue(service["publicPreview"]["browserLocalPortfolio"])
        self.assertTrue(service["publicPreview"]["portableJsonBackup"])
        for field in ("storesOnServer", "deductsCredits", "connectsWallet", "connectsExchange", "fetchesMarketData", "placesOrders"):
            self.assertFalse(service["publicPreview"][field])

        self.assertEqual(product["officialLinks"]["portfolioRiskMap"], "https://gcagochina.com/portfolio-risk.html")
        self.assertEqual(credits["officialLinks"]["portfolioRiskMap"], "https://gcagochina.com/portfolio-risk.html")
        self.assertIn("Portfolio Risk Map", access["serviceModules"])

    def test_portfolio_risk_engine_calculates_limits_and_validates_backups(self):
        bundled_node = Path("/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
        node = shutil.which("node") or (str(bundled_node) if bundled_node.exists() else "")
        if not node:
            self.skipTest("Node.js is unavailable")

        module_path = SITE / "assets" / "portfolio-risk.js"
        workspace_path = SITE / "assets" / "member-workspace.js"
        script = (
            "const p=require(process.argv[1]);const w=require(process.argv[2]);"
            "const config=p.normalizeConfig({accountEquity:10000,riskBudgetPercent:2,grossExposureLimitPercent:200,marginLimitPercent:50,scenarioShockPercent:5,costBps:20});"
            "const base={version:1,createdAt:'2026-07-16T00:00:00Z',updatedAt:'2026-07-16T00:00:00Z'};"
            "const long=p.normalizePosition({...base,id:'gca_position_alpha1234',symbol:'btc/usdt',side:'long',quantity:.1,entry:30000,stop:29000,leverage:2,label:'Core setup'});"
            "const short=p.normalizePosition({...base,id:'gca_position_beta12345',symbol:'ETH/USDT',side:'short',quantity:1,entry:2000,stop:2100,leverage:4,label:'Risk hedge'});"
            "const positions=p.orderPositions([long,short]);"
            "const analysis=p.analyzePortfolio(config,positions);"
            "const backup=p.buildBackup(config,positions,'2026-07-16T01:00:00Z');"
            "const parsed=p.parseBackup(JSON.stringify(backup));"
            "const workspace=w.summarizePortfolioRisk(JSON.stringify(backup),p);"
            "const invalidExtra=p.parseBackup({...backup,unexpected:true});"
            "const duplicate=p.parseBackup({...backup,positions:[backup.positions[0],backup.positions[0]]});"
            "const invalidLongStop=p.normalizePosition({...base,id:'gca_position_badstop123',symbol:'BTC/USDT',side:'long',quantity:1,entry:100,stop:101,leverage:1,label:''});"
            "const sensitive=p.normalizePosition({...base,id:'gca_position_secret123',symbol:'BTC/USDT',side:'long',quantity:1,entry:100,stop:99,leverage:1,label:'save seed phrase'});"
            "const removed=p.removePosition(positions,long.id);"
            "process.stdout.write(JSON.stringify({config,long,short,analysis,backup,parsed,workspace,invalidExtra,duplicate,invalidLongStop,sensitive,removed,emptyWorkspace:w.summarizePortfolioRisk('{}',p)}));"
        )
        completed = subprocess.run(
            [node, "-e", script, str(module_path), str(workspace_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(result["long"]["symbol"], "BTC/USDT")
        self.assertEqual(result["analysis"]["positionCount"], 2)
        self.assertEqual(result["analysis"]["status"], "BLOCKED")
        self.assertEqual(result["analysis"]["blockerCount"], 1)
        self.assertGreaterEqual(result["analysis"]["warningCount"], 2)
        self.assertAlmostEqual(result["analysis"]["grossNotional"], 5000)
        self.assertAlmostEqual(result["analysis"]["netNotional"], 1000)
        self.assertAlmostEqual(result["analysis"]["totalPlannedLoss"], 210)
        self.assertAlmostEqual(result["analysis"]["totalRiskPercent"], 2.1)
        self.assertAlmostEqual(result["analysis"]["riskBudgetUsedPercent"], 105)
        self.assertAlmostEqual(result["analysis"]["marginUtilizationPercent"], 20)
        self.assertAlmostEqual(result["analysis"]["stressDownPnl"], -60)
        self.assertAlmostEqual(result["analysis"]["stressUpPnl"], 40)
        self.assertEqual(result["analysis"]["largestAssetSymbol"], "BTC/USDT")
        self.assertIn("RISK_BUDGET_EXCEEDED", {item["code"] for item in result["analysis"]["findings"]})
        self.assertEqual(result["backup"]["schema"], "gca-portfolio-risk-v1")
        self.assertEqual(result["parsed"], result["backup"])
        self.assertEqual(result["workspace"]["positionCount"], 2)
        self.assertEqual(result["workspace"]["status"], "BLOCKED")
        self.assertAlmostEqual(result["workspace"]["totalRiskPercent"], 2.1)
        self.assertEqual(result["workspace"]["savedAt"], "2026-07-16T01:00:00.000Z")
        self.assertIsNone(result["invalidExtra"])
        self.assertIsNone(result["duplicate"])
        self.assertIsNone(result["invalidLongStop"])
        self.assertIsNone(result["sensitive"])
        self.assertEqual(len(result["removed"]), 1)
        self.assertEqual(result["removed"][0]["symbol"], "ETH/USDT")
        self.assertEqual(result["emptyWorkspace"]["status"], "NO_POSITIONS")

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
            "undoDelete",
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
        self.assertIn("let lastDeletedTrade = null", page)
        self.assertIn("function clearUndo()", page)
        self.assertIn("trade restored. / 已恢复", page)
        self.assertIn("[hidden] { display:none !important; }", page)
        self.assertIn("engine.groupPerformance(visibleTrades,breakdownDimension.value)", page)
        self.assertIn("let editingId = null", page)
        self.assertIn("edit.dataset.editId=trade.id", page)
        self.assertIn("Update Trade / 更新记录", page)
        self.assertIn("createdAt:existing?.createdAt||new Date().toISOString()", page)
        self.assertIn("Simple total adds account returns without compounding", page)
        self.assertIn("does not upload trades", page)
        self.assertIn("engine.parseTradePlanHandoff", page)
        self.assertIn("applyTradePlanHandoff", page)
        self.assertIn("no journal entry was saved automatically", page)
        self.assertIn("never the date or realized return", page)
        self.assertNotIn("window.ethereum", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("WebSocket", page)
        self.assertIn('const STORAGE_KEY = "gca_trade_journal_v1"', engine)
        self.assertEqual(product["positioning"]["publicRiskToolPreviewsLive"], 10)
        self.assertEqual(product["officialLinks"]["tradeJournal"], "https://gcagochina.com/trade-journal.html")
        module = next(item for item in product["productModules"] if item["id"] == "trade-journal")
        self.assertTrue(module["completedPlanHandoff"])
        self.assertFalse(module["handoffAutoSavesTrade"])
        self.assertFalse(module["handoffImportsRealizedReturn"])
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
