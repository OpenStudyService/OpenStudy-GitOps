#!/usr/bin/env python3
"""Copy a Tunnel connector token to SSM without putting it in Terraform state."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid


def aws_json(arguments, region, profile):
    command = ["aws", "--region", region, "--output", "json", "--no-cli-pager"]
    if profile:
        command.extend(["--profile", profile])
    result = subprocess.run(command + arguments, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("AWS 요청에 실패했다. 로컬 자격증명과 대상 리소스 권한을 확인한다.")
    return json.loads(result.stdout)


def configure(account_id, tunnel_id, parameter_name, aws_account_id, region, profile=None):
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not api_token:
        raise RuntimeError("CLOUDFLARE_API_TOKEN 환경 변수를 설정한다.")
    if not re.fullmatch(r"[a-f0-9]{32}", account_id):
        raise RuntimeError("Cloudflare account ID 형식을 확인한다.")
    try:
        tunnel_id = str(uuid.UUID(tunnel_id))
    except ValueError:
        raise RuntimeError("Tunnel ID 형식을 확인한다.") from None
    if not re.fullmatch(r"\d{12}", aws_account_id):
        raise RuntimeError("12자리 AWS 계정 ID를 지정한다.")
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", parameter_name):
        raise RuntimeError("Parameter Store 경로 형식을 확인한다.")

    identity = aws_json(["sts", "get-caller-identity"], region, profile)
    if identity.get("Account") != aws_account_id:
        raise RuntimeError("현재 AWS 계정이 지정한 배포 계정과 다르다.")

    request = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/token",
        headers={"Authorization": f"Bearer {api_token}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    token = payload.get("result")
    if not payload.get("success") or not isinstance(token, str) or not token.strip():
        raise RuntimeError("Cloudflare에서 유효한 Tunnel 토큰을 받지 못했다.")

    with tempfile.TemporaryDirectory(prefix="openstudy-tunnel-") as directory:
        input_file = Path(directory) / "parameter.json"
        with open(input_file, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
            json.dump({
                "Name": parameter_name,
                "Type": "SecureString",
                "Value": token,
                "Overwrite": True,
                "Tier": "Standard",
            }, handle)
        result = aws_json(
            ["ssm", "put-parameter", "--cli-input-json", f"file://{input_file}"],
            region,
            profile,
        )
    print(f"Tunnel 토큰 등록을 완료했다. Parameter 버전: {result['Version']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--tunnel-id", required=True)
    parser.add_argument("--parameter-name", required=True)
    parser.add_argument("--aws-account-id", required=True)
    parser.add_argument("--region", default="ap-northeast-2")
    parser.add_argument("--profile")
    args = parser.parse_args()
    try:
        configure(**vars(args))
    except urllib.error.HTTPError as error:
        sys.exit(f"Cloudflare API 요청에 실패했다. HTTP {error.code}. 토큰 권한을 확인한다.")
    except urllib.error.URLError:
        sys.exit("Cloudflare 연결에 실패했다. 네트워크를 확인한다.")
    except (RuntimeError, ValueError, KeyError) as error:
        sys.exit(str(error) if isinstance(error, RuntimeError) else "API 응답 형식을 확인한다.")


if __name__ == "__main__":
    main()
