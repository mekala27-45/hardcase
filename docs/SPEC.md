# Hardcase contract

The executable preregistration is requests/experiment.json. Every setting below is a design choice, not an observed result. Observations are retained under evidence with source commit and run provenance.

## Data and identity

Capture the official BEIR SciFact archive with path, size, member and schema checks. Keep upstream SciFact, BEIR corpus and qrel notices distinct. Preserve source document IDs. The declared expected inventory is 5183 documents, 809 train queries, 300 test queries, 919 train qrel rows and 339 test rows. An inventory mismatch stops preparation.

Normalize title and abstract with NFC, join using two newlines, and tokenize with the pinned student tokenizer to 256 tokens. Store exact visible character offsets and token IDs/digests. BM25 and every encoder use that same visible text. Never imply that a truncated section was encoded.

Purge training queries connected to test text through normalized character-trigram Jaccard similarity at least 0.9. This audit reads no test qrels. Group remaining training queries by the same duplicate rule plus connected shared-positive-document links. Hash seed and complete group members into an 80/20 fit/validation assignment. No positive supervision document can cross these development partitions. Test groups are constructed only inside evaluation using the same fixed algorithm.

## Candidates and schedule

BM25 uses positive Robertson IDF, k1=1.5 and b=0.75 with stable document-ID ties. Dense retrieval is normalized exact dot product over the full corpus. Fuse top-50 BM25 and unchanged-encoder lists with RRF constant 60. Eligible hard candidates occupy fused ranks 5 through 50. Exclude every known positive and normalized duplicate positive document view. Choose four by seeded stable digest; record any deterministic fill. They remain unjudged weak negatives.

All arms use the same query schedule and positive sampling. Each fit query appears in the first pass before repeats. Uniform candidates are chosen from the eligible corpus. Hard and distilled arms share identical mined lists. Teacher scores retain query, selected positive and ordered candidate IDs with alignment hashes. The teacher supplies weak supervision only.

## Actual optimization

Start each arm from the same pinned MiniLM state. Train only transformer blocks 4 and 5; embeddings and blocks 0 through 3 stay frozen. Masked mean pooling and L2 normalization define the vectors. Per-query candidates are the selected positive and four weak negatives; no in-batch negative assumption is added.

Student logits equal cosine divided by 0.05. Contrastive loss equals logsumexp of all candidate logits minus logsumexp of all known-positive logits in the candidate set. Distillation uses KL from detached teacher softmax at temperature 1.0 to the student distribution with coefficient 0.1. Test qrels never enter this objective.

The registered budget is seed 2701, AdamW learning rate 0.00002, weight decay 0.01, two queries per microbatch, four accumulation steps, 120 optimizer updates, twelve warm-up updates and gradient norm cap 1.0. These are planned settings until the step ledger records execution. Validate at updates 40, 80 and 120 after re-encoding the full corpus with that checkpoint.

Atomic checkpoints include safetensors, tokenizer, optimizer, scheduler, RNG, sample cursor, configuration and content identity. Hash every file before updating the latest pointer. Trusted optimizer state is never accepted from a public upload. Independent-process resume must reproduce parameter and RNG hashes.

Select each arm checkpoint by validation nDCG@10, using a 0.000001 tie tolerance and earlier update. Select the overall candidate with the registered arm order as the final tie break. Keep every arm in the final study. Selection alone is not evidence of improvement.

## Export and serving

Export base and selected candidate to float32 ONNX with dynamic batch/sequence axes, mean pooling and normalization inside the graph. Check tokenizer IDs and masks exactly. Per-vector parity limits are maximum absolute error 0.0001 and cosine distance 0.00001. Use fixed fit/validation length strata and separately labeled authored edge cases.

Attempt dynamic QInt8 MatMul/Gemm weight quantization. Re-encode the entire corpus for every variant, retaining float32 output vectors. INT8 is eligible only within the declared validation quality loss and resource envelope and when measured faster. Freeze the variant before opening test results. Unsupported export remains failed, not zero or claimed faster.

Bundle identity hashes graph, tokenizer, model state reference, visible text policy, corpus, ID map, vector matrix, encoding receipt and runtime compatibility. The API verifies all bytes and a fixed startup embedding probe. It loads only prepackaged allowlisted bundles; requests cannot fetch models, train, export or choose file paths.

## Independent evaluation

The five main methods are BM25, unchanged encoder and the three validation-selected trained arms. Candidate float32 and candidate INT8 form a separate export table. Preserve every planned method-query row. Metrics are nDCG@10, Recall@10, Recall@100 and MRR@10 from published qrels. Duplicate retrieved IDs fail. Missing execution stays null.

The primary endpoint is selected-candidate minus base mean query nDCG@10. Sample whole connected test groups with replacement for 10000 fixed-seed percentile bootstrap draws and compute query-weighted means. Report group size imbalance and degenerate cases. Incomplete primary pairs suppress the complete estimate.

Secondary contrasts are hard minus uniform, distilled minus hard and candidate minus BM25. Use 10000 two-sided group sign flips with plus-one correction and Benjamini-Hochberg over the complete family. Report the exchangeability limitation. Error samples are post-run diagnosis, not selection data. Export drift compares each export with its exact PyTorch parent.

## API and transactional release

Routes are defined in src/hardcase/api/server.py. Search accepts only fixed aliases, a nonempty query of at most 512 Unicode characters and top_k from 1 to 20. Enforce 8 KiB bodies, one active request per session and a ten-second deadline. Anonymous capabilities contain 256 random bits; only their digests are stored. Receipt reads and idempotency bind to the session. Raw visitor query text is not retained.

At admission, capture one immutable bundle and alias generation. Persist terminal status and artifact identities after a final validity check. Ordinary rollback may leave an admitted request on the old valid bundle. Integrity revocation refuses the final commit and clears results. A new generation is a transaction, never an in-place model/index swap. Promotion and rollback require a protected operator token, expected generation, report/policy digests, deployment identity, expiry and idempotency key.

The registered promotion policy requires all arms complete, validation gain at least 0.01, float32 parity, complete held-out main rows, nonnegative test gain, grouped interval lower bound greater than -0.01, Recall@100 change at least -0.02, measured warm end-to-end p95 below 1500 ms, peak RSS below 768 MiB and fresh verified live bundle evidence. Local inference timing excludes network/DB and cannot substitute for the end-to-end gate.

## Completion

RESULTS.md is generated from evidence/completion.json. All eighteen lines require observed evidence. A health-only deployment, prepared tag, implemented evaluator or synthetic fixture cannot satisfy its corresponding execution line. Stretch work starts only after core evidence is complete.
