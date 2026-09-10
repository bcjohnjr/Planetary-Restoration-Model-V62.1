# OSCAR external-validation protocol for Planetary Restoration V62

## Purpose
This workload adds an independent OSCAR carbon-cycle benchmark without modifying the V62 model or allowing OSCAR validation to spill over onto ecological, engineering, financial, or human-service modules.

## Model and reproducibility
The scientific benchmark uses the public OSCAR v3.3 source at pinned commit `3ce008400e06363564e5981a35cbc32377d41d86`. OSCAR v4 is currently a beta/active-development line; the pinned v3.3 source is used here for a reproducible benchmark and because v3.3 incorporates AR6-era temperature-response and greenhouse-gas forcing updates.

## Paired experiment
1. Run OSCAR historical drivers through 2014.
2. Bridge 2015–2026 with OSCAR SSP2-4.5 non-CO2 drivers.
3. Pin atmospheric CO2 to the V62 observational common-state anchor of 428.73 ppm at end-2026.
4. From 2027 onward, remove prescribed CO2 concentration so OSCAR is emissions-driven for CO2.
5. **Removal ON:** inject `net_co2_gtco2` from the V62 external-validation trajectory.
6. **Removal OFF:** inject `gross_co2_gtco2 + permafrost_co2_gtco2 + stored_carbon_reversal_gtco2` from the same trajectory.
7. Hold every non-CO2 driver identical between ON and OFF.
8. Hold the terminal 2183 gross/permafrost/reversal/CDR component fluxes constant through 2300, matching the transparent extension convention used in the locked FaIR workload.

## Double-counting controls
The V62 trajectory contract already contains an explicit permafrost CO2 source and is the complete annual anthropogenic CO2 pathway supplied to external models. Therefore the primary OSCAR pathway-contract experiment sets OSCAR's endogenous frozen-carbon stock (`Cfroz_0`) to zero and zeros separate post-2026 OSCAR land-use CO2 drivers (`Eluc`, `d_Acover`, `d_Hwood`, `d_Ashift`). This prevents those sources from being counted once in V62's supplied pathway and again internally by OSCAR.

A later structural-sensitivity experiment may deliberately retain OSCAR endogenous permafrost while removing V62's explicit permafrost term from the injected flux. That is a different experiment and should be reported separately rather than mixed with the pathway-contract benchmark.

## Outputs
The action writes `oscar_validation_summary.json` and `oscar_paired_attribution.csv`, including p05/p50/p95 CO2 concentrations for the removal-on and removal-off branches, the atmospheric concentration difference, cumulative CDR, and median atmospheric response fraction.

## Pass gates
The workload fails if the V62 CO2 mass-balance identity is broken, the paired non-CO2 forcing differs, the common-state median misses 428.73 ppm by more than 0.05 ppm, final values are non-finite, removal fails to reduce median final CO2, or the final response fraction falls outside a broad physical sanity range.

## Claim boundary
A green OSCAR job is evidence that an independent reduced-complexity Earth-system model responds consistently to the V62 CO2 pathway under this documented forcing protocol. It is not validation of every module in V62 and does not create a single deterministic planetary-restoration year.
