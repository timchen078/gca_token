import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER_SOURCE = ROOT / "cloudflare" / "gca-registration-worker" / "src" / "worker.mjs"


class GcaWorkerRootRedirectTests(unittest.TestCase):
    def test_api_root_redirects_to_official_site(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")

        self.assertIn('const OFFICIAL_SITE_URL = "https://gcagochina.com/";', source)
        self.assertIn(
            '(request.method === "GET" || request.method === "HEAD") && url.pathname === "/"',
            source,
        )
        self.assertIn("return Response.redirect(OFFICIAL_SITE_URL, 302);", source)


if __name__ == "__main__":
    unittest.main()
