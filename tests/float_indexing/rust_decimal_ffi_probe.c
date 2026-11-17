/* Test-only C host for the independently authored Rust parser.
 * Unlike production GNU Prolog, this process deliberately selects locale.
 * Its libc sscanf serves as a negative locale-dependence control.
 */
#include <dlfcn.h>
#include <locale.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../rust/float-decimal/include/gprolog_decimal_rust.h"

typedef int32_t (*parse_fn)(const unsigned char *, size_t, uint64_t *);

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: ffi_host LIBRARY LOCALE DECIMAL\n");
        return 2;
    }
    if (!setlocale(LC_ALL, argv[2])) {
        fprintf(stderr, "missing locale: %s\n", argv[2]);
        return 3;
    }
    void *library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        return 4;
    }
    void *symbol = dlsym(library, "gprolog_decimal_parse_bits");
    if (!symbol) {
        fprintf(stderr, "missing Rust C ABI symbol\n");
        dlclose(library);
        return 5;
    }
    parse_fn parse = NULL;
    /* POSIX host: function pointer and dlsym pointer have same width. */
    if (sizeof(parse) != sizeof(symbol)) { dlclose(library); return 6; }
    memcpy(&parse, &symbol, sizeof(parse));

    const char *token = argv[3];
    uint64_t rust_bits = UINT64_C(0);
    int32_t status = parse((const unsigned char *)token, strlen(token), &rust_bits);

    double libc_value = 0.0;
    int libc_scanned = sscanf(token, "%lf", &libc_value);
    uint64_t libc_bits = UINT64_C(0);
    if (sizeof(libc_bits) != sizeof(libc_value)) { dlclose(library); return 7; }
    memcpy(&libc_bits, &libc_value, sizeof(libc_bits));

    printf("STATUS=%d\nRUST=%016llx\nC=%016llx\nSCANNED=%d\nLC=%s\nPOINT=%s\n",
           status, (unsigned long long)rust_bits,
           (unsigned long long)libc_bits, libc_scanned,
           setlocale(LC_NUMERIC, NULL), localeconv()->decimal_point);
    dlclose(library);
    return 0;
}
