"""Differential float-indexing semantic checks for GNU Prolog.

Use after building the exact branch with ./configure, make, make install.
Produces a JSON record of all commands, stdout, stderr, and exit codes.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bin-dir', required=True, type=Path)
    p.add_argument('--output', type=Path, default=HERE / 'results.json')
    args = p.parse_args()
    bindir = args.bin_dir.resolve()
    suffix = '.exe' if os.name == 'nt' else ''
    gplc = bindir / ('gplc' + suffix)
    gprolog = bindir / ('gprolog' + suffix)
    if not gplc.is_file() or not gprolog.is_file():
        raise SystemExit(f'missing GNU Prolog executables in {bindir}')
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ.get('PATH', ''))
    checks = []
    with tempfile.TemporaryDirectory(prefix='gprolog-float-index-') as td:
        work = Path(td)
        for src in (HERE / 'fixtures').glob('*.pl'):
            shutil.copyfile(src, work / src.name)
        commands = [
            ('compile-float', [str(gplc), '--no-top-level', '-o',
                               str(work / ('float_indexing' + suffix)), 'float_indexing.pl']),
            ('native-float', [str(work / ('float_indexing' + suffix))]),
            ('consulted-float', [str(gprolog), '--quiet', '--consult-file', 'float_indexing.pl']),
            ('compile-no-float', [str(gplc), '--no-top-level', '-o',
                                  str(work / ('no_float' + suffix)), 'no_float.pl']),
            ('native-no-float', [str(work / ('no_float' + suffix))]),
        ]
        for mode, cmd in commands:
            proc = subprocess.run(cmd, cwd=work, env=env, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=180)
            ok = proc.returncode == 0
            if mode in ('native-float', 'consulted-float'):
                ok = ok and proc.stdout.count('PASS ') == 13
                ok = ok and 'ALL 13 FLOAT INDEXING CHECKS PASSED' in proc.stdout
            if mode == 'native-no-float':
                ok = ok and 'NO FLOAT SUCCESS' in proc.stdout
            checks.append({'mode': mode, 'command': cmd, 'exit': proc.returncode,
                           'passed': ok, 'output': proc.stdout})
            print(f'[{mode}] exit={proc.returncode} passed={ok}\n{proc.stdout}')
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(checks, indent=2) + '\n', encoding='utf-8')
            if not ok:
                raise SystemExit(f'{mode} failed')
    print('PASS: float-indexing regression suite')


if __name__ == '__main__':
    main()
