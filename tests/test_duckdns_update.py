import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.parse


module_path = Path(__file__).resolve().parents[1] / "scripts/duckdns-update.py"
spec = importlib.util.spec_from_file_location("duckdns_update", module_path)
duckdns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(duckdns)


class DuckDNSUpdateTest(unittest.TestCase):
    subdomain = "openstudy"
    address = "198.51.100.10"
    token = "test-duckdns-account-token"

    def parameter(self, version=1):
        return {"Version": version, "Value": self.token}

    def test_update_targets_ec2_address_and_keeps_token_out_of_state(self):
        with patch.object(duckdns.urllib.request, "urlopen", return_value=io.BytesIO(b"OK\n")) as request:
            state, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(), {}, 100)
            self.assertEqual(status, "updated")
            sent = request.call_args.args[0]
            url = urllib.parse.urlsplit(sent.full_url)
            self.assertEqual((url.scheme, url.netloc, url.path), ("https", "www.duckdns.org", "/update"))
            self.assertEqual(urllib.parse.parse_qs(url.query), {
                "domains": [self.subdomain], "token": [self.token], "ip": [self.address],
            })
            self.assertNotIn(self.token, json.dumps(state))
            self.assertEqual(state["last_ip"], self.address)
            cached, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(), state, 1000)
            self.assertEqual((status, cached), ("unchanged", state))
            request.assert_called_once()

    def test_ip_change_updates_without_another_terraform_apply(self):
        previous = {"subdomain": self.subdomain, "token_version": 1, "last_ip": "198.51.100.9"}
        with patch.object(duckdns.urllib.request, "urlopen", return_value=io.BytesIO(b"OK")) as request:
            state, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(), previous, 100)
            self.assertEqual((status, state["last_ip"]), ("updated", self.address))
            request.assert_called_once()

    def test_rejection_stops_requests_until_parameter_version_changes(self):
        with patch.object(duckdns.urllib.request, "urlopen", side_effect=[io.BytesIO(b"KO"), io.BytesIO(b"OK")]) as request:
            state, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(), {}, 100)
            self.assertEqual(status, "blocked")
            state, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(), state, 10000)
            self.assertEqual(status, "blocked")
            self.assertEqual(request.call_count, 1)
            state, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(version=2), state, 10001)
            self.assertEqual(status, "updated")
            self.assertNotIn("blocked", state)
            self.assertEqual(request.call_count, 2)

    def test_transient_failure_backs_off_before_retrying(self):
        for code in (429, 500, 503):
            error = urllib.error.HTTPError("https://www.duckdns.org/", code, "error", {}, None)
            with self.subTest(code=code), patch.object(duckdns.urllib.request, "urlopen", side_effect=[error, io.BytesIO(b"OK")]) as request:
                state, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(), {}, 100)
                self.assertEqual((status, state["retry_after"]), ("retry", 1900))
                state, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(), state, 1899)
                self.assertEqual(status, "deferred")
                self.assertEqual(request.call_count, 1)
                _, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(), state, 1900)
                self.assertEqual(status, "updated")

    def test_unexpected_response_is_not_retained(self):
        with patch.object(duckdns.urllib.request, "urlopen", return_value=io.BytesIO(self.token.encode())):
            state, status = duckdns.synchronize(self.subdomain, self.address, self.parameter(), {}, 100)
            self.assertEqual(status, "blocked")
            self.assertNotIn("last_ip", state)
            self.assertNotIn(self.token, json.dumps(state))

    def test_public_ip_uses_imdsv2_without_a_proxy(self):
        opener = MagicMock()
        opener.open.side_effect = [io.BytesIO(b"imds-session-token"), io.BytesIO(self.address.encode())]
        with patch.object(duckdns.urllib.request, "build_opener", return_value=opener) as build:
            self.assertEqual(duckdns.public_ipv4(), self.address)
        self.assertEqual(build.call_args.args[0].proxies, {})
        token_request, ip_request = [call.args[0] for call in opener.open.call_args_list]
        self.assertEqual(token_request.get_method(), "PUT")
        self.assertTrue(ip_request.full_url.endswith("/meta-data/public-ipv4"))
        headers = {key.lower(): value for key, value in ip_request.header_items()}
        self.assertEqual(headers["x-aws-ec2-metadata-token"], "imds-session-token")

    def test_main_does_not_log_token_in_exception_urls(self):
        error = urllib.error.URLError(f"https://www.duckdns.org/update?token={self.token}")
        output = io.StringIO()
        with patch.object(duckdns.Path, "exists", return_value=False), \
                patch.object(duckdns, "public_ipv4", side_effect=error), \
                contextlib.redirect_stderr(output):
            self.assertEqual(duckdns.main(), 1)
        self.assertNotIn(self.token, output.getvalue())


if __name__ == "__main__":
    unittest.main()
