"""Nomic remote code still expects Transformers' removed attention-mask helper."""

from __future__ import annotations

import pytest

from backend.embeddings import _install_legacy_attention_mask, _legacy_extended_attention_mask


def test_legacy_extended_attention_mask_keeps_ones_and_masks_zeros():
    torch = pytest.importorskip("torch")

    class Model:
        dtype = torch.float32

    extended = _legacy_extended_attention_mask(Model(), torch.tensor([[1, 1, 0]]), (1, 3))
    assert tuple(extended.shape) == (1, 1, 1, 3)
    assert extended[0, 0, 0, 0].item() == 0
    assert extended[0, 0, 0, 1].item() == 0
    assert extended[0, 0, 0, 2].item() == torch.finfo(torch.float32).min


def test_install_legacy_attention_mask_patches_nomic_class_once():
    class NomicBertModel:
        pass

    class Wrapper:
        def modules(self):
            return [NomicBertModel()]

    wrapper = Wrapper()
    _install_legacy_attention_mask(wrapper)
    assert NomicBertModel.get_extended_attention_mask is _legacy_extended_attention_mask
    _install_legacy_attention_mask(wrapper)
    assert NomicBertModel.get_extended_attention_mask is _legacy_extended_attention_mask
