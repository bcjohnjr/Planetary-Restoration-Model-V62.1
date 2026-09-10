#!/usr/bin/env python3
"""Independent OSCAR v3.3 paired validation for Planetary Restoration V62.

The V62 model is not modified. The script expects the official OSCAR v3.3 source
at --oscar-root and the V62 external-validation CO2 trajectory at --trajectory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

COMMON_CO2_PPM = 428.73
OSCAR_PIN = "3ce008400e06363564e5981a35cbc32377d41d86"
SCENARIO = "SSP2-4.5"
START_YEAR = 2027
GTCO2_PER_PGC = 44.009 / 12.011
GTCO2_PER_PPM = 2.124 * GTCO2_PER_PGC
SEED = 6201


def quantiles(values):
    a = np.asarray(values, dtype=float).reshape(-1)
    return {k: float(v) for k, v in zip(("p05", "p50", "p95"), np.quantile(a, (0.05, 0.5, 0.95)))}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_pathway(path: Path, end_year: int) -> pd.DataFrame:
    df = pd.read_csv(path).sort_values("year").reset_index(drop=True)
    required = ["year", "gross_co2_gtco2", "permafrost_co2_gtco2",
                "stored_carbon_reversal_gtco2", "cdr_gtco2", "net_co2_gtco2"]
    missing = [c for c in required if c not in df]
    if missing:
        raise RuntimeError(f"Missing trajectory columns: {missing}")
    if int(df.year.iloc[0]) != 2026 or int(df.year.iloc[-1]) != 2183:
        raise RuntimeError("Canonical V62 trajectory must span 2026..2183")
    identity = (df.gross_co2_gtco2 + df.permafrost_co2_gtco2
                + df.stored_carbon_reversal_gtco2 - df.cdr_gtco2)
    err = float(np.max(np.abs(identity - df.net_co2_gtco2)))
    if err > 1e-9:
        raise RuntimeError(f"V62 net-CO2 identity failed: {err}")

    if end_year > 2183:
        last = df.iloc[-1]
        extra = []
        for y in range(2184, end_year + 1):
            gross = float(last.gross_co2_gtco2)
            pf = float(last.permafrost_co2_gtco2)
            rev = float(last.stored_carbon_reversal_gtco2)
            cdr = float(last.cdr_gtco2)
            extra.append({"year": y, "gross_co2_gtco2": gross,
                          "permafrost_co2_gtco2": pf,
                          "stored_carbon_reversal_gtco2": rev,
                          "cdr_gtco2": cdr,
                          "net_co2_gtco2": gross + pf + rev - cdr})
        df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
    return df[df.year <= end_year].copy()


def import_oscar(root: Path):
    if not (root / "core_fct" / "mod_process.py").exists():
        raise RuntimeError(f"OSCAR source not found at {root}")
    sys.path.insert(0, str(root))
    os.chdir(root)  # OSCAR v3 loaders use repository-relative data paths.
    from core_fct.mod_process import OSCAR
    from core_fct.fct_loadP import load_all_param
    from core_fct.fct_genMC import generate_config
    from run_scripts.get_SSP_drivers import For_hist, For_scen
    return OSCAR, load_all_param, generate_config, For_hist, For_scen


def move_static_to_par(xr, par, forcing):
    static = [v for v in forcing if "year" not in forcing[v].dims]
    if static:
        par = xr.merge([par, forcing[static]])
        forcing = forcing.drop_vars(static)
    return par, forcing


def abs_co2(ds, par):
    return np.asarray((ds["D_CO2"] + par["CO2_0"]).values, dtype=float)


def zero_separate_luc(forcing):
    # V62's trajectory is the complete annual anthropogenic CO2 pathway. Separate
    # OSCAR land-use CO2 drivers are zeroed after 2026 to avoid double counting.
    for name in ("Eluc", "d_Acover", "d_Hwood", "d_Ashift"):
        if name in forcing:
            forcing[name] = 0 * forcing[name]
    return forcing


def set_global_eff(xr, forcing, totals_gtco2, reference_eff):
    totals_pgc = np.asarray(totals_gtco2, dtype=float) / GTCO2_PER_PGC
    eff = forcing["Eff"]
    other_dims = [d for d in eff.dims if d != "year"]
    if not other_dims:
        forcing["Eff"] = xr.DataArray(totals_pgc, coords={"year": forcing.year}, dims=("year",))
        return forcing

    weights = reference_eff.astype(float)
    denom = weights.sum(dim=other_dims)
    if abs(float(np.asarray(denom).squeeze())) < 1e-12:
        weights = xr.ones_like(weights)
        denom = weights.sum(dim=other_dims)
    weights = weights / denom
    new_eff = xr.concat([weights * x for x in totals_pgc], dim="year")
    new_eff = new_eff.assign_coords(year=forcing.year.values).transpose(*eff.dims)
    forcing["Eff"] = new_eff
    return forcing


def run(args) -> int:
    launch_dir = Path.cwd().resolve()
    trajectory = Path(args.trajectory)
    if not trajectory.is_absolute():
        trajectory = (launch_dir / trajectory).resolve()
    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = (launch_dir / outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    pathway = load_pathway(trajectory, args.end_year)
    canonical = pathway[pathway.year <= 2183]

    OSCAR, load_all_param, generate_config, for_hist0, for_scen0 = import_oscar(Path(args.oscar_root).resolve())
    import xarray as xr

    np.random.seed(SEED)
    par0 = load_all_param(mod_region="RCP_5reg")
    par = generate_config(par0, nMC=args.nmc)

    # Primary pathway-contract run: V62 already supplies a permafrost-CO2 source,
    # so turn off OSCAR's own frozen-carbon stock to prevent double counting.
    if "Cfroz_0" in par:
        par["Cfroz_0"] = 0 * par["Cfroz_0"]

    for_hist = for_hist0.copy(deep=True)
    par, for_hist = move_static_to_par(xr, par, for_hist)
    out_hist, ini_2014 = OSCAR(Ini=None, Par=par, For=for_hist, get_final=True, nt=4)

    scen = for_scen0.sel(scen=SCENARIO, drop=True).copy(deep=True)
    bridge = scen.sel(year=slice(2015, 2026)).copy(deep=True)
    if "D_CO2" not in bridge:
        raise RuntimeError("OSCAR bridge lacks prescribed D_CO2")
    co2_0 = float(np.asarray(par0["CO2_0"]).squeeze())
    bridge["D_CO2"].loc[dict(year=2026)] = COMMON_CO2_PPM - co2_0
    out_bridge, ini_2026 = OSCAR(Ini=ini_2014, Par=par, For=bridge, get_final=True, nt=4)
    common = quantiles(abs_co2(ini_2026, par))

    future = scen.sel(year=slice(START_YEAR, args.end_year)).copy(deep=True)
    if "D_CO2" in future:
        future = future.drop_vars("D_CO2")
    future = zero_separate_luc(future)
    years = np.asarray(future.year.values, dtype=int)
    p = pathway[pathway.year >= START_YEAR].set_index("year")
    missing = [int(y) for y in years if int(y) not in p.index]
    if missing:
        raise RuntimeError(f"Trajectory missing years: {missing[:5]}")

    on = [float(p.loc[y, "net_co2_gtco2"]) for y in years]
    off = [float(p.loc[y, "gross_co2_gtco2"] + p.loc[y, "permafrost_co2_gtco2"]
                 + p.loc[y, "stored_carbon_reversal_gtco2"]) for y in years]
    ref_eff = scen["Eff"].sel(year=2025, drop=True)
    for_on = set_global_eff(xr, future.copy(deep=True), on, ref_eff)
    for_off = set_global_eff(xr, future.copy(deep=True), off, ref_eff)
    xr.testing.assert_identical(for_on.drop_vars("Eff"), for_off.drop_vars("Eff"))

    keep = ["D_Eluc", "D_Focean", "D_Fland", "D_Epf", "D_Tg"]
    out_on, fin_on = OSCAR(Ini=ini_2026, Par=par, For=for_on, var_keep=keep,
                            get_final=True, nt=4, nt_max=48, adapt_nt=True)
    out_off, fin_off = OSCAR(Ini=ini_2026, Par=par, For=for_off, var_keep=keep,
                              get_final=True, nt=4, nt_max=48, adapt_nt=True)

    co2_on = np.squeeze(abs_co2(out_on, par))
    co2_off = np.squeeze(abs_co2(out_off, par))
    if co2_on.ndim == 1:
        co2_on, co2_off = co2_on[:, None], co2_off[:, None]
    if co2_on.shape[0] != len(years):
        raise RuntimeError(f"Unexpected D_CO2 shape {co2_on.shape}")

    cdr = pathway.set_index("year")["cdr_gtco2"].to_dict()
    cumulative = 0.0
    rows = []
    for i, y in enumerate(years):
        cumulative += float(cdr[int(y)])
        q_on, q_off = quantiles(co2_on[i]), quantiles(co2_off[i])
        q_delta = quantiles(co2_off[i] - co2_on[i])
        response = float(q_delta["p50"] * GTCO2_PER_PPM / cumulative) if cumulative > 0 else None
        rows.append({"year": int(y),
                     "co2_on_p05_ppm": q_on["p05"], "co2_on_p50_ppm": q_on["p50"], "co2_on_p95_ppm": q_on["p95"],
                     "co2_off_p05_ppm": q_off["p05"], "co2_off_p50_ppm": q_off["p50"], "co2_off_p95_ppm": q_off["p95"],
                     "delta_co2_p05_ppm": q_delta["p05"], "delta_co2_p50_ppm": q_delta["p50"], "delta_co2_p95_ppm": q_delta["p95"],
                     "cumulative_cdr_from_2027_gtco2": cumulative,
                     "median_atmospheric_response_fraction": response})
    table = pd.DataFrame(rows)
    table.to_csv(outdir / "oscar_paired_attribution.csv", index=False)

    final_on = abs_co2(fin_on, par).reshape(-1)
    final_off = abs_co2(fin_off, par).reshape(-1)
    final_delta = final_off - final_on
    total_cdr = float(pathway[pathway.year >= START_YEAR].cdr_gtco2.sum())
    final_response = float(np.median(final_delta) * GTCO2_PER_PPM / total_cdr)
    gates = {
        "trajectory_identity": True,
        "matched_nonco2_forcing": True,
        "common_state_median_within_0p05ppm": abs(common["p50"] - COMMON_CO2_PPM) <= 0.05,
        "finite_final_co2": bool(np.isfinite(final_on).all() and np.isfinite(final_off).all()),
        "removal_lowers_final_co2_median": bool(np.median(final_delta) > 0),
        "response_fraction_physical_range": bool(0 < final_response < 1.5),
    }
    passed = all(gates.values())
    selected_years = [2030, 2050, 2100, 2156, 2183, 2200, args.end_year]
    summary = {
        "status": "PASS" if passed else "FAIL",
        "experiment": "OSCAR_V3_3_PATHWAY_CONTRACT_PAIRED",
        "oscar": {"repository": "https://github.com/tgasser/OSCAR", "version": "v3.3",
                  "pinned_commit": OSCAR_PIN, "ensemble_members": args.nmc,
                  "seed": SEED, "region_scheme": "RCP_5reg"},
        "v62_input": {"trajectory_file": trajectory.name, "sha256": sha256(trajectory),
                      "canonical_years": [2026, 2183],
                      "canonical_cdr_gtco2": float(canonical.cdr_gtco2.sum()),
                      "extension": f"terminal 2183 component fluxes held constant through {args.end_year}"},
        "forcing_protocol": {
            "historical": "Official OSCAR historical drivers through 2014",
            "bridge": f"Official OSCAR {SCENARIO} 2015-2026; atmospheric CO2 pinned to 428.73 ppm at end-2026",
            "future_co2": "Emissions-driven from 2027; V62 net pathway is sole anthropogenic CO2 flux",
            "future_nonco2": f"Identical {SCENARIO} non-CO2 drivers in both branches",
            "permafrost": "OSCAR Cfroz_0 disabled because V62 net pathway already includes explicit permafrost CO2",
            "separate_land_use_co2": "OSCAR Eluc/d_Acover/d_Hwood/d_Ashift zeroed after 2026 to avoid double counting",
            "time_index": "Annual OSCAR v3.3 series are mid-year means; final_state is the end-year endpoint"
        },
        "common_state_2026_ppm": common,
        "final_end_year": args.end_year,
        "final_end_year_co2_on_ppm": quantiles(final_on),
        "final_end_year_co2_off_ppm": quantiles(final_off),
        "final_end_year_delta_co2_ppm": quantiles(final_delta),
        "final_cumulative_cdr_2027_to_end_gtco2": total_cdr,
        "final_median_atmospheric_response_fraction": final_response,
        "selected_midyear_results": table[table.year.isin(selected_years)].to_dict(orient="records"),
        "gates": gates,
        "claim_boundary": "Independent OSCAR reduced-complexity benchmark of the V62 CO2 pathway; it does not validate ecological, engineering, finance or human-service modules."
    }
    (outdir / "oscar_validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("OSCAR VALIDATION PASSED" if passed else "OSCAR VALIDATION FAILED")
    return 0 if passed else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oscar-root", required=True)
    ap.add_argument("--trajectory", default="external_validation_net_co2_trajectory.csv")
    ap.add_argument("--outdir", default="oscar_results")
    ap.add_argument("--nmc", type=int, default=200)
    ap.add_argument("--end-year", type=int, default=2300)
    return run(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
