import copy
import unittest
from deploy.verify_live import verify
from deploy.decide_release import decide
from hardcase.contracts import load_json


class LiveEvidenceTests(unittest.TestCase):
    def fixture(self):
        artifacts={key:key+'-fixture' for key in ('graph_digest','tokenizer_digest','corpus_digest','index_digest')}
        package={'bundles':[{'method':'candidate_float32','id':'candidate',**artifacts}]}
        rows=[]
        observations={'deployment_id':'fixture-deployment'}
        for channel in ('browser','separate_client'):
            receipt={'id':channel,'status':'completed','fresh':True,'replayed':False,'bundle_id':'candidate','alias':'experimental','deployment_id':'fixture-deployment','query_digest':channel,'top_document_ids':['d1'],'results':[{'id':'d1'}],**artifacts}
            observations[channel]={'receipt':receipt,'origin':'public_production','expected_query_digest':channel}
            rows.append({'id':channel,'status':'completed','receipt':copy.deepcopy(receipt)})
        return observations,{'observer':'independent_database_connection','receipts':rows},package

    def test_independent_receipt_binding(self):
        self.assertEqual(verify(*self.fixture())['status'],'verified')

    def test_response_only_cannot_prove_persistence(self):
        observations,database,package=self.fixture()
        database['receipts'][0]['receipt']['top_document_ids']=['different']
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_DB_RECEIPT_MISMATCH'):
            verify(observations,database,package)

    def test_replay_and_wrong_artifact_refused(self):
        for field,value in [('replayed',True),('graph_digest','another-model')]:
            with self.subTest(field=field):
                observations,database,package=self.fixture()
                observations['browser']['receipt'][field]=value
                database['receipts'][0]['receipt'][field]=value
                with self.assertRaises(ValueError):verify(observations,database,package)

    def test_missing_release_evidence_stays_refused(self):
        result=decide(load_json('requests/experiment.json'),{})
        self.assertFalse(result['passed'])
        self.assertIsNone(result['observed']['test_gain'])
        self.assertEqual(result['decision'],'candidate_refused_default_remains_baseline')

    def test_local_serving_cannot_pass_public_gate(self):
        with self.assertRaisesRegex(ValueError,'RELEASE_SERVING_SCOPE_MISMATCH'):
            decide(load_json('requests/experiment.json'),{'serving':{'origin':'local','warm_p95_ms':1}})
