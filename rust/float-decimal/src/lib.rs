// GNU Prolog Rust experiment R0. LGPL-3.0-or-later OR GPL-2.0-or-later.
// Independently implemented; not linked to production GNU Prolog.
use std::{slice, str};
pub const MAX_TOKEN_BYTES: usize = 1_048_576;

// Match the Prolog decimal FLOAT token shape rather than generic f64
// spellings. Unary sign is accepted for standalone validation.
fn is_decimal_token(token: &[u8]) -> bool {
    let mut pos = 0;
    if matches!(token.first(), Some(b'+' | b'-')) { pos += 1; }
    let int_start = pos;
    while pos < token.len() && token[pos].is_ascii_digit() { pos += 1; }
    if pos == int_start || token.get(pos) != Some(&b'.') { return false; }
    pos += 1;
    let fraction_start = pos;
    while pos < token.len() && token[pos].is_ascii_digit() { pos += 1; }
    if pos == fraction_start { return false; }
    if matches!(token.get(pos), Some(b'e' | b'E')) {
        pos += 1;
        if matches!(token.get(pos), Some(b'+' | b'-')) { pos += 1; }
        let exponent_start = pos;
        while pos < token.len() && token[pos].is_ascii_digit() { pos += 1; }
        if pos == exponent_start { return false; }
    }
    pos == token.len()
}

/// Returns exact IEEE754 binary64 bits for an accepted finite token.
/// No C locale lookup, mutation or global state access.
pub fn finite_decimal_bits(token: &str) -> Option<u64> {
    if token.len() > MAX_TOKEN_BYTES || !is_decimal_token(token.as_bytes()) {
        return None;
    }
    let value: f64 = token.parse().ok()?;
    value.is_finite().then_some(value.to_bits())
}

/// C ABI: 1 = finite result; 0 = invalid/overflow; -1 = bad pointer/length.
///
/// # Safety
/// Caller guarantees a readable len-byte memory span and properly aligned
/// writable u64 output. Bad non-null C pointers cannot be checked.
#[no_mangle]
pub unsafe extern "C" fn gprolog_decimal_parse_bits(
    bytes: *const u8, len: usize, out_bits: *mut u64
) -> i32 {
    if bytes.is_null() || out_bits.is_null() || len == 0 || len > MAX_TOKEN_BYTES {
        return -1;
    }
    // SAFETY: C caller promises input pointer validity.
    let source = unsafe { slice::from_raw_parts(bytes, len) };
    let Ok(source) = str::from_utf8(source) else { return 0; };
    let Some(value) = finite_decimal_bits(source) else { return 0; };
    // SAFETY: C caller promises output pointer validity.
    unsafe { out_bits.write(value); }
    1
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_known_values() {
        for (literal, expected) in [
            ("0.1", 0x3fb999999999999a),
            ("1.25", 0x3ff4000000000000),
            ("-0.0", 0x8000000000000000),
            ("5.0e-324", 0x0000000000000001),
            ("-5.0e-324", 0x8000000000000001),
            ("1.7976931348623157e308", 0x7fefffffffffffff),
            ("1.0e-9999", 0),
            ("-1.0e-9999", 0x8000000000000000),
        ] {
            assert_eq!(finite_decimal_bits(literal), Some(expected), "{literal}");
        }
    }
    #[test]
    fn reject_unrecognized_formats_and_infinity() {
        for token in [
            "", "1", "1.", ".5", "1e2", "1.0e", "1.0e+", " 1.0",
            "1.0 ", "1,25", "1.0junk", "NaN", "nan", "Inf",
            "Infinity", "-inf", "0x1.0p0", "1.0e309", "-1.0e309",
            "1.7976931348623159e308", "1.0\n", "1.0\0",
        ] {
            assert_eq!(finite_decimal_bits(token), None, "{token:?}");
        }
    }
    #[test]
    fn ffi_values_and_bad_pointer_guards() {
        let token = b"-0.0";
        let mut output = 0_u64;
        assert_eq!(unsafe { gprolog_decimal_parse_bits(token.as_ptr(),token.len(), &mut output) }, 1);
        assert_eq!(output, 0x8000000000000000);
        assert_eq!(unsafe { gprolog_decimal_parse_bits(std::ptr::null(),0,&mut output) },-1);
        assert_eq!(unsafe { gprolog_decimal_parse_bits(token.as_ptr(), token.len(), std::ptr::null_mut()) },-1);
        assert_eq!(unsafe { gprolog_decimal_parse_bits(token.as_ptr(), MAX_TOKEN_BYTES+1, &mut output) },-1);
    }
    #[test]
    fn syntax_is_explicit_not_just_rust_float_parser() {
        assert!(is_decimal_token(b"1.25E-99"));
        assert!(is_decimal_token(b"+1.0e3"));
        assert!(!is_decimal_token(b"1e3"));
        assert!(!is_decimal_token(b"1.0e++1"));
    }
}
