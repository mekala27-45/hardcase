import argparse
import json
import math
import random
import time
from pathlib import Path
from hardcase.contracts import Stage, atomic_json, canonical, digest, load_json, require, utcnow
from hardcase.mining.candidates import select_checkpoint
from hardcase.mining.retrieval import exact_search
from .encoder import download_locked, load_encoder, pool, encode, parameter_hashes, freeze_policy
from .loss import objective, validate_candidate_alignment
from .checkpoint import save_checkpoint, load_checkpoint
from evaluation.metrics import grade, qrel_map


def run_arm(arm, resume=None):
    import numpy as np
    import torch
    config = load_json("requests/experiment.json")
    require(arm in config["arms"], "UNKNOWN_ARM")
    frozen = load_json("data/manifests/preparation.json")
    require(frozen["config_digest"] == digest(config), "CONFIG_CHANGED_AFTER_PREPARATION")
    require(frozen["model_lock_digest"] == digest(load_json("requests/model-lock.json")), "MODEL_LOCK_CHANGED")
    root = Path("artifacts/training") / arm
    root.mkdir(parents=True, exist_ok=True)
    with Stage(root, "run", {"arm": arm, "preparation_id": frozen["preparation_id"], "config_digest": digest(config)}) as report:
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        torch.manual_seed(config["seed"])
        random.seed(config["seed"])
        np.random.seed(config["seed"])
        documents = load_json("data/processed/documents.json")
        split = load_json("data/manifests/split.json")
        queries = load_json("data/processed/train-queries.json")
        lists = load_json("data/processed/candidates.json")
        teacher = load_json("data/processed/teacher-scores.json")
        schedule = load_json("data/processed/schedule.json")
        for key, value in (("split_digest", split), ("candidate_digest", lists), ("teacher_digest", teacher), ("schedule_digest", schedule), ("document_view_digest", documents)):
            require(frozen[key] == digest(value), "FROZEN_INPUT_CHANGED_" + key)
        require(set(row["query_id"] for row in schedule) == set(split["fit"]), "FIT_SCHEDULE_COVERAGE")
        gold = qrel_map(load_json("data/processed/train-qrels.json"))
        model, tokenizer = load_encoder(download_locked("student"))
        before = parameter_hashes(model)
        require(digest(before) == frozen["base_state_digest"], "ARM_START_NOT_IDENTICAL")
        names = freeze_policy(model)
        params = [p for p in model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(params, lr=config["learning_rate"], weight_decay=config["weight_decay"])
        warmup, total = config["warmup_updates"], config["optimizer_updates"]
        def factor(step):
            return (step + 1) / warmup if step < warmup else max(0.0, (total - step) / (total - warmup))
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, factor)
        identity = {"arm": arm, "config": digest(config), "preparation": frozen["preparation_id"], "base": digest(before), "trainable_names": names, "environment": load_json("evidence/setup/probe.json")["environment"]}
        report.update(identity=identity, trainable_names=names, trainable_parameters=sum(p.numel() for p in params), before_hashes=before, namespace="actual_training")
        start_update, cursor = 0, 0
        if resume:
            start_update, cursor = load_checkpoint(resume, identity, model, optimizer, scheduler)
            report["resume"] = {"path": str(resume), "update": start_update, "cursor": cursor}
        ids = sorted(documents)
        validation_rows = []
        table_path = root / "validation.json"
        if table_path.exists():
            validation_rows = load_json(table_path)
        microbatch, accumulation = config["microbatch_queries"], config["accumulation_steps"]
        report["actual_updates"] = start_update
        model.train()
        for step in range(start_update, total):
            started_at = utcnow()
            timer = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            initial = [p.detach().clone() for p in params]
            losses, contrastive_losses, distillation_losses, sample_rows = [], [], [], []
            token_count = 0
            lr = optimizer.param_groups[0]["lr"]
            for _ in range(accumulation):
                examples = schedule[cursor:cursor + microbatch]
                require(len(examples) == microbatch, "INCOMPLETE_ACCUMULATION")
                texts, masks, teacher_scores = [], [], []
                for sample in examples:
                    q, positive = sample["query_id"], sample["positive_id"]
                    route = "uniform" if arm == "uniform_contrastive" else "hard"
                    candidates = [positive] + [row["id"] for row in lists[q][route]]
                    score_record = teacher[q + ":" + positive] if arm == "hard_distilled" else None
                    masks.append(validate_candidate_alignment(candidates, lists[q]["positives"], score_record))
                    if score_record is not None:
                        teacher_scores.append(score_record["scores"])
                    texts.extend([queries[q]["text"]] + [documents[d]["visible_text"] for d in candidates])
                    sample_rows.append(sample | {"candidate_ids": candidates, "candidate_digest": digest(candidates)})
                batch = tokenizer(texts, padding=True, truncation=True, max_length=config["max_length"], return_tensors="pt")
                token_count += int(batch["attention_mask"].sum())
                embeddings = pool(model, batch).reshape(microbatch, 6, -1)
                logits = (embeddings[:, :1, :] * embeddings[:, 1:, :]).sum(-1) / config["student_temperature"]
                teacher_tensor = torch.tensor(teacher_scores, dtype=logits.dtype) / config["teacher_temperature"] if teacher_scores else None
                loss, contrastive, distillation = objective(logits, torch.tensor(masks, dtype=torch.bool), teacher_tensor, config["distillation_coefficient"])
                require(torch.isfinite(loss).item(), "NONFINITE_LOSS")
                (loss / accumulation).backward()
                losses.append(float(loss.detach()))
                contrastive_losses.append(float(contrastive.detach()))
                distillation_losses.append(float(distillation.detach()))
                cursor += microbatch
            norm = torch.nn.utils.clip_grad_norm_(params, config["gradient_norm_cap"])
            require(torch.isfinite(norm).item() and norm.item() > 0, "ZERO_OR_NONFINITE_GRADIENT")
            require(lr > 0, "ZERO_LEARNING_RATE")
            optimizer.step()
            scheduler.step()
            update_norm = math.sqrt(sum(float((p.detach() - old).pow(2).sum()) for p, old in zip(params, initial)))
            require(update_norm > 0, "UNCHANGED_OPTIMIZER_STEP")
            row = {"namespace": "actual_training", "arm": arm, "update": step + 1, "samples": sample_rows, "candidate_lists_digest": digest(sample_rows), "loss": sum(losses)/len(losses), "contrastive_loss": sum(contrastive_losses)/len(losses), "distillation_loss": sum(distillation_losses)/len(losses), "learning_rate": lr, "gradient_norm": float(norm), "update_norm": update_norm, "cumulative_examples": cursor, "encoded_tokens": token_count, "elapsed_seconds": time.perf_counter() - timer, "started_at": started_at, "ended_at": utcnow()}
            with (root / "steps.jsonl").open("ab") as stream:
                stream.write(canonical(row) + b"\n")
                stream.flush()
            report["actual_updates"] = step + 1
            if step + 1 in config["validation_updates"]:
                after = parameter_hashes(model)
                require(all(before[n] == after[n] for n in before if n not in names), "FROZEN_PARAMETER_CHANGED")
                require(any(before[n] != after[n] for n in names), "NO_LEARNED_PARAMETERS")
                checkpoint = root / f"checkpoint-{step + 1}"
                manifest = save_checkpoint(checkpoint, model, tokenizer, optimizer, scheduler, step + 1, cursor, identity)
                validation_timer = time.perf_counter()
                matrix = encode(model, tokenizer, [documents[d]["visible_text"] for d in ids], config["max_length"], receipt_path=root / f"corpus-encoding-{step+1}.json", identity=digest(after))
                qvecs = encode(model, tokenizer, [queries[q]["text"] for q in split["validation"]], config["max_length"], receipt_path=root / f"query-encoding-{step+1}.json", identity=digest(after))
                rankings = {q: [d for d, _ in exact_search(vector, matrix, ids)] for q, vector in zip(split["validation"], qvecs)}
                scores = [grade(rankings[q], gold[q]) for q in split["validation"]]
                atomic_json(root / f"validation-rankings-{step+1}.json", rankings)
                np.save(root / f"corpus-vectors-{step+1}.npy", matrix, allow_pickle=False)
                validation_rows.append({"arm": arm, "update": step + 1, "status": "completed", "ndcg10": sum(r["ndcg10"] for r in scores)/len(scores), "recall100": sum(r["recall100"] for r in scores)/len(scores), "query_count": len(scores), "corpus_count": len(ids), "seconds": time.perf_counter() - validation_timer, "checkpoint": str(checkpoint), "manifest_digest": digest(manifest), "state_digest": digest(after)})
                atomic_json(table_path, validation_rows)
                atomic_json(root / "progress.json", {"update": step + 1, "examples": cursor, "validation": validation_rows})
            print(json.dumps({"arm": arm, "update": step + 1, "loss": row["loss"], "seconds": row["elapsed_seconds"]}), flush=True)
        selected = select_checkpoint(validation_rows, config["arms"])
        report.update(selected=selected, after_hashes=parameter_hashes(model), examples=cursor, validation=validation_rows)
        atomic_json(root / "selected.json", selected)
        return selected


def run_all():
    config = load_json("requests/experiment.json")
    arms = config["arms"]
    shift = config["seed"] % len(arms)
    order = arms[shift:] + arms[:shift]
    rows = []
    for arm in order:
        try:
            rows.append(run_arm(arm))
        except Exception as error:
            rows.append({"arm": arm, "status": "failed", "ndcg10": None, "error": type(error).__name__ + ": " + str(error)[:300]})
    atomic_json("artifacts/training/arm-inventory.json", rows)
    require(all(r["status"] == "completed" for r in rows), "INCOMPLETE_THREE_ARM_COMPARISON")
    candidate = select_checkpoint(rows, arms)
    frozen = {"candidate": candidate, "arms": rows, "execution_order": order, "config_digest": digest(config), "preparation_id": load_json("data/manifests/preparation.json")["preparation_id"], "state": "selected_on_validation_before_test", "created_at": utcnow()}
    frozen["selection_id"] = digest(frozen)
    atomic_json("artifacts/training/selection.json", frozen)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm")
    parser.add_argument("--resume")
    args = parser.parse_args()
    run_arm(args.arm, args.resume) if args.arm else run_all()
