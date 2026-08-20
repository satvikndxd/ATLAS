# ATLAS Observability Boundary

The repository now includes an optional Compose profile for an OpenTelemetry Collector, Prometheus, and Grafana. The profile is a local integration surface; it does not imply that the current Python, .NET, database, and React path emits a single end-to-end trace in this sandbox.

## Local profile

```bash
docker compose --profile observability up
```

The collector accepts OTLP over gRPC/HTTP and exports metrics to Prometheus. The current .NET service emits structured application logs through ASP.NET logging, while Python has reference event and metric primitives. Exporter wiring and trace context propagation across API, scheduler, worker, database, CDC, and reconciliation remain the next integration step.

## Evidence required before removing the limitation

A future integration test must start a migration, execute a batch, write to a disposable SQL Server or PostgreSQL instance, reconcile the result, export a trace, and assert that `migration_id`, `job_id`, `batch_id`, `trace_id`, and `worker_id` remain correlated across the collector boundary. Until that test exists, ATLAS must not claim end-to-end OpenTelemetry coverage.
