import math
import unittest
import importlib.util
from hardcase.training.loss import validate_candidate_alignment
from hardcase.contracts import digest


class AlignmentTests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(validate_candidate_alignment(["p", "n"], ["p"]), [True, False])

    def test_reordered_teacher(self):
        with self.assertRaisesRegex(ValueError, "ALIGNMENT"):
            validate_candidate_alignment(["p", "n"], ["p"], {"candidate_ids": ["n", "p"], "candidate_digest": digest(["n", "p"]), "scores": [1, 2]})

    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            validate_candidate_alignment(["p", "p"], ["p"])

    def test_missing_positive(self):
        with self.assertRaisesRegex(ValueError, "MISSING"):
            validate_candidate_alignment(["n"], ["p"])


@unittest.skipUnless(importlib.util.find_spec("torch"), "Torch numerical checks require the locked worker environment")
class LossTests(unittest.TestCase):
    def test_numpy_reference_and_permutation(self):
        import numpy as np
        import torch
        from hardcase.training.loss import objective
        values = np.array([[1000., 1001., 999.]])
        mask = np.array([[True, False, True]])
        shifted = values - values.max()
        expected = np.log(np.exp(shifted).sum()) - np.log(np.exp(shifted[mask]).sum())
        logits = torch.tensor(values, requires_grad=True)
        loss, _, _ = objective(logits, torch.tensor(mask))
        self.assertAlmostEqual(loss.item(), expected, places=10)
        perm = [2, 0, 1]
        self.assertAlmostEqual(objective(logits[:, perm], torch.tensor(mask[:, perm]))[0].item(), expected, places=10)

    def test_finite_difference_and_teacher_detached(self):
        import torch
        from hardcase.training.loss import objective
        logits = torch.tensor([[0.4, -0.2, 0.1]], dtype=torch.float64, requires_grad=True)
        mask = torch.tensor([[True, False, False]])
        teacher = torch.tensor([[2., 0., -1000.]], dtype=torch.float64, requires_grad=True)
        loss = objective(logits, mask, teacher)[0]
        loss.backward()
        self.assertIsNone(teacher.grad)
        for j in range(3):
            plus, minus = logits.detach().clone(), logits.detach().clone()
            plus[0, j] += 1e-6
            minus[0, j] -= 1e-6
            difference = (objective(plus, mask, teacher)[0] - objective(minus, mask, teacher)[0]) / 2e-6
            self.assertAlmostEqual(logits.grad[0, j].item(), difference.item(), places=7)
        self.assertLess(logits.grad[0, 0], 0)

    def test_no_positive_refuses(self):
        import torch
        from hardcase.training.loss import objective
        with self.assertRaisesRegex(ValueError, "MISSING"):
            objective(torch.zeros(1, 2), torch.zeros(1, 2, dtype=torch.bool))
