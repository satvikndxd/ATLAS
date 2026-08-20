using System.Collections.Concurrent;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddOpenApi();
builder.Services.AddSingleton<AtlasStore>();
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
if (app.Environment.IsDevelopment()) app.MapOpenApi();
app.Run();

record MigrationRequest(string MigrationId, string Source, string Target);
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
