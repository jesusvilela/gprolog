"""Differential and structural float-indexing checks for GNU Prolog.

The emitted WAM must use new float instructions, not merely pass semantic
checks using stale bootstrap-generated WAM files.
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
    pl2wam = bindir / ('pl2wam' + suffix)
    if not all(x.is_file() for x in (gplc, gprolog, pl2wam)):
        raise SystemExit(f'missing GNU Prolog executables in {bindir}')
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ.get('PATH', ''))
    checks = []
    with tempfile.TemporaryDirectory(prefix='gprolog-float-index-') as td:
        work = Path(td)
        for src in (HERE / 'fixtures').glob('*.pl'):
            shutil.copyfile(src, work / src.name)
        commands = [
            ('generate-float-wam', [str(pl2wam), '--fast-math', 'float_indexing.pl']),
            ('generate-no-float-wam', [str(pl2wam), '--fast-math', 'no_float.pl']),
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
            switches = []
            if mode.startswith('generate-') and ok:
                wam_path = work / ('float_indexing.wam' if mode == 'generate-float-wam'
                                   else 'no_float.wam')
                ok = wam_path.is_file()
                if ok:
                    switches = [line.strip() for line in wam_path.read_text(encoding='utf-8').splitlines()
                                if 'switch_on_' in line]
                    emitted = '\n'.join(switches)
                    if mode == 'generate-float-wam':
                        ok = 'switch_on_term_flt(' in emitted and 'switch_on_float(' in emitted
                    else:
                        ok = 'switch_on_term(' in emitted and 'switch_on_term_flt(' not in emitted
            if mode in ('native-float', 'consulted-float'):
                ok = ok and proc.stdout.count('PASS ') == 13
                ok = ok and 'ALL 13 FLOAT INDEXING CHECKS PASSED' in proc.stdout
            if mode == 'native-no-float':
                ok = ok and 'NO FLOAT SUCCESS' in proc.stdout
            checks.append({'mode': mode, 'command': cmd, 'exit': proc.returncode,
                           'passed': ok, 'output': proc.stdout, 'wam_switches': switches})
            print(f'[{mode}] exit={proc.returncode} passed={ok}\n{proc.stdout}')
            if switches:
                print('WAM switches:\n' + '\n'.join(switches[:25]))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(checks, indent=2) + '\n', encoding='utf-8')
            if not ok:
                raise SystemExit(f'{mode} failed')
    print('PASS: float-indexing structural and semantic regression suite')


if __name__ == '__main__':
    main()
