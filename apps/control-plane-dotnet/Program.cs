using System.Text.Json;
using Atlas.ControlPlane;

var mode = (Environment.GetEnvironmentVariable("ATLAS_MODE") ?? "demo").Trim().ToLowerInvariant();
var requireAuth = bool.TryParse(Environment.GetEnvironmentVariable("ATLAS_REQUIRE_AUTH"), out var configuredAuth) ? configuredAuth : mode == "live";
var apiKey = Environment.GetEnvironmentVariable("ATLAS_API_KEY");
if (mode == "live" && requireAuth && string.IsNullOrWhiteSpace(apiKey)) throw new InvalidOperationException("ATLAS_API_KEY is required when ATLAS_MODE=live and authentication is enabled");
var allowedOrigins = (Environment.GetEnvironmentVariable("ATLAS_ALLOWED_ORIGINS") ?? "http://localhost:4173").Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddCors(options => options.AddDefaultPolicy(policy => policy.WithOrigins(allowedOrigins).AllowAnyHeader().AllowAnyMethod()));
builder.Services.ConfigureHttpJsonOptions(options => options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower);
builder.Services.AddSingleton<IMigrationService, MigrationService>();
builder.Services.AddSingleton<IJobService, JobService>();
builder.Services.AddSingleton<IApprovalService, ApprovalService>();
builder.Services.AddSingleton<IncidentService>();
builder.Services.AddSingleton<ReconciliationService>();
builder.Services.AddSingleton<IPolicyService, PolicyService>();
builder.Services.AddSingleton<CutoverService>();
builder.Services.AddHostedService<AtlasScheduler>();

var app = builder.Build();
app.UseCors();
app.Use(async (context, next) =>
{
    if (requireAuth && context.Request.Path.StartsWithSegments("/api") && !context.Request.Path.StartsWithSegments("/api/v1/health"))
    {
        if (string.IsNullOrWhiteSpace(apiKey) || !context.Request.Headers.TryGetValue("X-ATLAS-API-Key", out var presented) || presented != apiKey)
        {
            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            await context.Response.WriteAsJsonAsync(new { schema_version = ContractVersion.V1, error = "authentication_required" });
            return;
        }
    }
    await next();
});

app.MapGet("/health", () => Results.Ok(new { schema_version = ContractVersion.V1, status = "healthy", service = "atlas-control-plane" }));
app.MapGet("/api/v1/health", () => Results.Ok(new { schema_version = ContractVersion.V1, status = "healthy", service = "atlas-control-plane" }));

app.MapGet("/api/v1/migrations", (IMigrationService service) => Results.Ok(service.All()));
app.MapPost("/api/v1/migrations", (MigrationRequest request, IMigrationService service) =>
{
    try { return Results.Created($"/api/v1/migrations/{request.MigrationId}", service.Create(request.MigrationId, request.Source, request.Target)); }
    catch (ArgumentException error) { return Results.BadRequest(new { schema_version = ContractVersion.V1, error = error.Message }); }
    catch (InvalidOperationException error) { return Results.Conflict(new { schema_version = ContractVersion.V1, error = error.Message }); }
});
app.MapGet("/api/v1/migrations/{id}", (string id, IMigrationService service) => service.Get(id) is { } migration ? Results.Ok(migration) : Results.NotFound(new { schema_version = ContractVersion.V1, error = "migration_not_found", migration_id = id }));
app.MapPost("/api/v1/migrations/{id}/start", (string id, TransitionRequest request, IMigrationService service) => Transition(id, "RUNNING", request.Actor, service));
app.MapPost("/api/v1/migrations/{id}/pause", (string id, TransitionRequest request, IMigrationService service) => Transition(id, "PAUSED", request.Actor, service));
app.MapPost("/api/v1/migrations/{id}/resume", (string id, TransitionRequest request, IMigrationService service) => Transition(id, "RUNNING", request.Actor, service));
app.MapPost("/api/v1/migrations/{id}/abort", (string id, TransitionRequest request, IMigrationService service) => Transition(id, "ABORTED", request.Actor, service));
app.MapPost("/api/v1/migrations/{id}/jobs", (string id, JobRequest request, IMigrationService migrations, IJobService jobs) => migrations.Get(id) is null ? Results.NotFound(new { schema_version = ContractVersion.V1, error = "migration_not_found" }) : Results.Created($"/api/v1/jobs", jobs.Create(id, request.Table, request.Partition)));
app.MapGet("/api/v1/migrations/{id}/jobs", (string id, IJobService jobs) => Results.Ok(jobs.All(id)));
app.MapGet("/api/v1/migrations/{id}/reconciliation", (string id, ReconciliationService reconciliation) => Results.Ok(reconciliation.All(id)));
app.MapGet("/api/v1/migrations/{id}/incidents", (string id, IncidentService incidents) => Results.Ok(incidents.All(id)));

app.MapGet("/api/v1/workers", (IJobService jobs) => Results.Ok(jobs.Workers()));
app.MapGet("/api/v1/jobs", (IJobService jobs) => Results.Ok(jobs.All()));
app.MapGet("/api/v1/approvals", (string? migrationId, IApprovalService approvals) => Results.Ok(approvals.All(migrationId)));
app.MapPost("/api/v1/approvals", (ApprovalRequest request, IApprovalService approvals) => Results.Created("/api/v1/approvals", approvals.Request(request.MigrationId, request.Operation, request.Actor)));
app.MapPost("/api/v1/approvals/{id}/approve", (string id, ApprovalDecisionRequest request, IApprovalService approvals) => approvals.Approve(id, request.Approver, request.Reason, out var error) is { } approval ? Results.Ok(approval) : Results.NotFound(new { schema_version = ContractVersion.V1, error }));
app.MapPost("/api/v1/policies/precheck", (PolicyInput input, IPolicyService policies) => Results.Ok(policies.Precheck(input)));
app.MapPost("/api/v1/cutover/precheck", (PolicyInput input, CutoverService cutover) => Results.Ok(cutover.Precheck(input)));
app.MapPost("/api/v1/cutover/approve", (ApprovalRequest request, IApprovalService approvals, IPolicyService policies) => Results.Ok(new { schema_version = ContractVersion.V1, approval = approvals.Request(request.MigrationId, "CUTOVER", request.Actor), policy = policies.Precheck(new PolicyInput(true, 0, false, false, 0.0)) }));
app.MapPost("/api/v1/incidents", (IncidentRequest request, IncidentService incidents) => Results.Created("/api/v1/incidents", incidents.Create(request.MigrationId, request.Severity, request.Title, request.Hypothesis)));
app.MapGet("/api/v1/incidents", (string? migrationId, IncidentService incidents) => Results.Ok(incidents.All(migrationId)));
app.MapPost("/api/v1/reconciliation", (ReconciliationRequest request, ReconciliationService reconciliation) => Results.Created("/api/v1/reconciliation", reconciliation.Record(request.MigrationId, request.Table, request.ByteEquivalent, request.SemanticEquivalent, request.FinancialInvariantsPassed, request.SourceCount, request.TargetCount)));

app.MapGet("/openapi.json", () => Results.Json(new
{
    openapi = "3.0.0",
    info = new { title = "ATLAS Control Plane", version = ContractVersion.V1 },
    paths = new Dictionary<string, object>
    {
        ["/api/v1/health"] = new { get = new { responses = new Dictionary<string, object> { ["200"] = new { description = "Healthy" } } } },
        ["/api/v1/migrations"] = new { get = new { responses = new Dictionary<string, object> { ["200"] = new { description = "Migration list" } } }, post = new { responses = new Dictionary<string, object> { ["201"] = new { description = "Migration created" } } } },
        ["/api/v1/jobs"] = new { get = new { responses = new Dictionary<string, object> { ["200"] = new { description = "Job list" } } } },
        ["/api/v1/workers"] = new { get = new { responses = new Dictionary<string, object> { ["200"] = new { description = "Worker list" } } } },
        ["/api/v1/reconciliation"] = new { post = new { responses = new Dictionary<string, object> { ["201"] = new { description = "Reconciliation recorded" } } } },
        ["/api/v1/incidents"] = new { get = new { responses = new Dictionary<string, object> { ["200"] = new { description = "Incident list" } } }, post = new { responses = new Dictionary<string, object> { ["201"] = new { description = "Incident created" } } } },
        ["/api/v1/approvals"] = new { get = new { responses = new Dictionary<string, object> { ["200"] = new { description = "Approval list" } } }, post = new { responses = new Dictionary<string, object> { ["201"] = new { description = "Approval requested" } } } },
        ["/api/v1/policies/precheck"] = new { post = new { responses = new Dictionary<string, object> { ["200"] = new { description = "Policy decision" } } } },
        ["/api/v1/cutover/precheck"] = new { post = new { responses = new Dictionary<string, object> { ["200"] = new { description = "Cutover policy decision" } } } },
        ["/api/v1/cutover/approve"] = new { post = new { responses = new Dictionary<string, object> { ["200"] = new { description = "Cutover approval" } } } }
    }
}));

app.Run();

static IResult Transition(string id, string state, string actor, IMigrationService service)
{
    var updated = service.Transition(id, state, actor, out var error);
    return updated is not null ? Results.Ok(updated) : Results.NotFound(new { schema_version = ContractVersion.V1, error });
}

public record MigrationRequest(string MigrationId, string Source, string Target);
public record TransitionRequest(string Actor = "operator");
public record JobRequest(string? Table, string? Partition);
public record ApprovalRequest(string MigrationId, string Operation, string Actor);
public record ApprovalDecisionRequest(string Approver, string? Reason);
public record IncidentRequest(string MigrationId, string Severity, string Title, string? Hypothesis);
public record ReconciliationRequest(string MigrationId, string Table, bool? ByteEquivalent, bool? SemanticEquivalent, bool FinancialInvariantsPassed, int SourceCount, int TargetCount);
