"""Refresh execution-dependent checklist rows from retained evidence, never plans."""
from pathlib import Path
from hardcase.contracts import atomic_json, digest, load_json
from deploy.verify_live import verify


def optional(path):
    return load_json(path) if Path(path).is_file() else {}


def run():
    completion=load_json('evidence/completion.json')
    def item(number,passed,note):
        completion[str(number)]={'status':'done' if passed else 'not done','verified':bool(passed),'evidence':note}
    live=optional('evidence/live/pretest.json')
    live_verified=False
    if live.get('status')=='verified':
        actual=verify(load_json('evidence/live/observations.json'),load_json('evidence/live/independent-db.json'),load_json('evidence/live/package.json'))
        live_verified=all(actual[k]==live[k] for k in actual if k!='verified_at')
    item(1,live_verified and optional('evidence/setup/probe.json').get('status')=='completed','evidence/setup/probe.json and evidence/live/pretest.json retain actual gradient/export and public learned-runtime observations; configuration is recorded in evidence/live/configuration.json.')
    item(8,optional('evidence/faults/runtime-transactions.json').get('status')=='passed' and live_verified,'Actual-bundle registry and transactional rollback/revocation tests: evidence/faults/runtime-transactions.json. The initialized production registry and matching receipts are independently observed in evidence/live/.')
    item(9,live_verified,'Unchanged deploy/verify_live.py revalidates separate public browser/client responses against independently queried production database receipts and packaged artifact identities in evidence/live/.')
    study=optional('evidence/evaluation/report.json')
    audit=optional('evidence/evaluation/independent-audit.json')
    study_ok=study.get('status')=='completed' and study.get('main_completed_rows')==study.get('main_planned_rows')==1500 and audit.get('passed') is True and audit.get('report_digest')==study.get('report_digest') and digest({k:v for k,v in study.items() if k!='report_digest'})==study.get('report_digest')
    item(10,study_ok,'evidence/evaluation/report.json and independent-audit.json bind the first frozen attempt, retained rankings, original judgments, all planned rows and independent regrading.' if study_ok else 'Frozen request requests/evaluate.json is admitted. Completion requires the retained first evaluation report and passing independent ranking audit; no pending row is counted as complete.')
    smoke=optional('evidence/serving/public-smoke.json')
    observed=optional('evidence/live/client-observations.json')
    smoke_ok=smoke.get('status')=='completed' and smoke.get('completed')==smoke.get('planned')==16 and smoke.get('origin')=='public_production' and digest(observed.get('rows'))==smoke.get('observations_digest')
    item(11,smoke_ok and bool(optional('evidence/serving/local-open-loop.json')),'Local staged timing and open-loop observations remain in evidence/serving/. The bounded public smoke binds sixteen serial requests and persisted readbacks in public-smoke.json and evidence/live/client-observations.json; first observer failure is retained under evidence/serving/attempts/.')
    decision=optional('evidence/release/decision.json')
    faults=all(optional(p).get('status')=='passed' for p in ['evidence/faults/actual-bundles.json','evidence/faults/runtime-transactions.json'])
    decision_ok=digest({k:v for k,v in decision.items() if k!='decision_digest'})==decision.get('decision_digest') and decision.get('source_digests',{}).get('evaluation')==digest(study)
    item(12,study_ok and smoke_ok and faults and decision_ok,'evidence/release/decision.json derives eligibility or refusal from frozen study, public verification and local resource evidence. All six actual-artifact fault cases are retained. A refusal is a valid completed decision and does not promote a model.')
    item(13,live_verified,'The public workbench serves genuine learned searches with artifact receipts. Existing training/evaluation/release/data views and the added Compare view retain explicit missing states. See evidence/live/observations.json and frontend checks.')
    item(17,study_ok and live_verified and smoke_ok,'Hash-locked original inputs were restored into a fresh checkout for independent regrading. Public browser/client/DB proof is separate in evidence/live/release-20261114/; the original pretest is unchanged.' if study_ok else 'Fresh checkout and immutable input assets are available. Final clean regrading requires the retained held-out rankings and a passing independent audit.')
    product=optional('evidence/release/product.json')
    item(18,product.get('status')=='published' and bool(product.get('tag')) and bool(product.get('commit')),'Merged implementation history is retained. Product release/tag: '+str(product.get('tag')) if product else 'Main contains the merged implementation and live proof. A product release tag remains pending final verified core evidence; asset prereleases do not satisfy this line.')
    atomic_json('evidence/completion.json',completion)


if __name__=='__main__':
    run()
