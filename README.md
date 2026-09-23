# Campus Room Booking Observability Project

This project is a small FastAPI service for creating and cancelling campus
study-room bookings. Its purpose is to demonstrate application metrics,
business metrics, structured logging, infrastructure monitoring, controlled
fault injection, and bounded cardinality testing.

## Requirements

- Docker Desktop with Docker Compose v2
- Python 3.8 or later for the experiment clients
- Approximately 6 GB free RAM and 4 GB free disk for the Elastic stack

## Start the complete system

From this directory:

```powershell
docker compose up -d --build
docker compose ps
```

Elasticsearch and Kibana can take one or two minutes to become ready on their
first launch.

| Component | URL | Purpose |
|---|---|---|
| Booking API | <http://localhost:8000/docs> | Create, list, and cancel bookings |
| Raw application metrics | <http://localhost:8000/metrics> | Prometheus exposition |
| Prometheus targets | <http://localhost:9090/targets> | Verify scrape health |
| Grafana | <http://localhost:3000> | Metrics dashboard (`admin` / `admin`) |
| Node Exporter | <http://localhost:9100/metrics> | Docker Desktop Linux VM metrics |
| Elasticsearch | <http://localhost:9200/_cat/indices?v> | Log-index inventory |
| Kibana | <http://localhost:5601/app/discover> | Search structured logs |

Grafana automatically provisions the **Room Booking Observability** dashboard.
The monitored machine named in its resource panels is the **Docker Desktop
Linux VM**, not the full Windows host.

## Use the application

Open Swagger at <http://localhost:8000/docs>, or create a booking with
PowerShell:

```powershell
$body = @{
    room = "Study-Room-101"
    duration_minutes = 60
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri http://localhost:8000/bookings `
    -ContentType "application/json" `
    -Body $body
```

Submitting the same room twice returns `409 Conflict`. This is an intentional
business-rule rejection and appears in both metrics and logs.

## Generate dashboard traffic

Generate successful creations, duplicate rejections, cancellations, and list
requests for two minutes:

```powershell
python experiments\load_test.py --duration 120 --interval 0.5
```

Set the Grafana time range to **Last 15 minutes** and refresh to **5s**.

## Configure Kibana

1. Generate traffic using the command above.
2. Open <http://localhost:5601/app/management/kibana/dataViews>.
3. Create a data view named `Room Booking Logs`.
4. Use index pattern `room-booking-logs-*`.
5. Select `@timestamp` as the time field.
6. Open Discover and select the new data view.

The reusable KQL searches are recorded in
[`monitoring/kibana/queries.md`](monitoring/kibana/queries.md).

## Slow-request experiment

Run all three stages with identical request counts. The script disables the
fault in a `finally` block and saves client-observed measurements:

```powershell
python experiments\anomaly_experiment.py
```

Default stages:

1. Baseline: 30 normal requests.
2. Fault: 30 requests with a 500 ms delay on every fifth creation.
3. Recovery: 30 requests after the fault is removed.

Results are written to `evidence/anomaly-results.json`. Capture the Grafana
dashboard during each stage. For a longer visible experiment:

```powershell
python experiments\anomaly_experiment.py --requests-per-stage 60 --interval 0.5
```

## Cardinality experiment

The experiment is deliberately capped at 100 unique IDs. Never raise the cap
for this assignment.

### Unsafe mode: request ID is a metric label

```powershell
$env:CARDINALITY_MODE = "unsafe"
docker compose up -d --force-recreate room-booking-api
python experiments\cardinality_test.py --count 100
```

Expected current result:

```promql
count(demo_requests_total)
```

```text
100
```

### Safe mode: request ID removed from the metric

```powershell
$env:CARDINALITY_MODE = "safe"
docker compose up -d --force-recreate room-booking-api
python experiments\cardinality_test.py --count 100
```

After another Prometheus scrape, the same query should report one current
series. Historical unsafe series remain in Prometheus until retention removes
them; removing a label does not immediately erase history.

Return to the normal default environment:

```powershell
Remove-Item Env:CARDINALITY_MODE -ErrorAction SilentlyContinue
docker compose up -d --force-recreate room-booking-api
```

Request IDs remain in JSON logs, where they can be searched without creating a
Prometheus time series for every request.

## Persistence and retention

- Bookings are intentionally in memory and disappear when the API restarts.
- Prometheus data is stored in the `prometheus-data` named volume and retained
  for seven days.
- Grafana state is stored in `grafana-data`; the submitted dashboard is also
  versioned as JSON under `monitoring/grafana/dashboards`.
- Docker stores application stdout logs using the `json-file` driver and rotates
  them at three files of 10 MB each.
- Filebeat tracks its read position in `filebeat-data`.
- Elasticsearch stores searchable logs in `elasticsearch-data`. This classroom
  stack does not automatically delete indices; they remain until its volume is
  intentionally removed.

## Stop and clean up

Stop containers while preserving monitoring data:

```powershell
docker compose down
```

Permanently delete all project containers and named data volumes:

```powershell
docker compose down -v
```

The `-v` command irreversibly removes Prometheus history, Grafana state,
Filebeat state, and Elasticsearch logs. The source code and dashboard JSON are
not deleted.

## Troubleshooting

```powershell
docker compose ps
docker compose logs --tail=100 room-booking-api
docker compose logs --tail=100 prometheus
docker compose logs --tail=100 filebeat
docker compose logs --tail=100 elasticsearch
docker compose logs --tail=100 kibana
```

If a rate or p95 panel says **No data**, generate new traffic. These panels use
recent one- or five-minute windows and correctly become empty after traffic
stops.

## Project layout

```text
app/main.py                         application, metrics, logs, fault controls
experiments/load_test.py            continuous mixed traffic
experiments/anomaly_experiment.py   baseline/fault/recovery measurement
experiments/cardinality_test.py     bounded 100-ID cardinality test
monitoring/prometheus/              scrape configuration
monitoring/grafana/                 datasource and dashboard provisioning
monitoring/filebeat/                Docker log collection and JSON parsing
monitoring/kibana/queries.md         reproducible KQL searches
evidence/                            screenshots and measured results
report.md                            assignment report draft
```

## Credits

The course's **Lab 1: Midnight Launch** was used as a reference for the Docker,
Prometheus, Grafana, Filebeat, Elasticsearch, and Kibana arrangement. OpenAI
Codex assisted with scaffolding, debugging, configuration, and documentation;
all behavior and results should be reviewed and explained by the submitting
student according to course policy.
