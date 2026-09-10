#!/usr/bin/env bash
set -euo pipefail
python -m py_compile planetary_restoration_model_v62.py test_planetary_restoration_model_v62.py
python test_planetary_restoration_model_v62.py
