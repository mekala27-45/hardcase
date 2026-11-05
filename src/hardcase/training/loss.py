from hardcase.contracts import require


def objective(logits, positive_mask, teacher_scores=None, coefficient=0.1):
    import torch
    require(logits.ndim == 2 and positive_mask.shape == logits.shape, "LOSS_SHAPE")
    require(positive_mask.dtype == torch.bool and bool(positive_mask.any(dim=1).all()), "MISSING_POSITIVE")
    require(bool(torch.isfinite(logits).all()), "NONFINITE_LOGITS")
    contrastive = (torch.logsumexp(logits, dim=1) - torch.logsumexp(logits.masked_fill(~positive_mask, float("-inf")), dim=1)).mean()
    distillation = logits.sum() * 0
    if teacher_scores is not None:
        require(teacher_scores.shape == logits.shape and bool(torch.isfinite(teacher_scores).all()), "TEACHER_SHAPE_OR_FINITE")
        teacher_log_probs = torch.log_softmax(teacher_scores.detach(), dim=1)
        teacher_probs = teacher_log_probs.exp()
        student_log_probs = torch.log_softmax(logits, dim=1)
        distillation = (teacher_probs * (teacher_log_probs - student_log_probs)).sum(dim=1).mean()
    return contrastive + coefficient * distillation, contrastive, distillation


def validate_candidate_alignment(ids, known_positives, teacher_record=None):
    from hardcase.contracts import digest
    require(len(ids) == len(set(ids)), "DUPLICATE_CANDIDATE")
    mask = [d in set(known_positives) for d in ids]
    require(any(mask), "MISSING_POSITIVE")
    if teacher_record is not None:
        require(teacher_record["candidate_ids"] == ids and teacher_record["candidate_digest"] == digest(ids), "TEACHER_ALIGNMENT")
        require(len(teacher_record["scores"]) == len(ids), "TEACHER_SCORE_COUNT")
    return mask
