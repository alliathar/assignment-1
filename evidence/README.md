# Evidence inventory

The following evidence was captured from the local Compose stack on 26
September 2026:

- `prometheus-targets.png` — all three scrape targets are UP.
- `grafana-normal.png` — dashboard during the baseline stage.
- `grafana-slow-fault.png` — dashboard while the slow fault is enabled.
- `grafana-recovery.png` — dashboard after recovery.
- `kibana-request-search.png` — request-ID search with structured fields.
- `kibana-error-search.png` — working warning search.
- `cardinality-unsafe.png` — `count(demo_requests_total)` equals 100.
- `cardinality-safe.png` — the same query equals 1.
- `anomaly-results.json` — exact client-side anomaly measurements.

Use a visible time range and include panel titles or query text in each capture.
