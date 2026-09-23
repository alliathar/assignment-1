# Evidence checklist

Do not fabricate results. Add the following files after running the experiments:

- `prometheus-targets.png` — all three scrape targets are UP.
- `grafana-normal.png` — dashboard during the baseline stage.
- `grafana-slow-fault.png` — dashboard while the slow fault is enabled.
- `grafana-recovery.png` — dashboard after recovery.
- `kibana-request-search.png` — one request ID search with structured fields.
- `kibana-error-search.png` — a working warning/error search.
- `cardinality-unsafe.png` — `count(demo_requests_total)` near 100.
- `cardinality-safe.png` — the same query showing one current series.
- `anomaly-results.json` — automatically written by the anomaly script.

Use a visible time range and include panel titles or query text in each capture.
