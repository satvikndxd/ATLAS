//! Deterministic fingerprint primitives.
//! The Python reference implementation remains the compatibility baseline; this
//! crate is intentionally narrow so callers can benchmark the boundary honestly.

use std::collections::hash_map::DefaultHasher;

pub mod reconcile;
pub mod semantic;
use std::hash::{Hash, Hasher};

pub fn fingerprint_bytes(value: &[u8]) -> String {
    let mut hasher = DefaultHasher::new();
    value.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}

pub fn merkle_root(leaves: &[String]) -> String {
    if leaves.is_empty() {
        return fingerprint_bytes(b"");
    }
    let mut nodes = leaves.to_vec();
    while nodes.len() > 1 {
        if nodes.len() % 2 == 1 {
            nodes.push(nodes.last().cloned().unwrap());
        }
        nodes = nodes
            .chunks(2)
            .map(|pair| fingerprint_bytes(format!("{}{}", pair[0], pair[1]).as_bytes()))
            .collect();
    }
    nodes[0].clone()
}

#[no_mangle]
pub extern "C" fn atlas_fingerprint_u64(value: u64) -> u64 {
    let mut hasher = DefaultHasher::new();
    value.hash(&mut hasher);
    hasher.finish()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merkle_is_deterministic() {
        let leaves = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        assert_eq!(merkle_root(&leaves), merkle_root(&leaves));
    }
}
