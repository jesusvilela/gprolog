# GNU Prolog, still becoming

> A native Prolog compiler with an old soul, a real WAM, and unfinished business.

This fork starts from [GNU Prolog](https://www.gprolog.org/), Daniel Diaz's
native-code Prolog system, and asks a precise question:

**What should a serious Prolog compiler feel like at the edge of 2027?**

Not a rewrite for the pleasure of rewriting. Not a compatibility costume.
We keep the machinery that already matters—native standalone executables,
fast startup, a compact runtime, ISO-oriented semantics, finite-domain
constraints, and the Prolog/C boundary—then bring in the best *ideas* proven
across the wider logic-programming ecosystem.

The direction is evolutionary:

```text
GNU Prolog's native spine
        + better compilation hooks
        + stronger indexing
        + explicit contracts and analysis
        + incremental development
        + selective tabling
        = a modern compiler that remains recognizably Prolog
```

No benchmark theater. No borrowed feature names without semantics. Every step
must arrive as a small vertical slice with executable evidence.

## What already lives here

GNU Prolog provides:

- native-code compilation to standalone executables;
- an interactive byte-code interpreter and debugger;
- a low-level WAM debugger;
- ISO Prolog coverage for arithmetic, streams, dynamic code, and exceptions;
- clause indexing, DCGs, sockets, operating-system integration, and global
  variables;
- more than 300 built-in predicates;
- a bidirectional C interface;
- an integrated finite-domain constraint solver with reification, symbolic and
  arithmetic constraints, and multiple enumeration heuristics.

The compiler accepts Prolog, WAM, C, and object inputs. It removes many unused
built-ins while linking standalone programs, keeping the result closer to a
compiled language artifact than a bundled interactive image.

## The first new compiler seam: goal expansion

This branch introduces SWI-inspired `goal_expansion/2` hooks and the explicit
`expand_goal/2` predicate, adapted to GNU Prolog rather than imitating another
system wholesale.

```prolog
goal_expansion(square(X, Y), Y is X * X).

area_of_square(Side, Area) :-
    square(Side, Area).
```

During compilation, the body of `area_of_square/2` is specialized to native
arithmetic. Expansion traverses control constructs such as conjunction,
disjunction, conditionals, negation, `call/1`, `once/1`, and `catch/3`, while
ordinary data arguments remain data.

The safety boundary is deliberate:

- the first successful hook wins;
- source-goal variables may not be bound or aliased by a hook;
- finite rewrite cycles are detected;
- hook definitions are protected from self-expansion;
- consulted code inherits the active expansion hooks;
- this is a documented, tested subset—not a claim of full SWI compatibility.

See [the compiler evolution notes](docs/COMPILER_EVOLUTION.md) for the exact
semantics, exclusions, and evidence.

## Smallest successful path

After installing GNU Prolog and making sure its binaries are on `PATH`:

```console
$ gprolog
| ?- write('hello from Prolog'), nl.
hello from Prolog
yes
```

Compile a program:

```console
$ gplc hello.pl
$ ./hello
```

`gplc --help` shows the accepted inputs and compiler options. The full build
instructions live in [INSTALL](INSTALL); Windows-specific compiler notes are in
[src/WINDOWS](src/WINDOWS).

## Build from source

On a Unix-like system, the canonical in-place build is:

```console
$ cd src
$ ./configure --with-install-dir=in-place
$ make
$ make install
```

Validate the compiler and the new expansion seam:

```console
$ python3 ../tests/goal_expansion/run.py --bin-dir "$PWD/../bin"
$ make check
$ make check-e
$ make check-i
```

Those commands cover native, emulated, and interpreted compiler modes. A green
run establishes the behavior exercised by those suites; it is not, by itself,
a universal performance or compatibility claim.

On Windows, read [src/WINDOWS](src/WINDOWS) before building. The MSVC and MSYS
ports have different toolchain requirements, and a source path containing
spaces can break the MSYS build.

## Where this compiler goes next

The research map is intentionally plural:

- **SWI-Prolog and YAP:** deeper, observable indexing without disturbing answer
  order or side effects;
- **Ciao:** assertions, modes, and analysis that can become compiler knowledge;
- **WAMpy and modern incremental systems:** shorter edit–compile–inspect loops;
- **XSB:** selective tabling with explicit semantic and memory boundaries;
- **Trealla, Scryer, and Clausal:** smaller embeddings and cleaner host-language
  interfaces.

These are design sources, not code-mining targets. Features enter this fork
only when their semantics fit GNU Prolog, their licensing is compatible, and
their behavior can be reconstructed from tests.

## Documentation and conversation

- The manual is under [`doc/`](doc/README).
- Upstream development and bug tracking live at
  [didoudiaz/gprolog](https://github.com/didoudiaz/gprolog/issues).
- The traditional user list is `users-prolog@gnu.org`.
- Historical bug mail may still be sent to `bug-prolog@gnu.org`.

This fork is an experiment in compiler evolution, but its ancestry is not
ambiguous. If you report a problem, please say whether it reproduces in
upstream GNU Prolog or only after one of this fork's additions.

## License and provenance

GNU Prolog was developed by Daniel Diaz. This repository is a fork of the
upstream GNU Prolog project and retains its notices and history.

Since version 1.4.0, GNU Prolog is distributed under a dual license. You may
redistribute and/or modify it under either:

- the GNU Lesser General Public License, version 3 or later; or
- the GNU General Public License, version 2 or later;

or under both in parallel. See [COPYING](COPYING) for the complete terms.
Versions before 1.4.0 were released entirely under the GPL.

GNU Prolog is provided without warranty, including implied warranties of
merchantability or fitness for a particular purpose.

---

**Keep the native spine. Open the compiler. Let Prolog teach the machine how to
compile Prolog.**
