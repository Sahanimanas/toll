"""Device resolution tests — must run on machines with no torch/GPU."""

import pytest

from anpr_pipeline import device as device_mod
from anpr_pipeline.device import resolve_device


def test_cpu_is_always_cpu(monkeypatch):
    monkeypatch.setattr(device_mod, "cuda_available", lambda: True)
    assert resolve_device("cpu") == "cpu"


def test_auto_without_cuda_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(device_mod, "cuda_available", lambda: False)
    assert resolve_device("auto") == "cpu"


def test_auto_with_cuda_picks_first_gpu(monkeypatch):
    monkeypatch.setattr(device_mod, "cuda_available", lambda: True)
    monkeypatch.setattr(device_mod, "_gpu_name", lambda index: "fake GPU")
    assert resolve_device("auto") == "cuda:0"


def test_explicit_cuda_normalized_to_indexed_device(monkeypatch):
    monkeypatch.setattr(device_mod, "cuda_available", lambda: True)
    monkeypatch.setattr(device_mod, "_gpu_name", lambda index: "fake GPU")
    assert resolve_device("cuda") == "cuda:0"
    assert resolve_device("cuda:1") == "cuda:1"


def test_explicit_cuda_without_cuda_fails_loudly(monkeypatch):
    monkeypatch.setattr(device_mod, "cuda_available", lambda: False)
    with pytest.raises(RuntimeError):
        resolve_device("cuda")
    with pytest.raises(RuntimeError):
        resolve_device("cuda:0")


def test_unknown_device_rejected():
    with pytest.raises(ValueError):
        resolve_device("tpu")


def test_input_is_case_and_whitespace_tolerant(monkeypatch):
    monkeypatch.setattr(device_mod, "cuda_available", lambda: False)
    assert resolve_device(" CPU ") == "cpu"
    assert resolve_device("") == "cpu"  # empty behaves like auto
