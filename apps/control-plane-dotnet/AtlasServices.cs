using System.Collections.Concurrent;
using Microsoft.Extensions.Hosting;

namespace Atlas.ControlPlane;

public record AtlasMigration(string MigrationId, string State, string Source, string Target, string PlanVersion, DateTimeOffset UpdatedAt);
public record AtlasApproval(string ApprovalId, string MigrationId, string Operation, string RequestedBy, string? ApprovedBy, string Status, DateTimeOffset UpdatedAt);
public record AtlasIncident(string IncidentId, string MigrationId, string Severity, string Title, string Status, DateTimeOffset CreatedAt);
public record AtlasReconciliation(string MigrationId, string Table, bool ByteEquivalent, bool SemanticEquivalent, bool FinancialInvariantsPassed, DateTimeOffset CreatedAt);

public interface IPolicyEngine
{
    PolicyDecision Evaluate(PolicyInput input);
}

public sealed record PolicyInput(bool ReconciliationPassed, int CdcLag, bool BreakingSchemaChange, bool PiiLogging, double RiskScore);
public sealed record PolicyDecision(bool Allowed, IReadOnlyList<string> Reasons);

public sealed class PolicyEngine : IPolicyEngine
{
    public PolicyDecision Evaluate(PolicyInput input)
    {
        var reasons = new List<string>();
        if (!input.ReconciliationPassed) reasons.Add("reconciliation failed");
        if (input.CdcLag > 0) reasons.Add("CDC lag exceeds policy");
        if (input.BreakingSchemaChange) reasons.Add("breaking schema change requires approval");
        if (input.PiiLogging) reasons.Add("raw PII logging is denied");
        if (input.RiskScore >= .5) reasons.Add("risk score requires human approval");
        return new PolicyDecision(reasons.Count == 0, reasons);
    }
}

public interface IMigrationManager
{
    AtlasMigration Create(string migrationId, string source, string target);
    AtlasMigration Transition(string migrationId, string nextState, string actor);
    IReadOnlyCollection<AtlasMigration> All();
}

public sealed class MigrationManager : IMigrationManager
{
    private readonly ConcurrentDictionary<string, AtlasMigration> _migrations = new();
    private readonly ILogger<MigrationManager> _logger;

    public MigrationManager(ILogger<MigrationManager> logger) => _logger = logger;

    public AtlasMigration Create(string migrationId, string source, string target)
    {
        var migration = new AtlasMigration(migrationId, "DRAFT", source, target, "plan-v1", DateTimeOffset.UtcNow);
        _migrations[migrationId] = migration;
        _logger.LogInformation("Migration {MigrationId} created in state {State}", migrationId, migration.State);
        return migration;
    }

    public AtlasMigration Transition(string migrationId, string nextState, string actor)
    {
        if (!_migrations.TryGetValue(migrationId, out var current)) throw new KeyNotFoundException(migrationId);
        var next = current with { State = nextState, UpdatedAt = DateTimeOffset.UtcNow };
        _migrations[migrationId] = next;
        _logger.LogInformation("Migration {MigrationId} transitioned {OldState}->{NewState} by {Actor}", migrationId, current.State, nextState, actor);
        return next;
    }

    public IReadOnlyCollection<AtlasMigration> All() => _migrations.Values.ToArray();
}

public interface IApprovalEngine
{
    AtlasApproval Request(string migrationId, string operation, string actor);
    AtlasApproval Approve(string approvalId, string approver);
}

public sealed class ApprovalEngine : IApprovalEngine
{
    private readonly ConcurrentDictionary<string, AtlasApproval> _approvals = new();

    public AtlasApproval Request(string migrationId, string operation, string actor)
    {
        var approval = new AtlasApproval(Guid.NewGuid().ToString("N"), migrationId, operation, actor, null, "PENDING", DateTimeOffset.UtcNow);
        _approvals[approval.ApprovalId] = approval;
        return approval;
    }

    public AtlasApproval Approve(string approvalId, string approver)
    {
        if (!_approvals.TryGetValue(approvalId, out var approval)) throw new KeyNotFoundException(approvalId);
        var updated = approval with { ApprovedBy = approver, Status = "APPROVED", UpdatedAt = DateTimeOffset.UtcNow };
        _approvals[approvalId] = updated;
        return updated;
    }
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

public sealed class IncidentManager
{
    private readonly ConcurrentBag<AtlasIncident> _incidents = new();
    public AtlasIncident Create(string migrationId, string severity, string title)
    {
        var incident = new AtlasIncident(Guid.NewGuid().ToString("N"), migrationId, severity, title, "OPEN", DateTimeOffset.UtcNow);
        _incidents.Add(incident);
        return incident;
    }
    public IReadOnlyCollection<AtlasIncident> All() => _incidents.ToArray();
}

public sealed class ReconciliationCoordinator
{
    private readonly ConcurrentBag<AtlasReconciliation> _reports = new();
    public AtlasReconciliation Record(string migrationId, string table, bool byteEquivalent, bool semanticEquivalent, bool financialInvariantsPassed)
    {
        var report = new AtlasReconciliation(migrationId, table, byteEquivalent, semanticEquivalent, financialInvariantsPassed, DateTimeOffset.UtcNow);
        _reports.Add(report);
        return report;
    }
    public IReadOnlyCollection<AtlasReconciliation> All() => _reports.ToArray();
}

public sealed class CutoverCoordinator
{
    private readonly IPolicyEngine _policy;
    public CutoverCoordinator(IPolicyEngine policy) => _policy = policy;
    public PolicyDecision Precheck(PolicyInput input) => _policy.Evaluate(input);
}
