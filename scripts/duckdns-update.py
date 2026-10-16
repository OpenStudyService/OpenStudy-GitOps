#!/usr/bin/env python3
"""Keep one DuckDNS A record in sync with EC2's public IPv4 from IMDSv2."""

import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def public_ipv4():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        "http://169.254.169.254/latest/api/token",
        method="PUT",
        headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
    )
    with opener.open(request, timeout=5) as response:
        token = response.read().decode().strip()
    request = urllib.request.Request(
        "http://169.254.169.254/latest/meta-data/public-ipv4",
        headers={"X-aws-ec2-metadata-token": token},
    )
    with opener.open(request, timeout=5) as response:
        return str(ipaddress.IPv4Address(response.read().decode().strip()))


def token_parameter(name, region):
    result = subprocess.run(
        [
            "aws", "ssm", "get-parameter", "--name", name, "--region", region,
            "--with-decryption", "--output", "json", "--no-cli-pager",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError("Cannot read DuckDNS token; check SSM registration and permissions.")
    return json.loads(result.stdout)["Parameter"]


def synchronize(subdomain, address, parameter, previous, now):
    token = parameter["Value"]
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("The DuckDNS SecureString must contain the account token.")
    token = token.strip()
    state = dict(previous)
    if state.get("subdomain") != subdomain or state.get("token_version") != parameter["Version"]:
        state = {"subdomain": subdomain, "token_version": parameter["Version"]}
    if state.get("blocked"):
        return state, "blocked"
    if now < state.get("retry_after", 0):
        return state, "deferred"
    if state.get("last_ip") == address:
        return state, "unchanged"

    query = urllib.parse.urlencode({"domains": subdomain, "token": token, "ip": address})
    request = urllib.request.Request(
        f"https://www.duckdns.org/update?{query}",
        headers={"User-Agent": "OpenStudy DuckDNS/Linux-1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            reply = response.read(1024).decode("utf-8", errors="replace").strip()
    except urllib.error.HTTPError as error:
        if error.code >= 500 or error.code == 429:
            state["retry_after"] = now + 1800
            return state, "retry"
        state["blocked"] = f"http_{error.code}"
        return state, "blocked"
    except (urllib.error.URLError, TimeoutError):
        state["retry_after"] = now + 1800
        return state, "retry"

    if reply == "OK":
        state["last_ip"] = address
        state.pop("retry_after", None)
        return state, "updated"
    state["blocked"] = "rejected" if reply == "KO" else "unexpected_response"
    return state, "blocked"


def main():
    os.umask(0o077)
    state_file = Path("/var/lib/openstudy-duckdns/state.json")
    try:
        previous = json.loads(state_file.read_text()) if state_file.exists() else {}
        address = public_ipv4()
        parameter = token_parameter(os.environ["DUCKDNS_TOKEN_PARAMETER"], os.environ["AWS_DEFAULT_REGION"])
        state, status = synchronize(os.environ["DUCKDNS_SUBDOMAIN"], address, parameter, previous, time.time())
        temporary = state_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(state))
        temporary.replace(state_file)
        print(f"DuckDNS update: {status}")
        if status == "blocked":
            print("Check DuckDNS domain ownership and token. Store a new SSM parameter version after correction.", file=sys.stderr)
        return 1 if status in {"retry", "blocked"} else 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired, RuntimeError):
        # HTTP exception messages may contain the token-bearing URL; never print them.
        print("DuckDNS update failed; check IMDSv2, SSM token and parameter format.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
