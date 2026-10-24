"""Live traffic for the demo. Standard library only.

    python -m scripts.traffic --base-url https://shelf-xyz.a.run.app
    python -m scripts.traffic --base-url ... --partner   # one knock on /embed/widget
"""

from __future__ import annotations

import argparse
import time
import urllib.error
import urllib.request

PARTNER_KEY = "acme-quarterly-report"


def get(url: str, headers: dict[str, str] | None = None) -> int:
    request = urllib.request.Request(url, headers={"user-agent": "shelf-traffic", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--rate", type=float, default=1.0, help="requests per second to /v2/books")
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--partner", action="store_true", help="the forgotten partner calls the widget once")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    if args.partner:
        status = get(f"{base}/embed/widget", {"x-partner-key": PARTNER_KEY})
        print(f"partner {PARTNER_KEY} -> /embed/widget: {status}")
        return

    deadline = time.monotonic() + args.seconds
    while time.monotonic() < deadline:
        print(f"/v2/books: {get(f'{base}/v2/books')}")
        time.sleep(1 / args.rate)


if __name__ == "__main__":
    main()
