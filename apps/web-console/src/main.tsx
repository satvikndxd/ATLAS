import { useMemo, useState, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Code2,
  Database,
  ExternalLink,
  FileCheck2,
  GitBranch,
  Globe2,
  Grid2X2,
  History,
  Layers3,
  LineChart,
  LockKeyhole,
  Menu,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  Zap,
} from 'lucide-react'
import './styles.css'

type ViewId = 'overview' | 'archaeology' | 'genome' | 'migration' | 'evidence' | 'incidents' | 'research'

type EvidenceState = 'OBSERVED' | 'DERIVED' | 'INFERRED' | 'SIMULATED' | 'CONTRADICTED'

const nav: Array<{ id: ViewId; label: string; icon: typeof Activity; group: string }> = [
  { id: 'overview', label: 'Overview', icon: Grid2X2, group: 'Workspace' },
  { id: 'archaeology', label: 'System archaeology', icon: Search, group: 'Workspace' },
  { id: 'genome', label: 'Data Genome', icon: Boxes, group: 'Workspace' },
  { id: 'migration', label: 'Migration runtime', icon: Layers3, group: 'Workspace' },
  { id: 'evidence', label: 'Evidence ledger', icon: FileCheck2, group: 'Proof' },
  { id: 'incidents', label: 'Incidents', icon: AlertTriangle, group: 'Proof' },
  { id: 'research', label: 'Research lab', icon: LineChart, group: 'Research' },
]

const metrics = [
  { label: 'Semantic preservation', value: '99.94%', delta: '+0.18%', tone: 'green', caption: 'after canonical normalization' },
  { label: 'Integrity debt', value: '14', delta: '3 open', tone: 'amber', caption: 'inherited source exceptions' },
  { label: 'CDC lag', value: '0.0 s', delta: 'within policy', tone: 'blue', caption: 'last source position 8,431' },
  { label: 'Proof coverage', value: '92.6%', delta: '+4.1%', tone: 'purple', caption: 'required certificate gates' },
]

const trend = [34, 44, 38, 54, 48, 66, 58, 72, 70, 78, 83, 91]
const genomeRows = [
  { name: 'accounts', type: 'entity', value: '20 columns · 2 relationships', status: 'Observed', confidence: '0.99' },
  { name: 'transactions', type: 'entity', value: '17 columns · 4 lifecycles', status: 'Derived', confidence: '0.96' },
  { name: 'customer_ref → customer_no', type: 'relationship', value: 'join coverage 99.8%', status: 'Inferred', confidence: '0.91' },
  { name: 'account conservation', type: 'invariant', value: 'opening + credits − debits + adjustments', status: 'Validated', confidence: '0.98' },
]

const incidents = [
  { id: 'INC-042', title: 'Duplicate customer identity', source: 'legacy_customers', status: 'Open', severity: 'Medium', time: '12 min ago', detail: '1 inherited duplicate key is quarantined from canonical reconciliation.' },
  { id: 'INC-041', title: 'CDC gap recovered', source: 'legacy_transactions', status: 'Resolved', severity: 'High', time: '1 hr ago', detail: 'Sequence 8,404–8,406 replayed from immutable source snapshot.' },
  { id: 'INC-039', title: 'Schema drift detected', source: 'legacy_accounts', status: 'Acknowledged', severity: 'Low', time: '3 hr ago', detail: 'acct_bal widened from VARCHAR(32) to VARCHAR(64); mapping unchanged.' },
]

const evidence = [
  { id: 'EVD-83FA', claim: 'Source timestamps are UTC', state: 'INFERRED' as EvidenceState, confidence: 0.94, age: 'verified 2d ago', source: 'legacy_accounts.profile' },
  { id: 'EVD-771B', claim: 'Account conservation holds', state: 'DERIVED' as EvidenceState, confidence: 0.98, age: 'verified 18m ago', source: 'reconcile.accounts' },
  { id: 'EVD-620C', claim: 'customer_ref identifies customer_no', state: 'CONTRADICTED' as EvidenceState, confidence: 0.41, age: 'conflict 12m ago', source: 'archaeology.relationships' },
  { id: 'EVD-10AD', claim: 'Plan B survives a worker crash', state: 'SIMULATED' as EvidenceState, confidence: 0.88, age: 'game day #42', source: 'morpheus.shadow-world' },
]

function Sparkline({ data = trend, color = '#635bff' }: { data?: number[]; color?: string }) {
  const max = Math.max(...data)
  const min = Math.min(...data)
  const points = data.map((value, index) => `${(index / (data.length - 1)) * 100},${100 - ((value - min) / (max - min || 1)) * 78 - 10}`).join(' ')
  return (
    <svg className="sparkline" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} fill="none" stroke={color} strokeWidth="3" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function StatusPill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'green' | 'amber' | 'purple' | 'red' | 'blue' }) {
  return <span className={`status-pill ${tone}`}><span className="status-dot" />{children}</span>
}

function MetricCard({ item }: { item: (typeof metrics)[number] }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{item.label}<CircleHelp size={14} /></div>
      <div className="metric-value-row"><strong>{item.value}</strong><span className={`delta ${item.tone}`}>{item.delta}</span></div>
      <div className="metric-caption">{item.caption}</div>
      <div className="metric-chart"><Sparkline color={item.tone === 'green' ? '#22a06b' : item.tone === 'amber' ? '#b7791f' : item.tone === 'purple' ? '#8b5cf6' : '#635bff'} /></div>
    </div>
  )
}

function SectionHeader({ eyebrow, title, copy, action }: { eyebrow: string; title: string; copy?: string; action?: React.ReactNode }) {
  return <div className="section-heading"><div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2>{copy && <p>{copy}</p>}</div>{action}</div>
}

function Overview({ setView }: { setView: (view: ViewId) => void }) {
  return <>
    <div className="hero-row">
      <div><div className="eyebrow">ATLAS / MIGRATION-042</div><h1>Reality, under transformation.</h1><p className="hero-copy">A research console for preserving meaning, identity, time, provenance, and verifiable correctness when the execution machinery changes.</p><div className="hero-actions"><button className="primary" onClick={() => setView('migration')}><Play size={15} />Open runtime</button><button className="secondary" onClick={() => setView('genome')}><Boxes size={15} />Explore genome</button></div></div>
      <div className="hero-proof"><div className="proof-icon"><ShieldCheck size={22} /></div><div><strong>Certificate in progress</strong><span>8 of 10 required gates passed</span></div><div className="proof-ring"><span>80%</span></div></div>
    </div>
    <div className="metric-grid">{metrics.map(item => <MetricCard item={item} key={item.label} />)}</div>
    <div className="dashboard-grid">
      <div className="panel panel-wide"><SectionHeader eyebrow="Preservation / 30 days" title="Semantic preservation" copy="Equivalence after normalization, lifecycle mapping, and invariant checks." action={<button className="icon-button"><ExternalLink size={15} /></button>} /><div className="chart-head"><strong>99.94%</strong><span className="chart-positive"><ArrowUpRight size={14} /> 0.18%</span><span className="chart-muted">vs previous run</span></div><div className="big-chart"><div className="chart-gridlines"><span /><span /><span /><span /></div><Sparkline data={[52, 56, 51, 62, 66, 61, 70, 68, 76, 81, 78, 88, 91, 90, 96, 99]} color="#635bff" /><div className="chart-axis"><span>JUL 23</span><span>JUL 30</span><span>AUG 06</span><span>AUG 13</span><span>AUG 21</span></div></div></div>
      <div className="panel"><SectionHeader eyebrow="Execution" title="Runtime state" action={<StatusPill tone="green">Running</StatusPill>} /><div className="runtime-value"><strong>68.4%</strong><span>of source rows committed</span></div><div className="progress"><span style={{ width: '68.4%' }} /></div><div className="runtime-meta"><span>Throughput<strong>4,882 rows/s</strong></span><span>Workers<strong>3 / 4 healthy</strong></span><span>Next checkpoint<strong>in 18 sec</strong></span></div><button className="text-button" onClick={() => setView('migration')}>View execution details <ArrowUpRight size={14} /></button></div>
    </div>
    <div className="dashboard-grid lower-grid">
      <div className="panel"><SectionHeader eyebrow="Data Genome" title="What ATLAS knows" action={<button className="text-button" onClick={() => setView('genome')}>Open genome <ArrowUpRight size={14} /></button>} /><div className="knowledge-list"><div><span className="knowledge-mark observed" /><div><strong>Observed</strong><span>18,492 facts from source snapshots</span></div><b>68%</b></div><div><span className="knowledge-mark derived" /><div><strong>Derived</strong><span>2,183 relationships and invariants</span></div><b>17%</b></div><div><span className="knowledge-mark inferred" /><div><strong>Inferred</strong><span>421 mappings require review</span></div><b>9%</b></div><div><span className="knowledge-mark simulated" /><div><strong>Simulated</strong><span>Plan rehearsal and fault evidence</span></div><b>6%</b></div></div></div>
      <div className="panel"><SectionHeader eyebrow="Operator load" title="Attention required" action={<button className="icon-button"><ChevronDown size={15} /></button>} /><div className="attention-stack"><div><span className="attention-icon amber"><AlertTriangle size={15} /></span><div><strong>1 unresolved incident</strong><span>Duplicate identity in customers</span></div><button onClick={() => setView('incidents')}>Review</button></div><div><span className="attention-icon purple"><Sparkles size={15} /></span><div><strong>3 mapping questions</strong><span>Highest uncertainty reduction</span></div><button onClick={() => setView('evidence')}>Resolve</button></div><div><span className="attention-icon blue"><LockKeyhole size={15} /></span><div><strong>Cutover approval</strong><span>Awaiting operator sign-off</span></div><button onClick={() => setView('migration')}>Open</button></div></div></div>
    </div>
  </>
}

function GenomeView() {
  return <>
    <SectionHeader eyebrow="Data Genome / v1.4" title="A model beyond the schema" copy="ATLAS compares ecosystems by identity, relationships, temporal behavior, semantics, invariants, and uncertainty—not by table names alone." action={<button className="secondary"><GitBranch size={15} />Compare genomes</button>} />
    <div className="genome-summary-grid"><div className="genome-score-card"><span>Source → target distance</span><strong>0.083</strong><em>low semantic drift</em><div className="distance-bars"><span style={{ width: '13%' }} /><span style={{ width: '8%' }} /><span style={{ width: '11%' }} /><span style={{ width: '4%' }} /><span style={{ width: '17%' }} /></div></div>{[['Schema', '0.031'], ['Identity', '0.012'], ['Temporal', '0.084'], ['Semantic', '0.029'], ['Invariants', '0.000']].map(([label, value]) => <div className="mini-score" key={label}><span>{label}</span><strong>{value}</strong><Sparkline data={trend.slice(0, 8).map((v, i) => v - i * Number(value) * 30)} color={label === 'Temporal' ? '#b7791f' : '#635bff'} /></div>)}</div>
    <div className="panel table-panel"><div className="table-toolbar"><div className="search-field"><Search size={15} /><input placeholder="Filter entities, relationships, invariants" /></div><button className="secondary small"><History size={14} />Version history</button></div><div className="genome-table"><div className="table-row table-header"><span>Object</span><span>Type</span><span>Meaning / evidence</span><span>Epistemic state</span><span>Confidence</span></div>{genomeRows.map(row => <div className="table-row" key={row.name}><span className="object-name"><Database size={15} />{row.name}</span><span className="mono muted">{row.type}</span><span>{row.value}</span><span><StatusPill tone={row.status === 'Observed' ? 'blue' : row.status === 'Inferred' ? 'purple' : 'green'}>{row.status}</StatusPill></span><span className="confidence"><span className="confidence-bar"><i style={{ width: `${Number(row.confidence) * 100}%` }} /></span>{row.confidence}</span></div>)}</div></div>
  </>
}

function ArchaeologyView() {
  return <>
    <SectionHeader eyebrow="System archaeology" title="Understand the unknown system" copy="Findings are ranked by evidence and uncertainty. Inference never silently becomes truth." action={<button className="primary"><Search size={15} />Run archaeology</button>} />
    <div className="archaeology-banner"><div className="banner-icon"><Sparkles size={20} /></div><div><strong>Archaeology pass completed</strong><span>12 tables · 184 columns · 29 candidate relationships · 7 candidate business rules</span></div><button className="secondary small">Export findings</button></div>
    <div className="archaeology-grid"><div className="panel"><SectionHeader eyebrow="Confidence map" title="Findings by epistemic state" /><div className="donut-wrap"><div className="donut"><div><strong>421</strong><span>findings</span></div></div><div className="legend"><div><i className="blue-dot" /><span>Known / observed</span><b>68%</b></div><div><i className="purple-dot" /><span>Derived</span><b>17%</b></div><div><i className="amber-dot" /><span>Inferred</span><b>9%</b></div><div><i className="gray-dot" /><span>Unknown</span><b>6%</b></div></div></div></div><div className="panel"><SectionHeader eyebrow="Highest uncertainty" title="Human questions" /><div className="question-list"><div><span className="question-number">01</span><div><strong>Does customer_ref remain stable across merges?</strong><span>Expected uncertainty reduction · 23%</span></div><button>Answer</button></div><div><span className="question-number">02</span><div><strong>Are source timestamps UTC or local time?</strong><span>Impacts 4 mappings and 2 invariants</span></div><button>Answer</button></div><div><span className="question-number">03</span><div><strong>Is acct_bal a ledger balance or available balance?</strong><span>Impacts semantic equivalence</span></div><button>Answer</button></div></div></div></div>
    <div className="panel table-panel"><div className="table-toolbar"><div><div className="eyebrow">Evidence-backed findings</div><h3>Archaeology report</h3></div><div className="segmented"><button className="active">All</button><button>Relationships</button><button>Business rules</button><button>PII</button></div></div><div className="genome-table"><div className="table-row table-header"><span>Finding</span><span>Category</span><span>Evidence</span><span>Status</span><span>Confidence</span></div>{[['customer_ref → customer_no', 'relationship', 'join coverage 99.8% · overlap 1,992/2,003', 'INFERRED', '0.91'], ['status → lifecycle field', 'business rule', '6 observed states · 2 contradictions', 'UNDER REVIEW', '0.55'], ['phone', 'PII candidate', 'field name + format distribution', 'LIKELY', '0.85'], ['closed_at', 'temporal field', 'date parse 99.7% · non-null 84.2%', 'LIKELY', '0.82']].map(([finding, category, ev, status, confidence]) => <div className="table-row" key={finding}><span className="object-name"><Search size={15} />{finding}</span><span className="mono muted">{category}</span><span>{ev}</span><span><StatusPill tone={status === 'UNDER REVIEW' ? 'amber' : 'purple'}>{status}</StatusPill></span><span className="confidence"><span className="confidence-bar"><i style={{ width: `${Number(confidence) * 100}%` }} /></span>{confidence}</span></div>)}</div></div>
  </>
}

function MigrationView() {
  return <>
    <SectionHeader eyebrow="Migration runtime / MIGRATION-042" title="A proof-carrying execution" copy="The plan is running in shadow-aware mode. Every batch carries provenance, checkpoints, policy, and validation evidence." action={<button className="secondary"><TerminalSquare size={15} />Open CLI</button>} />
    <div className="migration-topline"><div className="run-state"><span className="pulse" /><div><strong>RUNNING</strong><span>Started Aug 21, 10:14:08 UTC</span></div></div><div className="migration-actions"><button className="secondary small"><RotateCcw size={14} />Pause</button><button className="primary small"><ShieldCheck size={14} />Review cutover</button></div></div>
    <div className="pipeline panel"><div className="pipeline-step done"><span><Check size={15} /></span><div><strong>Profile</strong><small>184 fields</small></div></div><div className="pipeline-line done" /><div className="pipeline-step done"><span><Check size={15} /></span><div><strong>Compile IR</strong><small>plan-v17</small></div></div><div className="pipeline-line done" /><div className="pipeline-step active"><span><Activity size={15} /></span><div><strong>Execute</strong><small>68.4% committed</small></div></div><div className="pipeline-line" /><div className="pipeline-step"><span><FileCheck2 size={15} /></span><div><strong>Reconcile</strong><small>waiting</small></div></div><div className="pipeline-line" /><div className="pipeline-step"><span><ShieldCheck size={15} /></span><div><strong>Certify</strong><small>8 / 10 gates</small></div></div></div>
    <div className="dashboard-grid"><div className="panel panel-wide"><SectionHeader eyebrow="Execution plan" title="Plan B · resilient verification" action={<button className="text-button">Plan diff <ArrowUpRight size={14} /></button>} /><div className="plan-grid"><div><span className="plan-label">Strategy</span><strong>High recovery granularity</strong><small>10-row checkpoints · semantic hash per batch</small></div><div><span className="plan-label">Risk model</span><strong>0.176 · Low</strong><small>PII logging denied by policy</small></div><div><span className="plan-label">Shadow result</span><strong>0 data-loss scenarios</strong><small>5 faults · 4 auto-remediated</small></div></div><div className="batch-chart"><div className="batch-labels"><span>customers</span><span>accounts</span><span>transactions</span></div><div className="batch-bars"><div><span style={{ width: '100%' }} /><em>100%</em></div><div><span style={{ width: '78%' }} /><em>78%</em></div><div><span style={{ width: '54%' }} /><em>54%</em></div></div></div></div><div className="panel"><SectionHeader eyebrow="Certificate" title="Gate progress" /><div className="gate-list"><div><span className="gate-pass"><Check size={13} /></span><span>Schema compatibility</span><b>PASS</b></div><div><span className="gate-pass"><Check size={13} /></span><span>Mapping validation</span><b>PASS</b></div><div><span className="gate-pass"><Check size={13} /></span><span>Audit completeness</span><b>PASS</b></div><div><span className="gate-warn"><Clock3 size={13} /></span><span>Semantic reconciliation</span><b>WAIT</b></div><div><span className="gate-warn"><LockKeyhole size={13} /></span><span>Operator approval</span><b>WAIT</b></div></div><button className="text-button">Open certificate <ArrowUpRight size={14} /></button></div></div>
  </>
}

function EvidenceView() {
  return <>
    <SectionHeader eyebrow="Proof / evidence ledger" title="What do we know, and why?" copy="Every claim has a source, epistemic state, confidence, and knowledge age. Contradiction is a first-class result." action={<button className="secondary"><History size={15} />Knowledge time</button>} />
    <div className="evidence-banner"><div><strong>Evidence freshness</strong><span>Confidence decays when observations are not re-verified. Current ledger is 94% fresh.</span></div><div className="freshness-bar"><span style={{ width: '94%' }} /></div></div>
    <div className="panel table-panel"><div className="table-toolbar"><div className="search-field"><Search size={15} /><input placeholder="Search claims, sources, or evidence IDs" /></div><button className="secondary small"><Code2 size={14} />Export JSONL</button></div><div className="genome-table"><div className="table-row table-header"><span>Claim</span><span>State</span><span>Confidence</span><span>Source</span><span>Freshness</span></div>{evidence.map(item => <div className="table-row evidence-row" key={item.id}><span><strong>{item.claim}</strong><small>{item.id}</small></span><span><StatusPill tone={item.state === 'CONTRADICTED' ? 'red' : item.state === 'SIMULATED' ? 'purple' : item.state === 'INFERRED' ? 'amber' : 'green'}>{item.state}</StatusPill></span><span className="confidence"><span className="confidence-bar"><i style={{ width: `${item.confidence * 100}%` }} /></span>{item.confidence.toFixed(2)}</span><span className="mono muted">{item.source}</span><span className="muted">{item.age}</span></div>)}</div></div>
    <div className="dashboard-grid lower-grid"><div className="panel"><SectionHeader eyebrow="Assumption ledger" title="3 assumptions need review" /><div className="assumption-list"><div><span className="assumption-state amber" /><div><strong>All source timestamps are UTC</strong><span>0.94 confidence · impacts 6 results</span></div><button>Inspect</button></div><div><span className="assumption-state red" /><div><strong>Duplicate customer IDs are impossible</strong><span>Invalidated 12 min ago · 4 dependents</span></div><button>Trace</button></div><div><span className="assumption-state green" /><div><strong>Currency code is ISO-4217</strong><span>1.00 confidence · verified from reference</span></div><button>Open</button></div></div></div><div className="panel conflict-card"><div className="conflict-icon"><AlertTriangle size={16} /></div><div><div className="eyebrow">Evidence conflict</div><strong>customer_ref identity continuity</strong><p>Two sources disagree about the merge boundary. ATLAS has held the mapping at 0.41 confidence instead of choosing.</p><button className="text-button">Open conflict graph <ArrowUpRight size={14} /></button></div></div></div>
  </>
}

function IncidentsView() {
  return <>
    <SectionHeader eyebrow="Operations / incident intelligence" title="Make failure explainable" copy="Incidents preserve symptoms, evidence, blast radius, hypotheses, and recovery state. Resolved incidents become regression fixtures." action={<button className="primary"><Zap size={15} />Inject fault</button>} />
    <div className="incident-overview"><div className="incident-stat"><span>Open incidents</span><strong>1</strong><em className="amber-text">needs attention</em></div><div className="incident-stat"><span>Mean time to localize</span><strong>4m 12s</strong><em className="green-text">−18% vs last run</em></div><div className="incident-stat"><span>Integrity half-life</span><strong>2h 14m</strong><em>synthetic game day</em></div><div className="incident-stat"><span>Recovery rate</span><strong>4 / 5</strong><em className="purple-text">1 human review</em></div></div>
    <div className="panel incident-panel"><div className="incident-list">{incidents.map((incident, index) => <div className={`incident-item ${index === 0 ? 'selected' : ''}`} key={incident.id}><div className={`severity-bar ${incident.severity.toLowerCase()}`} /><div className="incident-main"><div className="incident-title"><strong>{incident.title}</strong><StatusPill tone={incident.status === 'Resolved' ? 'green' : incident.status === 'Open' ? 'amber' : 'blue'}>{incident.status}</StatusPill></div><div className="incident-meta"><span>{incident.id}</span><span>{incident.source}</span><span>{incident.time}</span></div><p>{incident.detail}</p></div><ArrowUpRight size={16} className="incident-arrow" /></div>)}</div><div className="incident-detail"><div className="eyebrow">INC-042 / selected incident</div><h3>Duplicate customer identity</h3><div className="detail-tags"><StatusPill tone="amber">Medium severity</StatusPill><span>Inherited integrity debt</span><span>blast radius · 1 entity</span></div><div className="timeline"><div><span className="timeline-dot blue" /><div><strong>Detected</strong><small>12:42:08 UTC · key coverage check</small></div></div><div><span className="timeline-dot amber" /><div><strong>Localized</strong><small>12:42:11 UTC · legacy_customers / customer_no</small></div></div><div><span className="timeline-dot purple" /><div><strong>Hypothesis</strong><small>duplicate source record, not target write error</small></div></div><div><span className="timeline-dot gray" /><div><strong>Next action</strong><small>human review before certification</small></div></div></div><button className="secondary full">Open crash dump <ExternalLink size={14} /></button></div></div>
  </>
}

function ResearchView() {
  return <>
    <SectionHeader eyebrow="Research lab / reproducibility" title="Turn failure into knowledge" copy="Experiments are versioned by seed, dataset hash, engine version, hardware, and measurement method." action={<button className="primary"><Play size={15} />Run experiment</button>} />
    <div className="research-hero"><div className="research-icon"><LineChart size={20} /></div><div><strong>Migration correctness under distributed failure</strong><span>Research question · active experiment family</span></div><StatusPill tone="purple">12 runs</StatusPill><button className="text-button">Open lab notebook <ArrowUpRight size={14} /></button></div>
    <div className="research-grid"><div className="panel"><SectionHeader eyebrow="Reconciliation benchmark" title="Merkle vs naive" /><div className="benchmark-bars"><div><span>Naive comparison</span><div><i style={{ width: '82%', background: '#c5c9d3' }} /></div><b>8.42 s</b></div><div><span>Partition fingerprints</span><div><i style={{ width: '42%', background: '#635bff' }} /></div><b>4.10 s</b></div><div><span>Semantic Merkle</span><div><i style={{ width: '29%', background: '#22a06b' }} /></div><b>2.87 s</b></div></div><p className="panel-note">Synthetic reference benchmark · 100,000 rows · seed 42 · local machine. Not a production throughput claim.</p></div><div className="panel"><SectionHeader eyebrow="Forecast calibration" title="Predicted vs observed" /><div className="calibration-number"><strong>0.87</strong><span>mean absolute calibration score</span></div><div className="calibration-bars"><span style={{ height: '40%' }} /><span style={{ height: '62%' }} /><span style={{ height: '54%' }} /><span style={{ height: '78%' }} /><span style={{ height: '68%' }} /><span style={{ height: '91%' }} /><span style={{ height: '74%' }} /><span style={{ height: '88%' }} /></div><p className="panel-note">8 completed synthetic runs · confidence interval recorded in artifact.</p></div></div>
    <div className="panel"><SectionHeader eyebrow="Experiment catalog" title="Research artifacts" /><div className="experiment-table"><div className="table-row table-header"><span>Experiment</span><span>Dataset</span><span>Result</span><span>Reproducibility</span><span /></div>{[['worker-scaling', 'bank-v1 / 100K', '4.1× at 4 workers', 'Reproducible'], ['adaptive-verification', 'bank-v1 / 25K', '0.94 confidence / CPU-s', 'Reproducible'], ['CDC recovery', 'fault-matrix / #42', '4 / 5 auto-recovered', 'Reproducible'], ['semantic equivalence', 'golden-pairs / v2', '98.2% F1', 'Needs labels']].map(row => <div className="table-row" key={row[0]}><span className="object-name"><Activity size={15} />{row[0]}</span><span className="mono muted">{row[1]}</span><span>{row[2]}</span><span><StatusPill tone={row[3] === 'Reproducible' ? 'green' : 'amber'}>{row[3]}</StatusPill></span><span><ArrowUpRight size={15} /></span></div>)}</div></div>
  </>
}

function App() {
  const [active, setActive] = useState<ViewId>('overview')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [connected, setConnected] = useState(false)
  const activeLabel = useMemo(() => nav.find(item => item.id === active)?.label ?? 'Overview', [active])
  const renderView = () => {
    if (active === 'overview') return <Overview setView={setActive} />
    if (active === 'genome') return <GenomeView />
    if (active === 'archaeology') return <ArchaeologyView />
    if (active === 'migration') return <MigrationView />
    if (active === 'evidence') return <EvidenceView />
    if (active === 'incidents') return <IncidentsView />
    return <ResearchView />
  }
  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
      <div className="brand"><div className="brand-mark">A</div><div><strong>ATLAS</strong><span>reality runtime</span></div><button className="mobile-close" onClick={() => setSidebarOpen(false)}><ChevronDown size={16} /></button></div>
      <div className="workspace-switch"><div className="workspace-avatar">M</div><div><strong>Migration 042</strong><span>Research workspace</span></div><ChevronDown size={15} /></div>
      {['Workspace', 'Proof', 'Research'].map(group => <div className="nav-group" key={group}><div className="nav-group-label">{group}</div>{nav.filter(item => item.group === group).map(item => { const Icon = item.icon; return <button key={item.id} className={`nav-item ${active === item.id ? 'active' : ''}`} onClick={() => { setActive(item.id); setSidebarOpen(false) }}><Icon size={17} /><span>{item.label}</span>{item.id === 'incidents' && <em>1</em>}</button> })}</div>)}
      <div className="sidebar-bottom"><div className="connection-card"><div className={`connection-dot ${connected ? 'connected' : ''}`} /><div><strong>{connected ? 'Control plane connected' : 'Demo data mode'}</strong><span>{connected ? 'localhost:8080' : 'synthetic / seed 42'}</span></div><button onClick={() => setConnected(value => !value)}><RotateCcw size={14} /></button></div><button className="nav-item"><CircleHelp size={17} /><span>Documentation</span><ExternalLink size={13} /></button><div className="user-row"><div className="user-avatar">SA</div><div><strong>Satvik Anand</strong><span>Operator</span></div><ChevronDown size={15} /></div></div>
    </aside>
    <main className="main-shell">
      <header className="topbar"><button className="mobile-menu" onClick={() => setSidebarOpen(true)}><Menu size={19} /></button><div className="breadcrumbs"><span>ATLAS</span><span>/</span><strong>{activeLabel}</strong></div><div className="topbar-actions"><button className="topbar-icon"><Search size={17} /></button><button className="topbar-icon"><BellDot /></button><div className="topbar-divider" /><button className="environment-button"><span className="live-dot" />{connected ? 'Live control plane' : 'Demo data'}<ChevronDown size={14} /></button></div></header>
      <div className="content"><div className="announcement"><Sparkles size={15} /><span>ATLAS is an experimental runtime for preserving data-system reality under transformation and failure.</span><button>Read the research note <ArrowUpRight size={13} /></button></div>{renderView()}</div>
    </main>
  </div>
}

function BellDot() { return <span className="bell-dot"><Activity size={16} /></span> }

export default App

createRoot(document.getElementById('root')!).render(<App />)
