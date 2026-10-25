"""Frozen CLI entry point; only imports the evaluation-only preview."""
if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    from awareness_kernel.cli import main
    raise SystemExit(main())
