"""Verify that PyTorch is the CUDA build and can actually compute on the GPU.

Run after any environment change that touches torch:

    .\\.venv\\Scripts\\python.exe scripts\\check_gpu.py

Exits non-zero if CUDA is unavailable or a device computation fails. See CLAUDE.md,
TECH STACK: torch must come from the cu126 index, never the default PyPI index.
"""

import sys

import torch


def main() -> int:
    print(f"torch.__version__            : {torch.__version__}")
    print(f"torch.version.cuda           : {torch.version.cuda}")
    print(f"torch.cuda.is_available()    : {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print(
            "\nFAIL: CUDA is not available.\n"
            "This machine has an RTX 4060. If this fails, the likely cause is a "
            "CPU-only wheel from the default PyPI index, not missing hardware.\n"
            "Reinstall with:\n"
            "  pip install torch torchvision "
            "--index-url https://download.pytorch.org/whl/cu126",
            file=sys.stderr,
        )
        return 1

    props = torch.cuda.get_device_properties(0)
    total = props.total_memory
    print(f"torch.cuda.get_device_name(0): {torch.cuda.get_device_name(0)}")
    print(f"  .total_memory              : {total} bytes ({total / 1024**3:.2f} GiB)")
    print(f"  compute capability         : {props.major}.{props.minor}")

    # Small matmul executed on the device, checked against a CPU reference.
    torch.manual_seed(0)
    a = torch.randn(512, 512, device="cuda")
    b = torch.randn(512, 512, device="cuda")
    c = a @ b
    torch.cuda.synchronize()

    ref = a.cpu() @ b.cpu()
    max_err = (c.cpu() - ref).abs().max().item()

    print(f"\nmatmul (512x512) on {c.device}")
    print(f"  result shape               : {tuple(c.shape)}")
    print(f"  result[0, :3]              : {c[0, :3].tolist()}")
    print(f"  max abs diff vs CPU        : {max_err:.3e}")
    print(f"  peak memory allocated      : {torch.cuda.max_memory_allocated() / 1024**2:.1f} MiB")

    # fp32 matmul on GPU vs CPU differs only by accumulation order.
    if max_err > 1e-3:
        print(f"\nFAIL: GPU/CPU mismatch too large ({max_err:.3e}).", file=sys.stderr)
        return 1

    print("\nOK: CUDA build verified, GPU computation correct.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
