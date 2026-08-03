"""rootip/api.py の安全機能（ガードレール）が維持されていることを確認するテスト。

実行方法:
    python -m unittest discover -s tests

これらのテストは実際のAPI通信を行いません。
安全機能を変更した場合、このテストが失敗することで意図しない変更に気づけます。
"""

import csv
import importlib
import json
import os
import stat
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

import rootip.api as api_module
from rootip.app_sample.master_currencies_get_and_update import get_currency_rate
from rootip.api import (
    ALLOWED_METHODS,
    json_to_csv_array,
    json_to_csv_file,
    make_request,
    normalize_url,
    sanitize_csv_value,
)


class TestNormalizeUrl(unittest.TestCase):
    def test_https_url_is_accepted(self):
        url = normalize_url("https://example.rootip-cloud.net", "/api/v1/case_biblios")
        self.assertEqual(url, "https://example.rootip-cloud.net/api/v1/case_biblios")

    def test_scheme_less_url_becomes_https(self):
        url = normalize_url("example.rootip-cloud.net", "/api/v1/case_biblios")
        self.assertEqual(url, "https://example.rootip-cloud.net/api/v1/case_biblios")

    def test_trailing_slash_is_normalized(self):
        url = normalize_url("https://example.rootip-cloud.net/", "/api/v1/case_biblios")
        self.assertEqual(url, "https://example.rootip-cloud.net/api/v1/case_biblios")

    def test_http_url_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url("http://example.rootip-cloud.net", "/api/v1/case_biblios")

    def test_url_with_credentials_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url(
                "https://user:pass@example.rootip-cloud.net", "/api/v1/case_biblios"
            )

    def test_url_with_extra_path_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url(
                "https://example.rootip-cloud.net/extra", "/api/v1/case_biblios"
            )

    def test_non_rootip_host_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url("https://example.com", "/api/v1/case_biblios")

    def test_lookalike_rootip_host_is_rejected(self):
        for root_url in (
            "https://rootip-cloud.net.example.com",
            "https://example-rootip-cloud.net",
        ):
            with self.assertRaises(ValueError, msg=root_url):
                normalize_url(root_url, "/api/v1/case_biblios")

    def test_non_https_port_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url(
                "https://example.rootip-cloud.net:8443",
                "/api/v1/case_biblios",
            )

    def test_endpoint_outside_api_path_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url("https://example.rootip-cloud.net", "/admin")

    def test_absolute_url_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url(
                "https://example.rootip-cloud.net", "https://evil.example/api/v1/x"
            )

    def test_dot_segment_endpoint_is_rejected(self):
        # /api/配下限定ガードを「..」で回避できないこと（パストラバーサル対策）
        for endpoint in ("/api/../admin", "/api/v1/../../admin", "/api/./v1/x"):
            with self.assertRaises(ValueError, msg=endpoint):
                normalize_url("https://example.rootip-cloud.net", endpoint)

    def test_percent_encoded_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url("https://example.rootip-cloud.net", "/api/%2e%2e/admin")

    def test_backslash_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url("https://example.rootip-cloud.net", "/api\\admin")

    def test_control_character_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_url("https://example.rootip-cloud.net", "/api/v1/x\r\nHost:evil")

    def test_endpoint_with_query_is_accepted(self):
        url = normalize_url(
            "https://example.rootip-cloud.net", "/api/v1/case_biblios?page=1&limit=10"
        )
        self.assertEqual(
            url, "https://example.rootip-cloud.net/api/v1/case_biblios?page=1&limit=10"
        )


class TestMethodAllowlist(unittest.TestCase):
    def test_delete_is_not_allowed(self):
        self.assertNotIn("DELETE", ALLOWED_METHODS)
        with self.assertRaises(ValueError):
            make_request("DELETE", "/api/v1/master_currencies")

    def test_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            make_request("PATCH", "/api/v1/master_currencies")

    def test_request_keeps_tls_verification_and_disables_redirects(self):
        response = mock.Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.iter_content.return_value = [b"[]"]
        session = mock.MagicMock()
        session.__enter__.return_value = session
        session.request.return_value = response

        with tempfile.NamedTemporaryFile() as certificate:
            with (
                mock.patch.object(api_module, "_secrets", object()),
                mock.patch.object(api_module, "ROOTIP_USER_ID", "fictional-user"),
                mock.patch.object(api_module, "ROOTIP_API_KEY", "fictional-token"),
                mock.patch.object(
                    api_module,
                    "ROOTIP_URL",
                    "https://example.rootip-cloud.net",
                ),
                mock.patch.object(
                    api_module,
                    "ROOTIP_CLIENT_CERTIFICATE_PEM",
                    certificate.name,
                ),
                mock.patch.object(
                    api_module,
                    "ROOTIP_CLIENT_CERTIFICATE_P12",
                    "",
                ),
                mock.patch.object(api_module.requests, "Session", return_value=session),
            ):
                result = make_request("GET", "/api/v1/case_biblios")

        self.assertIs(result, response)
        request_options = session.request.call_args.kwargs
        self.assertIsNot(request_options["verify"], False)
        self.assertFalse(request_options["allow_redirects"])
        self.assertTrue(request_options["stream"])
        self.assertEqual(request_options["timeout"], api_module.REQUEST_TIMEOUT)

    def test_oversized_api_response_is_rejected(self):
        response = mock.Mock()
        response.iter_content.return_value = [b"x" * 11]
        with (
            mock.patch.object(api_module, "MAX_RESPONSE_BYTES", 10),
            self.assertRaises(ValueError),
        ):
            api_module._load_limited_response_content(response)
        response.close.assert_called_once()


class TestCsvInjectionGuard(unittest.TestCase):
    def test_formula_values_are_escaped(self):
        for dangerous in ("=SUM(A1:A9)", "+1+2", "-1+2", "@cmd", "\tabc"):
            sanitized = sanitize_csv_value(dangerous)
            self.assertTrue(
                sanitized.startswith("'"),
                f"数式として解釈され得る値が無害化されていません: {dangerous!r}",
            )

    def test_normal_values_are_unchanged(self):
        self.assertEqual(sanitize_csv_value("山田太郎"), "山田太郎")
        self.assertEqual(sanitize_csv_value(123), 123)
        self.assertEqual(sanitize_csv_value(1.5), 1.5)
        self.assertEqual(sanitize_csv_value(None), None)

    def test_json_to_csv_array_escapes_formula(self):
        rows = json_to_csv_array(json.dumps([{"name": "=cmd|' /C calc'!A0"}]))
        self.assertIn("'=cmd", rows[1])

    def test_json_to_csv_array_rejects_empty_data(self):
        with self.assertRaises(ValueError):
            json_to_csv_array("[]")

    def test_json_to_csv_array_rejects_non_object_list(self):
        with self.assertRaises(ValueError):
            json_to_csv_array(json.dumps(["not-an-object"]))

    def test_json_to_csv_array_keeps_header_order(self):
        rows = json_to_csv_array(
            json.dumps(
                [
                    {"id": 1, "name": "first"},
                    {"name": "second", "id": 2},
                ]
            )
        )
        parsed = list(csv.reader(rows))
        self.assertEqual(parsed[0], ["id", "name"])
        self.assertEqual(parsed[2], ["2", "second"])

    def test_json_to_csv_file_uses_owner_only_permissions(self):
        if os.name == "nt":
            self.skipTest("WindowsではPOSIXファイル権限を検証できません")
        with tempfile.TemporaryDirectory() as directory:
            file_path = os.path.join(directory, "output.csv")
            json_to_csv_file(json.dumps([{"id": 1}]), file_path)
            mode = stat.S_IMODE(os.stat(file_path).st_mode)
            self.assertEqual(mode, 0o600)


class TestExternalCurrencyCsvGuard(unittest.TestCase):
    class FakeResponse:
        def __init__(self, content, status_code=200, content_type="text/csv"):
            self._content = content
            self.status_code = status_code
            self.headers = {"Content-Type": content_type}
            self.closed = False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            del chunk_size
            yield self._content

        def close(self):
            self.closed = True

    def test_valid_csv_is_parsed_with_decimal(self):
        content = (
            "最終更新日時：2026/08/03\n"
            "説明\n"
            "通貨名,T.T.S.,T.T.B.\n"
            "USD 米ドル,150.19,149.11\n"
        ).encode("cp932")
        response = self.FakeResponse(content)

        with mock.patch(
            "rootip.app_sample.master_currencies_get_and_update.requests.get",
            return_value=response,
        ):
            _, update_date, rates = get_currency_rate(decimal_places=1)

        self.assertEqual(update_date, "2026-08-03T00:00:00.000+09:00")
        self.assertEqual(rates, [["USD", Decimal("150.1"), Decimal("149.1")]])
        self.assertTrue(response.closed)

    def test_redirect_response_is_rejected(self):
        response = self.FakeResponse(b"", status_code=302)
        with (
            mock.patch(
                "rootip.app_sample.master_currencies_get_and_update.requests.get",
                return_value=response,
            ),
            self.assertRaises(api_module.requests.exceptions.HTTPError),
        ):
            get_currency_rate()
        self.assertTrue(response.closed)


class TestSampleImportSafety(unittest.TestCase):
    def test_importing_samples_has_no_network_or_file_side_effects(self):
        modules = (
            "app.sample",
            "rootip.app_sample.case_biblios_get",
            "rootip.app_sample.master_currencies_get_and_update",
            "rootip.app_sample.master_staffs_get_to_csv",
            "rootip.app_sample.master_staffs_put",
        )
        for module in modules:
            importlib.import_module(module)


if __name__ == "__main__":
    unittest.main()
