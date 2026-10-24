"""Fail closed unless this exact revision's latest trusted Checks run passed.

Input is the authenticated GitHub workflow-runs response for checks.yml. No
credentials are accepted here; the workflow supplies its scoped token to gh.
"""
import json
import re
import sys


class ReleaseBlocked(ValueError):
    pass


def verify_checks(payload, commit, repository):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ReleaseBlocked('A full lowercase commit SHA is required.')
    candidates = []
    for run in payload.get('workflow_runs', []):
        if (
            run.get('head_sha') == commit
            and (run.get('head_repository') or {}).get('full_name', '').casefold() == repository.casefold()
            and run.get('event') == 'push'
            and run.get('path') == '.github/workflows/checks.yml'
        ):
            if not isinstance(run.get('id'), int) or run['id'] <= 0:
                raise ReleaseBlocked('Invalid Checks run metadata.')
            candidates.append(run)
    if not candidates:
        raise ReleaseBlocked('No trusted push Checks run exists for this exact revision.')
    # Do not accept an older success after a later failed/pending run or rerun.
    latest = max(candidates, key=lambda r: r['id'])
    if latest.get('status') != 'completed' or latest.get('conclusion') != 'success':
        raise ReleaseBlocked('The latest Checks run must complete successfully, including the image scan.')
    return latest['id']


def main():
    try:
        if len(sys.argv) != 3:
            raise ReleaseBlocked('Usage: release_gate.py COMMIT_SHA OWNER/REPOSITORY < runs.json')
        run_id = verify_checks(json.load(sys.stdin), sys.argv[1], sys.argv[2])
    except (ReleaseBlocked, json.JSONDecodeError, AttributeError, TypeError) as error:
        print(f'Release blocked: {error}', file=sys.stderr)
        return 1
    print(f'Validated Checks run {run_id} for {sys.argv[1]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
