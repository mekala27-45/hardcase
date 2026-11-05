# Observed build journal

This journal records observed outcomes. It does not invent failed model experiments.

| Time (UTC) | Attempt | Evidence | Decision |
| --- | --- | --- | --- |
| 2026-11-05, preparation run | Capture, group, mine and score the full frozen source | [Preparation run 42109854166](https://github.com/mekala27-45/hardcase/actions/runs/42109854166), evidence/preparation | Retain the frozen inputs and their notices; keep test qrels out of training. |
| 2026-11-05, first expanded interface check | Navigate all five views at multiple widths | [Failed run 42116135644](https://github.com/mekala27-45/hardcase/actions/runs/42116135644) | Desktop inline text produced a different accessible name. Add explicit button labels. |
| 2026-11-05, corrected interface check | Repeat the responsive navigation and font/contrast checks | [Successful run 42116694390](https://github.com/mekala27-45/hardcase/actions/runs/42116694390) | Retain the observed checks and screenshots. |
| 2026-11-05T22:24:34Z | Build selected-document persistence in the review branch | [Review run 42121205972](https://github.com/mekala27-45/hardcase/actions/runs/42121205972) | TypeScript correctly rejected a nullable document argument. Narrow it after the identity guard and add populated-control coverage. |
| 2026-11-05, review preparation | Continue through the new workspace configuration | Windows executor and browser path-validation errors; no command executed | Use the connected repository review branch. Do not claim new local verification. |
| 2026-11-05, deployment preparation | Configure database access and publish further changes to main | Automatic approval review rejected these actions | Keep the credential out of source and the remaining commits in draft PR 1. Await explicit approval for the blocked destinations. |
