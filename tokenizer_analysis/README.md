# Tokenizer Analysis

This folder is intentionally separate from the training pipeline. `main_pipeline.py`
does not import or run anything from here.

Contents:

- `analyzer.py`: tokenizer efficiency measurement utilities
- `run_analysis.py`: standalone tokenizer-analysis entrypoint
- `results/`: generated tokenizer-only JSON outputs

Run it directly:

```text
python tokenizer_analysis/run_analysis.py
```

Default output:

```text
project/tokenizer_analysis/results/tokenizer_analysis.json
```

Training checkpoints and evaluation metrics remain outside this folder.
