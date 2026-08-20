# Public Data Boundary

ATLAS includes a `RawSnapshot` and `SnapshotStore` contract for public-data experiments. A snapshot records provider, endpoint, request parameters, retrieval time, effective time, schema version, normalization version, response hash, and payload. The store supports replay without a live provider call.

Official provider integrations remain extension work in this repository. The CLI `public-demo` intentionally reports the configured provider boundary for SEC EDGAR, GLEIF, ECB, FRED/ALFRED, Companies House, and optional OpenCorporates without claiming that any live request was made. When a provider is implemented, request policy, authentication, quotas, terms, User-Agent, cache behavior, and immutable snapshot artifacts must be tested and documented.
