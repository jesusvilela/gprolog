/* Experimental GNU Prolog R0 parser ABI, not used in production.
 * LGPL-3.0-or-later OR GPL-2.0-or-later, as in GNU Prolog COPYING.
 */
#ifndef GPROLOG_DECIMAL_RUST_H
#define GPROLOG_DECIMAL_RUST_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* 1 finite bits written, 0 rejected token, -1 invalid pointer/size.
 * Caller must pass valid memory; len <= 1048576.
 */
int32_t gprolog_decimal_parse_bits(const unsigned char *bytes,
                                   size_t len, uint64_t *out_bits);
#ifdef __cplusplus
}
#endif
#endif
