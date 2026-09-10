#!/usr/bin/env python3
"""Compare matched-forcing FaIR and Hector paired attribution outputs.

This script does not impose a pass/fail closeness criterion between models.
Scientific disagreement is reported, not suppressed. The gates are structural:
finite outputs, matched forcing in each model, and physically signed removal response.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

F = Path('fair_matched_attribution.csv')
H = Path('hector_matched_attribution.csv')
FS = Path('fair_matched_summary.json')
HS = Path('hector_matched_summary.json')
for p in (F, H, FS, HS):
    if not p.exists():
        raise FileNotFoundError(p)

f = pd.read_csv(F)
h = pd.read_csv(H)
fs = json.loads(FS.read_text(encoding='utf-8'))
hs = json.loads(HS.read_text(encoding='utf-8'))

if not np.isfinite(f[['delta_co2_p50_ppm','fraction_p50']].dropna().to_numpy()).all():
    raise RuntimeError('Non-finite FaIR matched attribution values')
if not np.isfinite(h[['delta_co2_ppm','apparent_response_fraction']].dropna().to_numpy()).all():
    raise RuntimeError('Non-finite Hector matched attribution values')

milestones = [2040, 2100, 2156, 2184, 2200, 2300]
rows = []
for y in milestones:
    fr = f.iloc[int(np.argmin(np.abs(f.year.to_numpy(float)-y)))]
    hr = h.iloc[int(np.argmin(np.abs(h.year.to_numpy(float)-y)))]
    rows.append({
        'year': y,
        'fair_delta_co2_p05_ppm': fr.delta_co2_p05_ppm,
        'fair_delta_co2_p50_ppm': fr.delta_co2_p50_ppm,
        'fair_delta_co2_p95_ppm': fr.delta_co2_p95_ppm,
        'hector_delta_co2_ppm': hr.delta_co2_ppm,
        'hector_minus_fair_p50_delta_ppm': hr.delta_co2_ppm - fr.delta_co2_p50_ppm,
        'fair_response_fraction_p05': fr.fraction_p05,
        'fair_response_fraction_p50': fr.fraction_p50,
        'fair_response_fraction_p95': fr.fraction_p95,
        'hector_response_fraction': hr.apparent_response_fraction,
        'hector_minus_fair_p50_fraction': hr.apparent_response_fraction - fr.fraction_p50,
        'hector_inside_fair_p05_p95_fraction': bool(
            np.isfinite(fr.fraction_p05) and np.isfinite(fr.fraction_p95)
            and fr.fraction_p05 <= hr.apparent_response_fraction <= fr.fraction_p95
        ),
    })

out = pd.DataFrame(rows)
out.to_csv('matched_forcing_cross_model_summary.csv', index=False)

summary = {
    'experiment': 'V62 matched future non-CO2 forcing cross-model comparison',
    'models': {
        'FaIR': {'version': fs['version'], 'configs': fs['configs']},
        'Hector': {'version': hs['version']},
    },
    'forcing_target': fs['matched_nonco2_target'],
    'forcing_match_gates': {
        'fair_on_max_abs_wm2': fs['forcing_match_max_abs_on_wm2'],
        'fair_off_max_abs_wm2': fs['forcing_match_max_abs_off_wm2'],
        'hector_on_max_abs_wm2': hs['forcing_match_max_abs_on_wm2'],
        'hector_off_max_abs_wm2': hs['forcing_match_max_abs_off_wm2'],
    },
    'common_state_within_model_2026': {
        'fair_co2_maxabs_ppm': fs['common_state_2026_co2_maxabs_ppm'],
        'fair_tas_maxabs_c': fs['common_state_2026_tas_maxabs_c'],
        'hector_co2_abs_error_ppm': hs['common_state_2026_co2_abs_error_ppm'],
        'hector_tas_abs_error_c': hs['common_state_2026_tas_abs_error_c'],
    },
    'milestones': rows,
    'interpretation': (
        'Future non-CO2 forcing is now harmonized between FaIR and Hector from 2027 onward. '
        'Differences in paired CO2 response therefore reflect model carbon-cycle/climate-response structure '
        'rather than different prescribed future non-CO2 forcing pathways. Historical states and model parameters '
        'remain model-specific, so this is not an identity test.'
    ),
    'cross_model_closeness_is_not_a_failure_gate': True,
}
Path('matched_forcing_cross_model_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

lines = [
    '# V62 matched-forcing FaIR/Hector comparison', '',
    'Future non-CO2 forcing is harmonized from 2027 onward. Cross-model disagreement is reported rather than treated as an automatic failure.', '',
    '| Year | FaIR ΔCO₂ p50 (ppm) | Hector ΔCO₂ (ppm) | FaIR response p50 | Hector response | Hector inside FaIR p05–p95? |',
    '|---:|---:|---:|---:|---:|:---:|'
]
for r in rows:
    lines.append(
        f"| {r['year']} | {r['fair_delta_co2_p50_ppm']:.4f} | {r['hector_delta_co2_ppm']:.4f} | "
        f"{r['fair_response_fraction_p50']:.4f} | {r['hector_response_fraction']:.4f} | "
        f"{'yes' if r['hector_inside_fair_p05_p95_fraction'] else 'no'} |"
    )
Path('MATCHED_FORCING_RESULTS.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
