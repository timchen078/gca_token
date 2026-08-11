import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from tools.check_gca_market_health import (
    API_URL,
    GCA_ADDRESS,
    POOL_ADDRESS,
    PUBLIC_POOL_URL,
    USDT_ADDRESS,
    MarketHealthCheckError,
    check_market_health,
    classify_market,
)


VALID_RESPONSE = {
    "data": {
        "id": f"base_{POOL_ADDRESS}",
        "type": "pool",
        "attributes": {
            "address": POOL_ADDRESS,
            "name": "GCA / USDT 0.01%",
            "base_token_price_usd": "0.00000180452417",
            "reserve_in_usd": "41.8349",
            "volume_usd": {"h24": "2.5000"},
            "transactions": {
                "h24": {"buys": 2, "sells": 1, "buyers": 2, "sellers": 1}
            },
            "price_change_percentage": {"h24": "-1.2500"},
            "pool_created_at": "2026-05-10T14:54:55Z",
        },
        "relationships": {
            "base_token": {"data": {"id": f"base_{GCA_ADDRESS}", "type": "token"}},
            "quote_token": {"data": {"id": f"base_{USDT_ADDRESS}", "type": "token"}},
            "dex": {"data": {"id": "uniswap-v4-base", "type": "dex"}},
        },
    }
}


class GcaMarketHealthTests(unittest.TestCase):
    def test_classifies_exact_official_pool_and_keeps_claims_bounded(self):
        payload = classify_market(
            VALID_RESPONSE,
            checked_at="2026-08-11T20:00:00Z",
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["packetVersion"], "gca_market_health_check_v1")
        self.assertEqual(payload["status"], "official-pool-observed")
        self.assertTrue(payload["identityVerified"])
        self.assertEqual(payload["chainId"], 8453)
        self.assertEqual(payload["poolAddress"], POOL_ADDRESS)
        self.assertEqual(payload["contractAddress"], GCA_ADDRESS)
        self.assertEqual(payload["quoteAssetAddress"], USDT_ADDRESS)
        self.assertEqual(payload["source"]["apiUrl"], API_URL)
        self.assertEqual(payload["source"]["publicPoolUrl"], PUBLIC_POOL_URL)
        self.assertEqual(payload["observed"]["baseTokenPriceUsd"], "0.00000180452417")
        self.assertEqual(payload["observed"]["reserveInUsd"], "41.8349")
        self.assertEqual(payload["observed"]["volumeUsd24h"], "2.5")
        self.assertEqual(payload["observed"]["priceChangePercentage24h"], "-1.25")
        self.assertEqual(payload["observed"]["transactions24h"]["total"], 3)
        self.assertEqual(
            payload["interpretation"]["activityStatus"],
            "24h-transactions-observed",
        )
        self.assertTrue(payload["interpretation"]["doesNotProveOrganicDemand"])
        self.assertFalse(payload["boundaries"]["connectsWallet"])
        self.assertFalse(payload["boundaries"]["buildsExecutableQuote"])
        self.assertFalse(payload["boundaries"]["submitsTrade"])
        self.assertFalse(payload["boundaries"]["claimsDeepLiquidity"])
        self.assertFalse(payload["boundaries"]["claimsOrganicDemand"])

    def test_zero_activity_is_reported_without_becoming_a_failure(self):
        fixture = deepcopy(VALID_RESPONSE)
        fixture["data"]["attributes"]["volume_usd"]["h24"] = "0.0"
        fixture["data"]["attributes"]["transactions"]["h24"] = {
            "buys": 0,
            "sells": 0,
            "buyers": 0,
            "sellers": 0,
        }

        payload = classify_market(fixture)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["observed"]["volumeUsd24h"], "0")
        self.assertEqual(payload["observed"]["transactions24h"]["total"], 0)
        self.assertEqual(
            payload["interpretation"]["activityStatus"],
            "no-24h-transactions-observed",
        )

    def test_rejects_wrong_pool_or_relationship_identity(self):
        cases = {
            "pool": ("data", "id", "base_0x0000000000000000000000000000000000000000"),
            "base": (
                "relationships",
                "base_token",
                "base_0x0000000000000000000000000000000000000000",
            ),
            "quote": (
                "relationships",
                "quote_token",
                "base_0x0000000000000000000000000000000000000000",
            ),
            "dex": ("relationships", "dex", "another-dex"),
        }
        for label, path in cases.items():
            with self.subTest(label=label):
                fixture = deepcopy(VALID_RESPONSE)
                if path[0] == "data":
                    fixture["data"][path[1]] = path[2]
                else:
                    fixture["data"]["relationships"][path[1]]["data"]["id"] = path[2]
                with self.assertRaisesRegex(MarketHealthCheckError, "identity mismatch"):
                    classify_market(fixture)

    def test_rejects_missing_or_invalid_aggregate_metrics(self):
        negative = deepcopy(VALID_RESPONSE)
        negative["data"]["attributes"]["reserve_in_usd"] = "-1"
        with self.assertRaisesRegex(MarketHealthCheckError, "non-negative"):
            classify_market(negative)

        invalid_count = deepcopy(VALID_RESPONSE)
        invalid_count["data"]["attributes"]["transactions"]["h24"]["buys"] = 1.5
        with self.assertRaisesRegex(MarketHealthCheckError, "integer"):
            classify_market(invalid_count)

    def test_fixture_cli_is_deterministic_and_failure_is_nonzero(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "tools" / "check_gca_market_health.py"
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / "market.json"
            fixture.write_text(json.dumps(VALID_RESPONSE), encoding="utf-8")
            command = [
                sys.executable,
                str(script),
                "--json-file",
                str(fixture),
                "--checked-at",
                "2026-08-11T20:00:00Z",
                "--json",
            ]
            completed = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            broken = deepcopy(VALID_RESPONSE)
            broken["data"]["relationships"]["dex"]["data"]["id"] = "wrong-dex"
            fixture.write_text(json.dumps(broken), encoding="utf-8")
            failed = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["checkedAt"], "2026-08-11T20:00:00Z")
        self.assertEqual(payload["status"], "official-pool-observed")
        self.assertEqual(failed.returncode, 2)
        failure = json.loads(failed.stdout)
        self.assertEqual(failure["status"], "market-snapshot-unavailable")
        self.assertFalse(failure["identityVerified"])
        self.assertFalse(failure["boundaries"]["submitsTrade"])

    def test_check_market_health_can_use_fixture_and_override_source_url(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / "market.json"
            fixture.write_text(json.dumps(VALID_RESPONSE), encoding="utf-8")
            payload = check_market_health(
                api_url="https://example.com/fixture",
                json_file=fixture,
                checked_at="2026-08-11T20:00:00Z",
            )

        self.assertEqual(payload["source"]["apiUrl"], "https://example.com/fixture")


if __name__ == "__main__":
    unittest.main()
