using System.Collections.Concurrent;

namespace Atlas.ControlPlane;

public static class ContractVersion
{
    public const string V1 = "1.0";
}

public record AtlasMigration(
    string SchemaVersion,
    string MigrationId,
    string State,
    string Source,
    string Target,
    string PlanVersion,
    double Progress,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);

public record AtlasJob(
    string SchemaVersion,
    string JobId,
    string MigrationId,
    string State,
    string? Table,
    string? Partition,
    string? WorkerId,
    string? LeaseId,
    DateTimeOffset? LeaseExpiry,
    int Attempt,
    double Progress,
    DateTimeOffset UpdatedAt);

public record AtlasWorker(string SchemaVersion, string WorkerId, string Status, DateTimeOffset LastHeartbeat);

public record AtlasApproval(
    string SchemaVersion,
    string ApprovalId,
    string MigrationId,
    string Operation,
    string RequestedBy,
    string? ApprovedBy,
    string Status,
    string? DecisionReason,
    DateTimeOffset RequestedAt,
    DateTimeOffset UpdatedAt);

public record AtlasIncident(
    string SchemaVersion,
    string IncidentId,
    string MigrationId,
    string Severity,
    string Title,
    string Status,
    string? Hypothesis,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);

public record AtlasReconciliation(
    string SchemaVersion,
    string ReconciliationId,
    string MigrationId,
    string Table,
    string Status,
    bool? ByteEquivalent,
    bool? SemanticEquivalent,
    bool FinancialInvariantsPassed,
    int SourceCount,
    int TargetCount,
    DateTimeOffset CreatedAt);

public record PolicyInput(bool ReconciliationPassed, int CdcLag, bool BreakingSchemaChange, bool PiiLogging, double RiskScore);
public record PolicyDecision(string SchemaVersion, string DecisionId, string PolicyVersion, bool Allowed, IReadOnlyList<string> Reasons, DateTimeOffset EvaluatedAt);

public interface IMigrationService
{
    AtlasMigration Create(string migrationId, string source, string target);
    AtlasMigration? Get(string migrationId);
    IReadOnlyCollection<AtlasMigration> All();
    AtlasMigration? Transition(string migrationId, string nextState, string actor, out string? error);
}

public sealed class MigrationService : IMigrationService
{
    private static readonly HashSet<string> AllowedStates = new(StringComparer.OrdinalIgnoreCase)
    {
        "DRAFT", "VALIDATING", "PLANNED", "APPROVAL_REQUIRED", "APPROVED", "RUNNING", "PAUSED", "RECOVERING", "RECONCILING", "VERIFIED", "CUTOVER_READY", "CUTOVER", "COMPLETED", "FAILED", "ABORTED", "ROLLED_BACK"
    };

    private readonly ConcurrentDictionary<string, AtlasMigration> _migrations = new();
    private readonly ILogger<MigrationService> _logger;

    public MigrationService(ILogger<MigrationService> logger) => _logger = logger;

    public AtlasMigration Create(string migrationId, string source, string target)
    {
        if (string.IsNullOrWhiteSpace(migrationId)) throw new ArgumentException("migration_id is required", nameof(migrationId));
        var now = DateTimeOffset.UtcNow;
        var migration = new AtlasMigration(ContractVersion.V1, migrationId, "DRAFT", source, target, "plan-v1", 0.0, now, now);
        if (!_migrations.TryAdd(migrationId, migration)) throw new InvalidOperationException($"migration already exists: {migrationId}");
        _logger.LogInformation("Created migration {MigrationId}", migrationId);
        return migration;
    }

    public AtlasMigration? Get(string migrationId) => _migrations.TryGetValue(migrationId, out var migration) ? migration : null;

    public IReadOnlyCollection<AtlasMigration> All() => _migrations.Values.OrderBy(item => item.CreatedAt).ToArray();

    public AtlasMigration? Transition(string migrationId, string nextState, string actor, out string? error)
    {
        error = null;
        if (!AllowedStates.Contains(nextState)) { error = $"unsupported state: {nextState}"; return null; }
        if (!_migrations.TryGetValue(migrationId, out var current)) { error = $"migration not found: {migrationId}"; return null; }
        if (current.State == "COMPLETED" || current.State == "ABORTED" || current.State == "FAILED" || current.State == "ROLLED_BACK") { error = $"terminal migration cannot transition: {current.State}"; return null; }
        var updated = current with { State = nextState.ToUpperInvariant(), UpdatedAt = DateTimeOffset.UtcNow };
        _migrations[migrationId] = updated;
        _logger.LogInformation("Migration {MigrationId} transitioned {OldState}->{NewState} by {Actor}", migrationId, current.State, updated.State, actor);
        return updated;
    }
}

public interface IJobService
{
    IReadOnlyCollection<AtlasJob> All(string? migrationId = null);
    IReadOnlyCollection<AtlasWorker> Workers();
    AtlasJob Create(string migrationId, string? table, string? partition);
}

public sealed class JobService : IJobService
{
    private readonly ConcurrentDictionary<string, AtlasJob> _jobs = new();
    private readonly ConcurrentDictionary<string, AtlasWorker> _workers = new();

    public JobService()
    {
        _workers["control-plane"] = new AtlasWorker(ContractVersion.V1, "control-plane", "READY", DateTimeOffset.UtcNow);
    }

    public AtlasJob Create(string migrationId, string? table, string? partition)
    {
        var now = DateTimeOffset.UtcNow;
        var job = new AtlasJob(ContractVersion.V1, Guid.NewGuid().ToString("N"), migrationId, "QUEUED", table, partition, null, null, null, 0, 0.0, now);
        _jobs[job.JobId] = job;
        return job;
    }

    public IReadOnlyCollection<AtlasJob> All(string? migrationId = null) => _jobs.Values.Where(job => migrationId is null || job.MigrationId == migrationId).OrderBy(job => job.UpdatedAt).ToArray();
    public IReadOnlyCollection<AtlasWorker> Workers() => _workers.Values.OrderBy(worker => worker.WorkerId).ToArray();
}

public interface IApprovalService
{
    IReadOnlyCollection<AtlasApproval> All(string? migrationId = null);
    AtlasApproval Request(string migrationId, string operation, string actor);
    AtlasApproval? Approve(string approvalId, string approver, string? reason, out string? error);
}

public sealed class ApprovalService : IApprovalService
{
    private readonly ConcurrentDictionary<string, AtlasApproval> _approvals = new();

    public IReadOnlyCollection<AtlasApproval> All(string? migrationId = null) => _approvals.Values.Where(item => migrationId is null || item.MigrationId == migrationId).OrderBy(item => item.RequestedAt).ToArray();

    public AtlasApproval Request(string migrationId, string operation, string actor)
    {
        var now = DateTimeOffset.UtcNow;
        var approval = new AtlasApproval(ContractVersion.V1, Guid.NewGuid().ToString("N"), migrationId, operation, actor, null, "PENDING", null, now, now);
        _approvals[approval.ApprovalId] = approval;
        return approval;
    }

    public AtlasApproval? Approve(string approvalId, string approver, string? reason, out string? error)
    {
        error = null;
        if (!_approvals.TryGetValue(approvalId, out var approval)) { error = $"approval not found: {approvalId}"; return null; }
        if (approval.Status != "PENDING") { error = $"approval is not pending: {approval.Status}"; return null; }
        var updated = approval with { ApprovedBy = approver, Status = "APPROVED", DecisionReason = reason, UpdatedAt = DateTimeOffset.UtcNow };
        _approvals[approvalId] = updated;
        return updated;
    }
}

public sealed class IncidentService
{
    private readonly ConcurrentDictionary<string, AtlasIncident> _incidents = new();
    public IReadOnlyCollection<AtlasIncident> All(string? migrationId = null) => _incidents.Values.Where(item => migrationId is null || item.MigrationId == migrationId).OrderByDescending(item => item.CreatedAt).ToArray();
    public AtlasIncident Create(string migrationId, string severity, string title, string? hypothesis = null)
    {
        var now = DateTimeOffset.UtcNow;
        var incident = new AtlasIncident(ContractVersion.V1, Guid.NewGuid().ToString("N"), migrationId, severity.ToUpperInvariant(), title, "OPEN", hypothesis, now, now);
        _incidents[incident.IncidentId] = incident;
        return incident;
    }
}

public sealed class ReconciliationService
{
    private readonly ConcurrentBag<AtlasReconciliation> _reports = new();
    public IReadOnlyCollection<AtlasReconciliation> All(string? migrationId = null) => _reports.Where(item => migrationId is null || item.MigrationId == migrationId).OrderByDescending(item => item.CreatedAt).ToArray();
    public AtlasReconciliation Record(string migrationId, string table, bool? byteEquivalent, bool? semanticEquivalent, bool financialInvariantsPassed, int sourceCount, int targetCount)
    {
        var status = byteEquivalent == true && semanticEquivalent == true && financialInvariantsPassed && sourceCount == targetCount ? "PASSED" : "INCONCLUSIVE";
        var report = new AtlasReconciliation(ContractVersion.V1, Guid.NewGuid().ToString("N"), migrationId, table, status, byteEquivalent, semanticEquivalent, financialInvariantsPassed, sourceCount, targetCount, DateTimeOffset.UtcNow);
        _reports.Add(report);
        return report;
    }
}

public interface IPolicyService
{
    PolicyDecision Precheck(PolicyInput input);
}

public sealed class PolicyService : IPolicyService
{
    public PolicyDecision Precheck(PolicyInput input)
    {
        var reasons = new List<string>();
        if (!input.ReconciliationPassed) reasons.Add("reconciliation_failed");
        if (input.CdcLag > 0) reasons.Add("cdc_lag_exceeds_policy");
        if (input.BreakingSchemaChange) reasons.Add("breaking_schema_change");
        if (input.PiiLogging) reasons.Add("raw_pii_logging_denied");
        if (input.RiskScore >= 0.5) reasons.Add("risk_requires_approval");
        return new PolicyDecision(ContractVersion.V1, Guid.NewGuid().ToString("N"), "policy-v1", reasons.Count == 0, reasons, DateTimeOffset.UtcNow);
    }
}

public sealed class CutoverService
{
    private readonly IPolicyService _policy;
    public CutoverService(IPolicyService policy) => _policy = policy;
    public PolicyDecision Precheck(PolicyInput input) => _policy.Precheck(input);
}

public sealed class AtlasScheduler : BackgroundService
{
    private readonly ILogger<AtlasScheduler> _logger;
    public AtlasScheduler(ILogger<AtlasScheduler> logger) => _logger = logger;
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("ATLAS scheduler started");
        while (!stoppingToken.IsCancellationRequested)
        {
            _logger.LogDebug("ATLAS scheduler heartbeat at {Time}", DateTimeOffset.UtcNow);
            await Task.Delay(TimeSpan.FromSeconds(15), stoppingToken);
        }
    }
}
