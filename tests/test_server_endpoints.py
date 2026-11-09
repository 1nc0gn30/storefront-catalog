"""Integration tests for storefront-catalog daemon HTTP endpoints.
Tests /health, /api/catalog, /api/products, and /api/payloads/<id> for all 10 products.
"""
import json
import threading
import time
import urllib.request
import urllib.error
from http.server import HTTPServer
from pathlib import Path
import pytest

from server import SovereignCatalogHandler, MANIFEST_PATH

ROOT_DIR = Path(__file__).resolve().parent.parent

@pytest.fixture(scope="module")
def running_server():
    server = HTTPServer(("127.0.0.1", 0), SovereignCatalogHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    server.shutdown()
    server.server_close()


def test_health_endpoint(running_server):
    for ep in ("/health", "/api/health"):
        req = urllib.request.Request(f"{running_server}{ep}")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "healthy"
            assert data["service"] == "storefront-catalog"
            assert data["total_listings"] == 10
            assert data["blended_margin"] == 62.6


def test_catalog_endpoint(running_server):
    req = urllib.request.Request(f"{running_server}/api/catalog")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["store_name"] == "YourDigitalSpace"
        assert len(data["listings"]) == 10
        assert data["portfolio_financials"]["blended_net_margin"] == 62.6


def test_products_endpoint(running_server):
    req = urllib.request.Request(f"{running_server}/api/products")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["total"] == 10
        assert len(data["listings"]) == 10
        assert data["financials"]["blended_net_margin"] == 62.6


def test_payload_endpoints_all_ten_products(running_server):
    manifest = json.loads(MANIFEST_PATH.read_text())
    for item in manifest["listings"]:
        prod_id = item["id"]
        # Test naked prod_id
        req = urllib.request.Request(f"{running_server}/api/payloads/{prod_id}")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            assert resp.status == 200
            payload = json.loads(resp.read().decode())
            assert "title" in payload
            assert "variants" in payload
            assert len(payload["tags"]) == 13

        # Test prod_id with _printify.json
        req2 = urllib.request.Request(f"{running_server}/api/payloads/{prod_id}_printify.json")
        with urllib.request.urlopen(req2, timeout=2.0) as resp2:
            assert resp2.status == 200


def test_payload_endpoint_404_on_unknown(running_server):
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{running_server}/api/payloads/non-existent-product", timeout=2.0)
    assert exc_info.value.code == 404


def test_drafts_endpoint(running_server):
    for ep in ("/api/drafts", "/api/live-drafts"):
        req = urllib.request.Request(f"{running_server}{ep}")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["schema_version"] == "1.0.0"
            assert len(data["listings"]) == 10
            assert all(item["ready_to_publish"] is True for item in data["listings"])
