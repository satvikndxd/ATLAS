using Atlas.ControlPlane;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace Atlas.ControlPlane.Tests;

public class ControlPlaneTests
{
    [Fact]
    public void MigrationLifecycleIsRealAndTerminalStatesAreProtected()
    {
        var service = new MigrationService(NullLogger<MigrationService>.Instance);
        var created = service.Create("migration-test", "legacy", "modern");
        Assert.Equal("1.0", created.SchemaVersion);
        Assert.Equal("DRAFT", created.State);
        var running = service.Transition("migration-test", "RUNNING", "test", out var error);
        Assert.Null(error);
        Assert.Equal("RUNNING", running!.State);
        var completed = service.Transition("migration-test", "COMPLETED", "test", out error);
        Assert.Null(error);
        Assert.Equal("COMPLETED", completed!.State);
        var invalid = service.Transition("migration-test", "RUNNING", "test", out error);
        Assert.Null(invalid);
        Assert.Contains("terminal", error);
    }

    [Fact]
    public void JobsAreCreatedWithStableSchemaAndQueuedState()
    {
        var jobs = new JobService();
        var job = jobs.Create("migration-test", "accounts", "partition-1");
        Assert.Equal("1.0", job.SchemaVersion);
        Assert.Equal("QUEUED", job.State);
        Assert.Contains(jobs.All("migration-test"), item => item.JobId == job.JobId);
    }

    [Fact]
    public void PolicyDeniesUnsafeCutoverInputs()
    {
        var policy = new PolicyService();
        var decision = policy.Precheck(new PolicyInput(false, 4, true, true, 0.9));
        Assert.False(decision.Allowed);
        Assert.Contains("reconciliation_failed", decision.Reasons);
        Assert.Contains("raw_pii_logging_denied", decision.Reasons);
    }

    [Fact]
    public void ApprovalIncidentAndReconciliationRecordsAreQueryable()
    {
        var approvals = new ApprovalService();
        var approval = approvals.Request("migration-test", "CUTOVER", "operator");
        var approved = approvals.Approve(approval.ApprovalId, "reviewer", "verified", out var error);
        Assert.Null(error);
        Assert.Equal("APPROVED", approved!.Status);

        var incidents = new IncidentService();
        var incident = incidents.Create("migration-test", "HIGH", "worker failed");
        Assert.Contains(incidents.All("migration-test"), item => item.IncidentId == incident.IncidentId);

        var reconciliation = new ReconciliationService();
        var report = reconciliation.Record("migration-test", "accounts", true, true, true, 10, 10);
        Assert.Equal("PASSED", report.Status);
    }
}
