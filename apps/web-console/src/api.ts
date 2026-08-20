export type MigrationState = 'DRAFT' | 'VALIDATING' | 'PLANNED' | 'APPROVAL_REQUIRED' | 'APPROVED' | 'RUNNING' | 'PAUSED' | 'RECOVERING' | 'RECONCILING' | 'VERIFIED' | 'CUTOVER_READY' | 'CUTOVER' | 'COMPLETED' | 'FAILED' | 'ABORTED' | 'ROLLED_BACK'

type MigrationWire = {
  schema_version: '1.0'
  migration_id: string
  state: MigrationState
  source: string
  target: string
  plan_version: string
  progress: number
  created_at: string
  updated_at: string
}

type JobWire = {
  schema_version: '1.0'
  job_id: string
  migration_id: string
  state: string
  table: string | null
  partition: string | null
  worker_id: string | null
  attempt: number
  progress: number
  updated_at: string
}

type WorkerWire = {
  schema_version: '1.0'
  worker_id: string
  status: string
  last_heartbeat: string
}

export type AtlasMigration = {
  schemaVersion: '1.0'
  migrationId: string
  state: MigrationState
  source: string
  target: string
  planVersion: string
  progress: number
  createdAt: string
  updatedAt: string
}

export type AtlasJob = {
  schemaVersion: '1.0'
  jobId: string
  migrationId: string
  state: string
  table: string | null
  partition: string | null
  workerId: string | null
  attempt: number
  progress: number
  updatedAt: string
}

export type AtlasWorker = {
  schemaVersion: '1.0'
  workerId: string
  status: string
  lastHeartbeat: string
}

export type LiveSnapshot = {
  migrations: AtlasMigration[]
  jobs: AtlasJob[]
  workers: AtlasWorker[]
  fetchedAt: string
}

const configuredBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '')
export const apiBaseUrl = configuredBase || 'http://localhost:8080'
const apiKey = (import.meta.env.VITE_ATLAS_API_KEY as string | undefined)?.trim()

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers: { Accept: 'application/json', ...(apiKey ? { 'X-ATLAS-API-Key': apiKey } : {}), ...(init?.headers ?? {}) } })
  if (!response.ok) throw new Error(`ATLAS API ${response.status}: ${await response.text()}`)
  return response.json() as Promise<T>
}

function normalizeMigration(item: MigrationWire): AtlasMigration {
  return { schemaVersion: item.schema_version, migrationId: item.migration_id, state: item.state, source: item.source, target: item.target, planVersion: item.plan_version, progress: item.progress, createdAt: item.created_at, updatedAt: item.updated_at }
}

function normalizeJob(item: JobWire): AtlasJob {
  return { schemaVersion: item.schema_version, jobId: item.job_id, migrationId: item.migration_id, state: item.state, table: item.table, partition: item.partition, workerId: item.worker_id, attempt: item.attempt, progress: item.progress, updatedAt: item.updated_at }
}

function normalizeWorker(item: WorkerWire): AtlasWorker {
  return { schemaVersion: item.schema_version, workerId: item.worker_id, status: item.status, lastHeartbeat: item.last_heartbeat }
}

export async function fetchLiveSnapshot(): Promise<LiveSnapshot> {
  const [migrations, jobs, workers] = await Promise.all([
    request<MigrationWire[]>('/api/v1/migrations'),
    request<JobWire[]>('/api/v1/jobs'),
    request<WorkerWire[]>('/api/v1/workers'),
  ])
  return { migrations: migrations.map(normalizeMigration), jobs: jobs.map(normalizeJob), workers: workers.map(normalizeWorker), fetchedAt: new Date().toISOString() }
}
