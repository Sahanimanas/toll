"""Compute-device resolution for the AI backends.

Follows the same convention as the `build_*` factories: `auto` silently
degrades to CPU when CUDA is missing, while an explicit `cuda`/`cuda:N`
request fails loudly rather than quietly running slow.
"""

import logging

logger = logging.getLogger(__name__)


def cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


def resolve_device(requested: str = "auto") -> str:
    """Resolve a device request to a concrete device string.

    - "auto"   -> "cuda:0" when CUDA is usable, else "cpu"
    - "cpu"    -> "cpu"
    - "cuda"   -> "cuda:0" (raises RuntimeError if CUDA is unavailable)
    - "cuda:N" -> unchanged (raises RuntimeError if CUDA is unavailable)
    """
    requested = (requested or "auto").strip().lower()
    if requested == "cpu":
        return "cpu"
    if requested == "auto":
        if cuda_available():
            logger.info("device: CUDA available, using cuda:0 (%s)", _gpu_name(0))
            return "cuda:0"
        logger.info("device: no CUDA, using cpu")
        return "cpu"
    if requested == "cuda" or requested.startswith("cuda:"):
        if not cuda_available():
            raise RuntimeError(
                f"ANPR_PIPELINE_DEVICE={requested!r} but CUDA is not available "
                "(install a CUDA-enabled torch build and check the driver)"
            )
        device = "cuda:0" if requested == "cuda" else requested
        logger.info("device: %s (%s)", device, _gpu_name(int(device.split(":")[1])))
        return device
    raise ValueError(f"unknown device {requested!r}; use auto, cpu, cuda or cuda:N")


def _gpu_name(index: int) -> str:
    try:
        import torch

        return torch.cuda.get_device_name(index)
    except Exception:
        return "unknown GPU"
