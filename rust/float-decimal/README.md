# Rust float-decimal · R0

This is an independently authored experimental Rust decimal parser, **not a new Prolog compiler** and not linked to GNU Prolog production. See docs/RUST_PORT_PLAN.md for the staged migration.

It accepts ASCII decimal float tokens with a decimal point and optional scientific exponent, allows an optional leading sign for the standalone ABI, rejects non-finite or malformed tokens and yields the exact 64-bit IEEE 754 representation of each finite value, including negative zero. The standard Rust floating parser is independent of the process-global C numeric locale.

Its export is gprolog_decimal_parse_bits(pointer, length, output_u64_pointer). The status code is 1 for a finite conversion, 0 for a rejected token, and -1 for an invalid pointer/size. Validity of non-null C pointers is the caller's responsibility; this library cannot prove arbitrary foreign memory is readable.

R0 tests include a 44-value exact rational oracle, a dynamically linked C foreign-function witness, German/C numeric-locale comparison and real ELF64/i686 ELF32 builds.

License: GNU Prolog-compatible dual LGPL v3-or-later OR GPL v2-or-later. The root COPYING file governs inherited GNU Prolog material. No performance or external-replication claim is implied.
