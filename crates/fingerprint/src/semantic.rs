//! Semantic fingerprints intentionally normalize representation-level differences.
use std::collections::BTreeMap;

use super::{fingerprint_bytes, merkle_root};

pub fn normalize_number(value: &str) -> String {
    let parsed = value.trim().parse::<f64>();
    match parsed {
        Ok(number) if number.fract() == 0.0 => format!("{:.0}", number),
        Ok(number) => format!("{number:.12}".trim_end_matches('0').trim_end_matches('.').to_string()),
        Err(_) => value.trim().to_ascii_lowercase(),
    }
}

pub fn semantic_fingerprint(fields: &BTreeMap<String, String>) -> String {
    let normalized = fields
        .iter()
        .map(|(key, value)| format!("{}={}", key.to_ascii_lowercase(), normalize_number(value)))
        .collect::<Vec<_>>()
        .join("|");
    fingerprint_bytes(normalized.as_bytes())
}

pub fn semantic_merkle_root(records: &[BTreeMap<String, String>]) -> String {
    let leaves = records.iter().map(semantic_fingerprint).collect::<Vec<_>>();
    merkle_root(&leaves)
}
