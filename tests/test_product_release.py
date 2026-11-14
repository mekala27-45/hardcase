import os
from contextlib import chdir
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from hardcase.contracts import digest
from deploy import publish_product


class ProductReleaseTests(unittest.TestCase):
    def exercise(self, *, core=True, conclusion='success', existing=False, changed=False):
        audit={'passed':True}
        fixtures={
            'requests/publish.json':{'tag':'v0.2.0','report_digest':'report','audit_digest':digest(audit),'decision_digest':'decision'},
            'evidence/evaluation/report.json':{'report_digest':'changed' if changed else 'report'},
            'evidence/evaluation/independent-audit.json':audit,
            'evidence/release/decision.json':{'decision_digest':'decision'},
            'evidence/completion.json':{str(i):{'verified':core} for i in range(1,19)},
        }
        runs=[{'path':'.github/workflows/'+name+'.yml','status':'completed','conclusion':conclusion} for name in ('ci','site')]
        calls=[]
        def command(args,**kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0 if existing or args[2]=='create' else 1)
        with tempfile.TemporaryDirectory() as folder, chdir(folder):
            with patch.dict(os.environ,{'GITHUB_SHA':'a'*40,'GITHUB_REPOSITORY':'mekala27-45/hardcase'}),patch.object(publish_product,'load_json',side_effect=lambda p:fixtures[str(p)]),patch.object(publish_product,'refresh'),patch.object(publish_product,'gh',return_value={'workflow_runs':runs}),patch.object(publish_product.subprocess,'run',side_effect=command):
                try:
                    publish_product.run()
                    return calls,None
                except ValueError as error:
                    return calls,str(error)

    def test_changed_evidence_incomplete_core_and_failed_ci_cannot_publish(self):
        for options,reason in [({'changed':True},'RELEASE_INPUT_CHANGED'),({'core':False},'CORE_EVIDENCE_INCOMPLETE'),({'conclusion':'failure'},'EXACT_COMMIT_CHECK_FAILED')]:
            calls,error=self.exercise(**options)
            self.assertEqual(error,reason)
            self.assertFalse(any(row[1:3]==['release','create'] for row in calls))

    def test_existing_release_cannot_be_replaced(self):
        calls,error=self.exercise(existing=True)
        self.assertEqual(error,'PRODUCT_RELEASE_ALREADY_EXISTS')
        self.assertFalse(any(row[1:3]==['release','create'] for row in calls))

    def test_verified_release_targets_exact_checked_commit(self):
        calls,error=self.exercise()
        self.assertIsNone(error)
        create=next(row for row in calls if row[1:3]==['release','create'])
        self.assertEqual(create[create.index('--target')+1],'a'*40)
        self.assertIn('--notes-file',create)
