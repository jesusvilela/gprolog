"""Run the same expansion regressions through native and consulted GNU Prolog.

python tests/goal_expansion/run.py --bin-dir /path/to/gprolog/bin
Use a bin-dir from an in-place or installed build, not a system SWI executable.
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=HERE / 'results.json')
    args = parser.parse_args()
    bindir = args.bin_dir.resolve()
    suffix = '.exe' if os.name == 'nt' else ''
    gplc = bindir / ('gplc' + suffix)
    gprolog = bindir / ('gprolog' + suffix)
    assert gplc.is_file() and gprolog.is_file(), bindir
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ.get('PATH', ''))
    results = []
    with tempfile.TemporaryDirectory(prefix='gprolog-goal-expansion-') as tmp:
        work = Path(tmp)
        for source in (HERE / 'fixtures').glob('*.pl'):
            shutil.copyfile(source, work / source.name)
        exe = work / ('expansion' + suffix)
        commands = [
            ('reject-invalid', [str(gplc), '--no-top-level', '-o', str(work / ('invalid' + suffix)), 'invalid.pl']),
            ('compile-native', [str(gplc), '--no-top-level', '-o', str(exe), 'expansion.pl']),
            ('native', [str(exe)]),
            ('consulted', [str(gprolog), '--quiet', '--consult-file', 'expansion.pl'])]
        for mode, command in commands:
            proc = subprocess.run(command, cwd=work, env=env, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=120)
            print(f'[{mode}] exit={proc.returncode}\n{proc.stdout}')
            ok = proc.returncode == 0
            if mode == 'reject-invalid':
                ok = proc.returncode != 0 and 'goal_expansion_input' in proc.stdout
            elif mode != 'compile-native':
                ok = ok and 'ALL 29 GOAL EXPANSION CHECKS PASSED' in proc.stdout
                ok = ok and proc.stdout.count('PASS ') == 29
            results.append({'mode': mode, 'command': command, 'exit': proc.returncode,
                            'passed': ok, 'output': proc.stdout})
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
            if not ok:
                raise SystemExit(f'{mode} failed')
    print('PASS: native and consulted paths each passed 29 checks')


if __name__ == '__main__':
    main()
