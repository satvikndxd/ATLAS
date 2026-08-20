using System.Collections.Concurrent;
using System.Text.Json;
using Atlas.ControlPlane;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddOpenApi();
builder.Services.AddSingleton<AtlasStore>();
builder.Services.AddSingleton<IPolicyEngine, PolicyEngine>();
builder.Services.AddSingleton<IMigrationManager, MigrationManager>();
builder.Services.AddSingleton<IApprovalEngine, ApprovalEngine>();
builder.Services.AddSingleton<IncidentManager>();
builder.Services.AddSingleton<ReconciliationCoordinator>();
builder.Services.AddSingleton<CutoverCoordinator>();
builder.Services.AddHostedService<AtlasScheduler>();
var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { status = "healthy", service = "atlas-control-plane", semantics = "reference-control-plane" }));
app.MapGet("/api/v1/migrations", (AtlasStore store) => Results.Ok(store.Migrations.Values));
app.MapGet("/api/v1/migrations/{id}", (string id, AtlasStore store) => store.Migrations.TryGetValue(id, out var migration) ? Results.Ok(migration) : Results.NotFound());
app.MapPost("/api/v1/migrations", (MigrationRequest request, AtlasStore store) =>
{
    if (string.IsNullOrWhiteSpace(request.MigrationId)) return Results.BadRequest(new { error = "migration_id is required" });
    var migration = new Migration(request.MigrationId, "DRAFT", request.Source, request.Target, DateTimeOffset.UtcNow);
    store.Migrations[request.MigrationId] = migration;
    store.Audit.Add(new AuditEvent("CREATE_MIGRATION", request.MigrationId, "control-plane", DateTimeOffset.UtcNow));
    return Results.Created($"/api/v1/migrations/{request.MigrationId}", migration);
});
app.MapPost("/api/v1/migrations/{id}/pause", (string id, AtlasStore store) => store.Transition(id, "PAUSED"));
app.MapPost("/api/v1/migrations/{id}/resume", (string id, AtlasStore store) => store.Transition(id, "RUNNING"));
app.MapPost("/api/v1/migrations/{id}/abort", (string id, AtlasStore store) => store.Transition(id, "ABORTED"));
app.MapGet("/api/v1/workers", (AtlasStore store) => Results.Ok(store.Workers));
app.MapGet("/api/v1/reconciliation/{id}", (string id, AtlasStore store) => Results.Ok(store.Reconciliations.Where(item => item.MigrationId == id)));
app.MapGet("/api/v1/audit", (AtlasStore store) => Results.Ok(store.Audit));
app.MapGet("/api/v1/approvals", (AtlasStore store) => Results.Ok(store.Approvals));
app.MapGet("/api/v1/control/migrations", (IMigrationManager manager) => Results.Ok(manager.All()));
app.MapPost("/api/v1/control/migrations", (MigrationRequest request, IMigrationManager manager) => Results.Ok(manager.Create(request.MigrationId, request.Source, request.Target)));
app.MapPost("/api/v1/control/migrations/{id}/transition", (string id, TransitionRequest request, IMigrationManager manager) => Results.Ok(manager.Transition(id, request.State, request.Actor)));
app.MapPost("/api/v1/control/approvals", (ApprovalRequest request, IApprovalEngine approvals) => Results.Ok(approvals.Request(request.MigrationId, request.Operation, request.Actor)));
app.MapPost("/api/v1/control/approvals/{id}/approve", (string id, ApproveRequest request, IApprovalEngine approvals) => Results.Ok(approvals.Approve(id, request.Approver)));
app.MapGet("/api/v1/control/incidents", (IncidentManager incidents) => Results.Ok(incidents.All()));
app.MapPost("/api/v1/control/incidents", (IncidentRequest request, IncidentManager incidents) => Results.Ok(incidents.Create(request.MigrationId, request.Severity, request.Title)));
app.MapGet("/api/v1/control/reconciliation", (ReconciliationCoordinator coordinator) => Results.Ok(coordinator.All()));
app.MapPost("/api/v1/control/reconciliation", (ReconciliationRequest request, ReconciliationCoordinator coordinator) => Results.Ok(coordinator.Record(request.MigrationId, request.Table, request.ByteEquivalent, request.SemanticEquivalent, request.FinancialInvariantsPassed)));
app.MapPost("/api/v1/control/cutover/precheck", (PolicyInput input, CutoverCoordinator coordinator) => Results.Ok(coordinator.Precheck(input)));
if (app.Environment.IsDevelopment()) app.MapOpenApi();
app.Run();

record MigrationRequest(string MigrationId, string Source, string Target);
record TransitionRequest(string State, string Actor);
record ApprovalRequest(string MigrationId, string Operation, string Actor);
record ApproveRequest(string Approver);
record IncidentRequest(string MigrationId, string Severity, string Title);
record ReconciliationRequest(string MigrationId, string Table, bool ByteEquivalent, bool SemanticEquivalent, bool FinancialInvariantsPassed);
record Migration(string MigrationId, string State, string Source, string Target, DateTimeOffset CreatedAt);
record Worker(string WorkerId, string Status, DateTimeOffset LastHeartbeat);
record Reconciliation(string MigrationId, string Table, bool Passed, DateTimeOffset CreatedAt);
record AuditEvent(string Action, string MigrationId, string Actor, DateTimeOffset CreatedAt);
record Approval(string ApprovalId, string Operation, string Status, string RequestedBy);

sealed class AtlasStore
{
    public ConcurrentDictionary<string, Migration> Migrations { get; } = new();
    public ConcurrentBag<Worker> Workers { get; } = new(new[] { new Worker("control-plane", "READY", DateTimeOffset.UtcNow) });
    public ConcurrentBag<Reconciliation> Reconciliations { get; } = new();
    public ConcurrentBag<AuditEvent> Audit { get; } = new();
    public ConcurrentBag<Approval> Approvals { get; } = new();

    public IResult Transition(string id, string state)
    {
        if (!Migrations.TryGetValue(id, out var old)) return Results.NotFound();
        var next = old with { State = state };
        Migrations[id] = next;
        Audit.Add(new AuditEvent($"STATE_{state}", id, "control-plane", DateTimeOffset.UtcNow));
        return Results.Ok(next);
    }
}
