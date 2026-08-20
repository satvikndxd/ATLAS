//! Hierarchical reconciliation kernel for deterministic partition localization.
use std::collections::BTreeMap;

use super::{fingerprint_bytes, merkle_root};
use super::semantic::semantic_fingerprint;

pub fn partition_roots(records: &[BTreeMap<String, String>], partitions: usize) -> Vec<String> {
    let count = partitions.max(1);
    let mut buckets = vec![Vec::new(); count];
    for record in records {
        let key = record.get("id").map(String::as_str).unwrap_or("");
        let bucket = u64::from_str_radix(&fingerprint_bytes(key.as_bytes())[..8], 16).unwrap_or(0) as usize % count;
        buckets[bucket].push(semantic_fingerprint(record));
    }
    buckets.iter().map(|leaves| merkle_root(leaves)).collect()
}

pub fn differing_partitions(left: &[BTreeMap<String, String>], right: &[BTreeMap<String, String>], partitions: usize) -> Vec<usize> {
    let left_roots = partition_roots(left, partitions);
    let right_roots = partition_roots(right, partitions);
    left_roots.iter().zip(right_roots.iter()).enumerate().filter_map(|(index, (left_root, right_root))| (left_root != right_root).then_some(index)).collect()
}
