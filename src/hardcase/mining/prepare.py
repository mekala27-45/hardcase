"""Freeze development inputs; teacher labels never touch final evaluation."""
import time
from pathlib import Path
from hardcase.contracts import Stage, atomic_json, digest, load_json, require, utcnow
from hardcase.data.capture import capture
from hardcase.data.grouping import leakage_purge, grouped_split
from hardcase.data.views import document_view
from hardcase.training.encoder import download_locked, load_encoder, encode, parameter_hashes
from .retrieval import BM25, exact_search
from .candidates import weak_negatives, sample_schedule
from evaluation.metrics import grade, qrel_map


def prepare():
    import numpy as np
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    config = load_json("requests/experiment.json")
    torch.set_num_threads(2)
    torch.manual_seed(config["seed"])
    torch.use_deterministic_algorithms(True)
    capture()
    with Stage("artifacts/preparation", "prepare", {"config": digest(config), "models": digest(load_json("requests/model-lock.json"))}) as report:
        corpus = load_json("data/processed/corpus.json")
        queries = load_json("data/processed/train-queries.json")
        qrels = load_json("data/processed/train-qrels.json")
        texts = {q: row["text"] for q, row in queries.items()}
        audit = leakage_purge(texts, load_json("data/audit/test-query-text.json"), config["query_duplicate_trigram_jaccard"])
        atomic_json("data/manifests/purge.json", audit)
        kept = {q: texts[q] for q in audit["kept"]}
        split = grouped_split(kept, qrels, config["seed"], config["validation_group_fraction"], config["query_duplicate_trigram_jaccard"])
        atomic_json("data/manifests/split.json", split)
        positive = {q: sorted(r["document_id"] for r in qrels if r["query_id"] == q and r["score"] > 0) for q in split["fit"]}
        model_path = download_locked("student")
        model, tokenizer = load_encoder(model_path)
        state_digest = digest(parameter_hashes(model))
        documents = {d: document_view(corpus[d], tokenizer, config["max_length"]) for d in sorted(corpus)}
        atomic_json("data/processed/documents.json", documents)
        views = {d: row["visible_text"] for d, row in documents.items()}
        ids = sorted(views)
        matrix = encode(model, tokenizer, [views[d] for d in ids], config["max_length"], receipt_path="artifacts/preparation/base-corpus-encoding.json", identity=state_digest)
        np.save("data/processed/base-vectors.npy", matrix, allow_pickle=False)
        all_queries = sorted(kept)
        query_vectors = encode(model, tokenizer, [kept[q] for q in all_queries], config["max_length"], receipt_path="artifacts/preparation/base-development-encoding.json", identity=state_digest)
        vectors = dict(zip(all_queries, query_vectors))
        bm25 = BM25(views)
        lists = {q: weak_negatives(q, positive[q], views, bm25.search(kept[q], 50), exact_search(vectors[q], matrix, ids, 50), config["seed"]) for q in split["fit"]}
        atomic_json("data/processed/candidates.json", lists)
        schedule = sample_schedule(split["fit"], positive, config["optimizer_updates"] * config["microbatch_queries"] * config["accumulation_steps"], config["seed"])
        atomic_json("data/processed/schedule.json", schedule)
        gold = qrel_map(qrels)
        baseline_validation = []
        for method in ("bm25", "base_encoder"):
            rankings = {}
            for q in split["validation"]:
                ranking = bm25.search(kept[q], 100) if method == "bm25" else exact_search(vectors[q], matrix, ids, 100)
                rankings[q] = [d for d, _ in ranking]
                baseline_validation.append({"method": method, "query_id": q, "metrics": grade(rankings[q], gold[q]), "status": "completed"})
            atomic_json(f"artifacts/preparation/{method}-validation-rankings.json", rankings)
        atomic_json("artifacts/preparation/baseline-validation.json", baseline_validation)
        del model
        teacher_path = download_locked("teacher")
        teacher = AutoModelForSequenceClassification.from_pretrained(teacher_path, local_files_only=True, trust_remote_code=False).eval()
        teacher.requires_grad_(False)
        teacher_tokenizer = AutoTokenizer.from_pretrained(teacher_path, local_files_only=True, trust_remote_code=False)
        scored = {}
        started = utcnow()
        timer = time.perf_counter()
        total_tokens = 0
        audit_rows = []
        with torch.inference_mode():
            for q in split["fit"]:
                for positive_id in positive[q]:
                    candidates = [positive_id] + [r["id"] for r in lists[q]["hard"]]
                    batch = teacher_tokenizer([kept[q]] * len(candidates), [views[d] for d in candidates], truncation=True, max_length=512, padding=True, return_tensors="pt")
                    total_tokens += int(batch["attention_mask"].sum())
                    scores = teacher(**batch).logits.flatten().tolist()
                    require(len(scores) == len(candidates) and np.isfinite(scores).all(), "TEACHER_INVALID_OUTPUT")
                    key = q + ":" + positive_id
                    scored[key] = {"query_id": q, "positive_id": positive_id, "candidate_ids": candidates, "candidate_digest": digest(candidates), "scores": scores, "teacher_revision": load_json("requests/model-lock.json")["teacher"]["revision"], "pair_token_digest": digest(batch["input_ids"].tolist()), "pair_truncated": [len(teacher_tokenizer(kept[q], views[d], truncation=False)["input_ids"]) > 512 for d in candidates]}
                    for index, d in enumerate(candidates[1:], 1):
                        audit_rows.append({"query_id": q, "document_id": d, "query": kept[q], "visible_text": views[d], "judgment": "unjudged", "fused_rank": next(r["fused_rank"] for r in lists[q]["hard"] if r["id"] == d), "teacher_score": scores[index], "selected_positive_score": scores[0], "automated_flag": "teacher_prefers_unjudged" if scores[index] >= scores[0] else "unjudged_not_adjudicated", "review": "automated; no human or domain expert adjudication"})
        atomic_json("data/processed/teacher-scores.json", scored)
        audit_rows = sorted(audit_rows, key=lambda r: (digest([config["seed"], r["query_id"], r["document_id"]]), r["query_id"], r["document_id"]))
        unique = {}
        for row in audit_rows:
            unique.setdefault((row["query_id"], row["document_id"]), row)
        atomic_json("artifacts/preparation/mining-audit.json", list(unique.values())[:config["audit_pairs"]])
        atomic_json("artifacts/preparation/teacher-receipt.json", {"namespace": "teacher_supervision", "pairs": sum(len(r["scores"]) for r in scored.values()), "encoded_tokens": total_tokens, "seconds": time.perf_counter() - timer, "started_at": started, "ended_at": utcnow(), "scores_digest": digest(scored), "teacher": load_json("requests/model-lock.json")["teacher"]})
        frozen = {"config_digest": digest(config), "model_lock_digest": digest(load_json("requests/model-lock.json")), "source_digest": digest(load_json("data/manifests/source.json")), "split_digest": digest(split), "candidate_digest": digest(lists), "schedule_digest": digest(schedule), "teacher_digest": digest(scored), "document_view_digest": digest(documents), "base_state_digest": state_digest, "fit_queries": len(split["fit"]), "validation_queries": len(split["validation"]), "purged_queries": len(audit["purged"]), "corpus_documents": len(ids), "state": "frozen_before_training", "created_at": utcnow()}
        frozen["preparation_id"] = digest(frozen)
        atomic_json("data/manifests/preparation.json", frozen)
        report.update(frozen=frozen, baseline_validation={method: sum(r["metrics"]["ndcg10"] for r in baseline_validation if r["method"] == method) / len(split["validation"]) for method in ("bm25", "base_encoder")})


if __name__ == "__main__":
    prepare()
