# Kibana queries

Create a data view named **Room Booking Logs** with the index pattern
`room-booking-logs-*` and `@timestamp` as its time field. The following Kibana
Query Language (KQL) searches are used by this project:

```text
service.name: "room-booking-api"
```

```text
service.name: "room-booking-api" and log.level: "warning"
```

```text
event_type: "booking_rejected"
```

```text
status >= 400
```

To follow one request, copy an `X-Request-ID` response header or a `request_id`
from a log event and search:

```text
request_id: "PASTE-REQUEST-ID-HERE"
```

Useful columns in Discover are `@timestamp`, `service.name`, `log.level`,
`message`, `request_id`, `event_type`, `method`, `route`, `status`, and
`duration_ms`.
