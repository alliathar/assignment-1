"""Run the assignment's bounded (maximum 100 IDs) cardinality experiment."""

import argparse
import json
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def read_json(url, method="GET"):
    request = Request(url, method=method, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(
        description="Send up to 100 unique IDs and report Prometheus series count."
    )
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--prometheus-url", default="http://localhost:9090")
    parser.add_argument("--scrape-wait", type=float, default=5.0)
    args = parser.parse_args()

    if not 1 <= args.count <= 100:
        raise SystemExit("--count must be between 1 and 100")

    try:
        _, health = read_json(f"{args.base_url}/health")
        mode = health["cardinality_mode"]
        prefix = uuid.uuid4().hex[:8]

        for number in range(1, args.count + 1):
            request_id = quote(f"demo-{prefix}-{number}")
            status, body = read_json(
                f"{args.base_url}/demo/cardinality?request_id={request_id}",
                method="POST",
            )
            if status != 200:
                raise RuntimeError(f"Request {number} failed: HTTP {status} {body}")

        print(
            f"Sent {args.count} unique IDs in {mode!r} mode. "
            f"Waiting {args.scrape_wait}s for a Prometheus scrape..."
        )
        time.sleep(args.scrape_wait)

        query = quote("count(demo_requests_total)")
        _, result = read_json(
            f"{args.prometheus_url}/api/v1/query?query={query}"
        )
        series = result["data"]["result"]
        series_count = int(float(series[0]["value"][1])) if series else 0

        expected = args.count if mode == "unsafe" else 1
        print(f"Prometheus query: count(demo_requests_total)")
        print(f"Observed series: {series_count}")
        print(f"Expected current series: {expected}")

        if series_count != expected:
            print(
                "Note: wait for another scrape if the service was just restarted; "
                "old labelled series become stale rather than being deleted immediately."
            )
    except URLError as error:
        raise SystemExit(
            "Could not reach the API or Prometheus. Run docker compose up -d first. "
            f"Details: {error}"
        ) from error


if __name__ == "__main__":
    main()
