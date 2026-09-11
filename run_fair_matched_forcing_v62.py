#!/usr/bin/env python3
"""V62 matched-non-CO2-forcing FaIR experiment.

Purpose
-------
Create a cross-model forcing target and run FaIR 2.2.4 removal-ON / removal-OFF
from the same FaIR state while forcing *every FaIR ensemble member* to see the
same non-CO2 effective radiative forcing (ERF) trajectory after 2026.

The target trajectory is the median non-CO2 ERF from FaIR's official
"medium-extension" calibrated-constrained setup. A dedicated synthetic
forcing-only species (type="unspecified") is added as an additive bookkeeping
adjustment so that, after 2026, (sum of all non-CO2 forcing contributions) ==
target for every configuration. The synthetic species is a diagnostic forcing
harmonization device only and has no physical interpretation.

CO2 is left emissions-driven.  The V62 annual carbon pathway is used exactly:
  ON  = gross + permafrost + stored-carbon reversal - CDR
  OFF = gross + permafrost + stored-carbon reversal
Terminal component fluxes are held constant from 2184 through 2300, matching
the archived V59.1/V60 benchmark convention.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from fair import FAIR
from fair.interface import fill, initialise
from fair.io import read_properties

ROOT = Path('.')
FREP = Path(os.environ.get('FAIR_SOURCE_DIR', '/tmp/FAIR-v2.2.4'))
D = FREP / 'examples/data/calibrated_constrained_ensemble'
PAR = D / 'calibrated_constrained_parameters_calibration1.4.1.csv'
SP = D / 'species_configs_properties_calibration1.4.1.csv'
EM = D / 'extensions_1750-2500.csv'
FO = D / 'volcanic_solar.csv'
TR = ROOT / 'external_validation_net_co2_trajectory.csv'
SCENARIO = 'medium-extension'
END_YEAR = 2300
MATCH_AFTER_YEAR = 2026
MATCH_TOL = 1e-7
MAX_MATCH_ITERS = 30
BOOKKEEPING_SPECIES = 'Matched non-CO2 forcing adjustment'
MATCHED_FORCING_SCRIPT_REVISION = 'V62.1-fair-match-convergence-fix-2026-09-11'
RUNTIME_SP = ROOT / '_matched_species_configs_runtime.csv'
RUNTIME_FO = ROOT / '_matched_forcing_runtime.csv'
CONV_GTCO2_PER_PPM = 2.124 * (44.009 / 12.011)

for p in (PAR, SP, EM, FO, TR):
    if not p.exists():
        raise FileNotFoundError(p)

cfg = pd.read_csv(PAR, index_col=0)
if len(cfg) != 841:
    raise RuntimeError(f'Expected 841 FaIR configurations; found {len(cfg)}')
ids = np.asarray(cfg.index.astype(str))

can = pd.read_csv(TR).sort_values('year').reset_index(drop=True)
req = [
    'year', 'gross_co2_gtco2', 'permafrost_co2_gtco2',
    'stored_carbon_reversal_gtco2', 'cdr_gtco2', 'net_co2_gtco2'
]
missing = [c for c in req if c not in can.columns]
if missing:
    raise RuntimeError(f'Missing V62 trajectory columns: {missing}')
if int(can.year.iloc[0]) != 2026 or int(can.year.iloc[-1]) != 2183:
    raise RuntimeError('Expected V62 canonical trajectory years 2026-2183')
if can.year.duplicated().any():
    raise RuntimeError('Duplicate years in V62 trajectory')
chk = (
    can.gross_co2_gtco2 + can.permafrost_co2_gtco2
    + can.stored_carbon_reversal_gtco2 - can.cdr_gtco2
)
mass_err = float(np.max(np.abs(chk - can.net_co2_gtco2)))
if mass_err >= 1e-9:
    raise RuntimeError(f'V62 trajectory mass balance failed: {mass_err}')

last = can.iloc[-1]
LG = float(last.gross_co2_gtco2)
LP = float(last.permafrost_co2_gtco2)
LR = float(last.stored_carbon_reversal_gtco2)
LC = float(last.cdr_gtco2)
CAN_CDR = float(can.cdr_gtco2.sum())
PEAK_CDR = float(can.cdr_gtco2.max())


def carbon_paths(end=END_YEAR):
    on, off, cdr = {}, {}, {}
    for r in can.itertuples(index=False):
        y = int(r.year)
        on[y] = float(r.net_co2_gtco2)
        off[y] = float(r.gross_co2_gtco2 + r.permafrost_co2_gtco2 + r.stored_carbon_reversal_gtco2)
        cdr[y] = float(r.cdr_gtco2)
    for y in range(2184, end + 1):
        on[y] = LG + LP + LR - LC
        off[y] = LG + LP + LR
        cdr[y] = LC
    return on, off, cdr


def prepare_runtime_forcing_carrier():
    # FaIR calibration 1.4.1 has Solar and Volcanic as its only native
    # forcing-driven species. Rather than mislabel a harmonization residual as
    # either physical solar or volcanic forcing, add an explicit synthetic
    # forcing-only species. FaIR v2.2.4 explicitly permits type='unspecified'
    # with input_mode='forcing'.
    sp = pd.read_csv(SP)
    if BOOKKEEPING_SPECIES not in set(sp['name'].astype(str)):
        base = sp.loc[sp['name'] == 'Solar'].iloc[0].copy()
        base['name'] = BOOKKEEPING_SPECIES
        base['type'] = 'unspecified'
        base['input_mode'] = 'forcing'
        base['greenhouse_gas'] = 0
        base['aerosol_chemistry_from_emissions'] = 0
        base['aerosol_chemistry_from_concentration'] = 0
        base['tropospheric_adjustment'] = 0
        base['forcing_efficacy'] = 1
        base['forcing_temperature_feedback'] = 0
        base['forcing_scale'] = 1
        sp = pd.concat([sp, pd.DataFrame([base])], ignore_index=True)
    sp.to_csv(RUNTIME_SP, index=False)

    fo = pd.read_csv(FO)
    fo.columns = fo.columns.str.lower()
    if BOOKKEEPING_SPECIES not in set(fo['variable'].astype(str)):
        sel = (
            (fo['scenario'] == SCENARIO)
            & (fo['variable'] == 'Solar')
            & (fo['region'].astype(str).str.lower() == 'world')
        )
        if not bool(sel.any()):
            raise RuntimeError('Could not find Solar forcing row to template synthetic bookkeeping forcing')
        row = fo.loc[sel].iloc[0].copy()
        row['variable'] = BOOKKEEPING_SPECIES
        for col in fo.columns:
            try:
                float(col)
            except (TypeError, ValueError):
                continue
            row[col] = 0.0
        fo = pd.concat([fo, pd.DataFrame([row])], ignore_index=True)
    fo.to_csv(RUNTIME_FO, index=False)
    return RUNTIME_SP, RUNTIME_FO


def build_model(end=END_YEAR):
    runtime_sp, runtime_fo = prepare_runtime_forcing_carrier()
    f = FAIR(ch4_method='Thornhill2021')
    f.define_time(1750, end, 1)
    f.define_scenarios([SCENARIO])
    f.define_configs(cfg.index)
    species, props = read_properties(filename=runtime_sp)
    f.define_species(species, props)
    f.allocate()
    f.fill_from_csv(emissions_file=EM, forcing_file=runtime_fo)
    fill(
        f.forcing,
        f.forcing.sel(specie='Volcanic') * cfg['forcing_scale[Volcanic]'].values.squeeze(),
        specie='Volcanic',
    )
    fill(
        f.forcing,
        f.forcing.sel(specie='Solar') * cfg['forcing_scale[Solar]'].values.squeeze(),
        specie='Solar',
    )
    f.fill_species_configs(runtime_sp)
    f.override_defaults(PAR)
    initialise(f.concentration, f.species_configs['baseline_concentration'])
    initialise(f.forcing, 0)
    initialise(f.temperature, 0)
    initialise(f.cumulative_emissions, 0)
    initialise(f.airborne_emissions, 0)
    initialise(f.ocean_heat_content_change, 0)
    return f, list(species), props


def override_carbon(f, net):
    ffi = np.asarray(f.emissions.loc[dict(scenario=SCENARIO, specie='CO2 FFI')], float).copy()
    af = np.asarray(f.emissions.loc[dict(scenario=SCENARIO, specie='CO2 AFOLU')], float).copy()
    for i, tp in enumerate(np.asarray(f.timepoints, float)):
        y = int(np.floor(tp))
        if y in net:
            ffi[i, :] = net[y]
            af[i, :] = 0.0
    f.emissions.loc[dict(scenario=SCENARIO, specie='CO2 FFI')] = ffi
    f.emissions.loc[dict(scenario=SCENARIO, specie='CO2 AFOLU')] = af


def choose_adjustment_species(species, props):
    if BOOKKEEPING_SPECIES not in species:
        raise RuntimeError(f'Synthetic forcing carrier {BOOKKEEPING_SPECIES!r} is absent')
    p = props.get(BOOKKEEPING_SPECIES, {})
    if p.get('type') != 'unspecified' or p.get('input_mode') != 'forcing':
        raise RuntimeError(f'Invalid synthetic forcing-carrier properties: {p}')
    return BOOKKEEPING_SPECIES


def run_model(net, adjustment=None, adjustment_species=None):
    f, species, props = build_model()
    override_carbon(f, net)
    if adjustment is not None:
        if adjustment_species is None:
            raise ValueError('adjustment_species required when adjustment is supplied')
        arr = np.asarray(f.forcing.loc[dict(scenario=SCENARIO, specie=adjustment_species)], float).copy()
        years = np.asarray(f.timebounds, float)
        if adjustment.shape != arr.shape:
            raise RuntimeError(f'Adjustment shape {adjustment.shape} != forcing slice {arr.shape}')
        mask = years > MATCH_AFTER_YEAR
        arr[mask, :] += adjustment[mask, :]
        f.forcing.loc[dict(scenario=SCENARIO, specie=adjustment_species)] = arr
    f.run(progress=False)
    return f, species, props


def nonco2_forcing(f, species):
    non = [s for s in species if s != 'CO2']
    return np.asarray(
        f.forcing.sel(scenario=SCENARIO, specie=non).sum(dim='specie'),
        float,
    )


def co2(f):
    return np.asarray(f.concentration.loc[dict(scenario=SCENARIO, specie='CO2')], float)


def temp(f):
    return np.asarray(f.temperature.loc[dict(scenario=SCENARIO, layer=0)], float)


def q3(x):
    return [float(v) for v in np.quantile(np.asarray(x, float), [0.05, 0.5, 0.95])]


def fit_matched_case(net, target, adjustment_species):
    years = np.arange(1750, END_YEAR + 1, dtype=float)
    adjustment = np.zeros((len(years), len(cfg)), dtype=float)
    mask = years > MATCH_AFTER_YEAR
    final = None
    audit = []
    for it in range(MAX_MATCH_ITERS):
        f, species, _ = run_model(net, adjustment, adjustment_species)
        non = nonco2_forcing(f, species)
        residual = target[:, None] - non
        max_abs = float(np.max(np.abs(residual[mask, :])))
        audit.append({'iteration': it + 1, 'max_abs_nonco2_forcing_error_wm2': max_abs})
        print(
            f'  forcing-match iteration {it + 1}/{MAX_MATCH_ITERS}: '
            f'max |residual| = {max_abs:.12g} W/m2',
            flush=True,
        )
        final = (f, species, non)
        if max_abs <= MATCH_TOL:
            break
        adjustment[mask, :] += residual[mask, :]
    if final is None:
        raise RuntimeError('FaIR forcing harmonization produced no run')
    if audit[-1]['max_abs_nonco2_forcing_error_wm2'] > MATCH_TOL:
        raise RuntimeError(f'FaIR forcing harmonization failed to converge: {audit[-1]}')
    return final[0], final[1], final[2], adjustment, audit


def attribution(fon, foff, cdr):
    years = np.asarray(fon.timebounds, float)
    aa = co2(fon)
    bb = co2(foff)
    rows = []
    for i, t in enumerate(years):
        upto = int(round(t)) - 1
        cumulative = sum(v for y, v in cdr.items() if y <= upto)
        d = bb[i] - aa[i]
        frac = d * CONV_GTCO2_PER_PPM / cumulative if cumulative > 0 else np.full_like(d, np.nan)
        dq = q3(d)
        fq = q3(frac) if cumulative > 0 else [math.nan, math.nan, math.nan]
        rows.append([t, cumulative, *dq, *fq])
    return pd.DataFrame(rows, columns=[
        'year', 'cumulative_cdr_gtco2',
        'delta_co2_p05_ppm', 'delta_co2_p50_ppm', 'delta_co2_p95_ppm',
        'fraction_p05', 'fraction_p50', 'fraction_p95'
    ])


def main():
    on, off, cdr = carbon_paths()

    # First pass: define the common cross-model non-CO2 ERF target as the
    # median FaIR non-CO2 ERF under the official medium-extension background.
    baseline, species, props = run_model(off)
    adjustment_species = choose_adjustment_species(species, props)
    years = np.asarray(baseline.timebounds, float)
    baseline_non = nonco2_forcing(baseline, species)
    target = np.median(baseline_non, axis=1)

    pd.DataFrame({
        'year': years.astype(int),
        'matched_nonco2_forcing_wm2': target,
    }).query('year >= 2026').to_csv('fair_matched_nonco2_forcing.csv', index=False)

    print(f'Adjustment bookkeeping species: {adjustment_species}', flush=True)
    print('Running matched-forcing removal ON', flush=True)
    fon, son, non_on, adj_on, audit_on = fit_matched_case(on, target, adjustment_species)
    print('Running matched-forcing removal OFF', flush=True)
    foff, soff, non_off, adj_off, audit_off = fit_matched_case(off, target, adjustment_species)

    if son != soff:
        raise RuntimeError('FaIR species definitions differ across paired runs')

    mask = years > MATCH_AFTER_YEAR
    match_on = float(np.max(np.abs(non_on[mask, :] - target[mask, None])))
    match_off = float(np.max(np.abs(non_off[mask, :] - target[mask, None])))
    cross_pair_non = float(np.max(np.abs(non_on[mask, :] - non_off[mask, :])))
    i26 = int(np.argmin(np.abs(years - 2026)))
    common_co2_2026 = float(np.max(np.abs(co2(fon)[i26] - co2(foff)[i26])))
    common_temp_2026 = float(np.max(np.abs(temp(fon)[i26] - temp(foff)[i26])))

    if match_on > MATCH_TOL or match_off > MATCH_TOL or cross_pair_non > 2 * MATCH_TOL:
        raise RuntimeError('FaIR matched-forcing audit failed')
    if common_co2_2026 > 1e-6 or common_temp_2026 > 1e-6:
        raise RuntimeError('FaIR common-state 2026 audit failed')

    attr = attribution(fon, foff, cdr)
    attr.to_csv('fair_matched_attribution.csv', index=False)

    # Compact paired state envelope for downstream comparison.
    co_on, co_off = co2(fon), co2(foff)
    t_on, t_off = temp(fon), temp(foff)
    rows = []
    for i, y in enumerate(years.astype(int)):
        if y < 2026:
            continue
        rows.append({
            'year': y,
            'co2_on_p05_ppm': q3(co_on[i])[0],
            'co2_on_p50_ppm': q3(co_on[i])[1],
            'co2_on_p95_ppm': q3(co_on[i])[2],
            'co2_off_p05_ppm': q3(co_off[i])[0],
            'co2_off_p50_ppm': q3(co_off[i])[1],
            'co2_off_p95_ppm': q3(co_off[i])[2],
            'tas_on_p50_c': q3(t_on[i])[1],
            'tas_off_p50_c': q3(t_off[i])[1],
        })
    pd.DataFrame(rows).to_csv('fair_matched_timeseries.csv', index=False)

    milestones = {}
    for yy in [2040, 2100, 2156, 2184, 2200, 2300]:
        r = attr.iloc[int(np.argmin(np.abs(attr.year.to_numpy(float) - yy)))]
        milestones[str(yy)] = {
            'delta_co2_p50_ppm': float(r.delta_co2_p50_ppm),
            'response_fraction_p05': float(r.fraction_p05),
            'response_fraction_p50': float(r.fraction_p50),
            'response_fraction_p95': float(r.fraction_p95),
        }

    summary = {
        'model': 'FaIR',
        'version': '2.2.4',
        'calibration': 'fair-calibrate 1.4.1',
        'configs': 841,
        'experiment': 'V62 removal-ON/OFF with harmonized non-CO2 ERF after 2026',
        'matched_nonco2_target': 'median FaIR medium-extension non-CO2 ERF; same scalar target imposed on all FaIR configs and exported to Hector',
        'adjustment_bookkeeping_species': adjustment_species,
        'bookkeeping_warning': 'The synthetic unspecified species is only an additive forcing carrier and has no physical interpretation.',
        'match_starts': 2027,
        'canonical_cdr_2026_2183_gtco2': CAN_CDR,
        'peak_cdr_2026_2183_gtco2_per_year': PEAK_CDR,
        'trajectory_mass_balance_max_abs_gtco2': mass_err,
        'common_state_2026_co2_maxabs_ppm': common_co2_2026,
        'common_state_2026_tas_maxabs_c': common_temp_2026,
        'forcing_match_max_abs_on_wm2': match_on,
        'forcing_match_max_abs_off_wm2': match_off,
        'forcing_match_on_vs_off_max_abs_wm2': cross_pair_non,
        'forcing_match_tolerance_wm2': MATCH_TOL,
        'fit_iterations_on': audit_on,
        'fit_iterations_off': audit_off,
        'milestones': milestones,
        'interpretation_boundary': (
            'This experiment removes future non-CO2 forcing differences as a cross-model confounder. '
            'It does not force FaIR and Hector to have identical carbon-cycle parameters or identical historical carbon pools.'
        ),
    }
    Path('fair_matched_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
