import unittest
from .release_gate import ReleaseBlocked, verify_checks

COMMIT = 'a' * 40
REPOSITORY = 'PalidaY/papradit_app'


def run(**changes):
    record = {
        'id': 100,
        'head_sha': COMMIT,
        'head_repository': {'full_name': REPOSITORY},
        'path': '.github/workflows/checks.yml',
        'event': 'push',
        'status': 'completed',
        'conclusion': 'success',
    }
    return dict(record, **changes)


class ReleaseGateTests(unittest.TestCase):
    def check(self, *runs):
        return verify_checks({'workflow_runs': list(runs)}, COMMIT, REPOSITORY)

    def test_exact_revision_success(self):
        self.assertEqual(self.check(run()), 100)

    def test_no_run_is_not_approval(self):
        with self.assertRaises(ReleaseBlocked):
            self.check()

    def test_other_commit_cannot_authorize_release(self):
        with self.assertRaises(ReleaseBlocked):
            self.check(run(head_sha='b' * 40))

    def test_fork_run_cannot_authorize_release(self):
        with self.assertRaises(ReleaseBlocked):
            self.check(run(head_repository={'full_name': 'other/papradit_app'}))

    def test_pending_checks_cannot_authorize_release(self):
        with self.assertRaises(ReleaseBlocked):
            self.check(run(status='in_progress', conclusion=None))

    def test_failed_scan_cannot_authorize_release(self):
        with self.assertRaises(ReleaseBlocked):
            self.check(run(conclusion='failure'))

    def test_new_failure_supersedes_old_success(self):
        with self.assertRaises(ReleaseBlocked):
            self.check(run(), run(id=101, conclusion='failure'))

    def test_other_workflow_cannot_authorize_release(self):
        with self.assertRaises(ReleaseBlocked):
            self.check(run(path='.github/workflows/deploy.yml'))

    def test_pull_request_run_cannot_authorize_push_release(self):
        with self.assertRaises(ReleaseBlocked):
            self.check(run(event='pull_request'))

    def test_invalid_run_metadata_fails_closed(self):
        with self.assertRaises(ReleaseBlocked):
            self.check(run(id=None))

    def test_short_sha_cannot_authorize_release(self):
        with self.assertRaises(ReleaseBlocked):
            verify_checks({'workflow_runs': [run()]}, 'abc1234', REPOSITORY)
