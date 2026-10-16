import contextlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import subprocess
import unittest
from unittest.mock import patch


module_path = Path(__file__).resolve().parents[1] / "scripts/configure-tunnel.py"
spec = importlib.util.spec_from_file_location("configure_tunnel", module_path)
tunnel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tunnel)


class TunnelTokenTest(unittest.TestCase):
    arguments = {
        "account_id": "0" * 32,
        "tunnel_id": "11111111-1111-4111-8111-111111111111",
        "parameter_name": "/openstudy-prod/cloudflared/token",
        "aws_account_id": "123456789012",
        "region": "ap-northeast-2",
    }

    @patch.dict("os.environ", {"CLOUDFLARE_API_TOKEN": "test-api-token"})
    def test_token_is_not_in_arguments_or_output(self):
        temporary_paths = []

        def fake_aws(command, **kwargs):
            self.assertNotIn("connector-secret", " ".join(command))
            if "get-caller-identity" in command:
                return subprocess.CompletedProcess(command, 0, '{"Account":"123456789012"}')
            path = Path(command[-1].removeprefix("file://"))
            temporary_paths.append(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            document = json.loads(path.read_text())
            self.assertEqual(document["Value"], "connector-secret")
            self.assertEqual(document["Type"], "SecureString")
            return subprocess.CompletedProcess(command, 0, '{"Version":1}')

        output = io.StringIO()
        response = io.BytesIO(b'{"success":true,"result":"connector-secret"}')
        with patch.object(tunnel.subprocess, "run", side_effect=fake_aws), \
                patch.object(tunnel.urllib.request, "urlopen", return_value=response), \
                contextlib.redirect_stdout(output):
            tunnel.configure(**self.arguments)

        self.assertNotIn("connector-secret", output.getvalue())
        self.assertEqual(len(temporary_paths), 1)
        self.assertFalse(temporary_paths[0].exists())

    @patch.dict("os.environ", {"CLOUDFLARE_API_TOKEN": "test-api-token"})
    def test_wrong_aws_account_prevents_token_fetch_and_write(self):
        result = subprocess.CompletedProcess([], 0, '{"Account":"999999999999"}')
        with patch.object(tunnel.subprocess, "run", return_value=result) as aws, \
                patch.object(tunnel.urllib.request, "urlopen") as cloudflare:
            with self.assertRaisesRegex(RuntimeError, "AWS 계정"):
                tunnel.configure(**self.arguments)
            aws.assert_called_once()
            cloudflare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
