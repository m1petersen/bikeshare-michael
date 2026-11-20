.PHONY: all data features train train-valid test clean model check-model

# --- The pipeline ----------------------------------------------------------
# Use the project venv when it exists, so results do not depend on whether
# it was activated (the system sklearn gives different scores).
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python)

all: data features train

data:
	$(PYTHON) -m src.ingest

features:
	$(PYTHON) -m src.features

train:
	$(PYTHON) -m src.train

# Validation scores only; use while iterating so the test set stays unseen.
train-valid:
	$(PYTHON) -m src.train --valid-only

test:
	$(PYTHON) -m pytest tests/ -q

clean:
	rm -f data/processed/*.parquet reports/metrics.json reports/metrics_valid.json reports/*.png

# --- The agent model (open weights, local) ----------------------------------
# Builds `bikeshare-coder`: the base model plus a 64k context window, which
# Claude Code needs and Ollama does not give you by default. Pick a larger
# BASE if your machine has the memory (see README.md).
BASE ?= qwen3.5:9b

model:
	ollama pull $(BASE)
	sed "s|^FROM .*|FROM $(BASE)|" model/Modelfile | ollama create bikeshare-coder -f -

check-model:
	bash model/check.sh
