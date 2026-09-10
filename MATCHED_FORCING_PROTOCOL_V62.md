# V62 matched-forcing FaIR/Hector validation protocol

## Question

Does the paired atmospheric-CO2 response to the V62 removal programme remain qualitatively and quantitatively comparable between FaIR 2.2.4 and Hector 3.5.0 after removing a known cross-model confounder: different future non-CO2 forcing backgrounds?

## Carbon experiment

Both models use the same annual V62 carbon components. Removal ON is gross anthropogenic CO2 + exported permafrost CO2 + stored-carbon reversal - deliberate CDR. Removal OFF is the identical source pathway with deliberate CDR set to zero. The terminal 2183 component fluxes are held constant through 2300, matching the archived V59.1/V60 benchmark convention.

The paired difference is always calculated as removal OFF minus removal ON. Apparent atmospheric response fraction is reported using the same 2.124 PgC/ppm conversion used in the prior FaIR/Hector comparison.

## Common non-CO2 forcing target

FaIR 2.2.4 is run with the official calibrated-constrained ensemble (fair-calibrate 1.4.1; 841 configurations) and its `medium-extension` background. At each year, the median of the ensemble's summed non-CO2 effective radiative forcing is taken as the common target.

From 2027 onward, every FaIR member is adjusted so that its summed non-CO2 forcing equals that scalar target. The adjustment is carried through one direct forcing-driven species purely as an additive bookkeeping device. The physical identity of that carrier species is not interpreted.

The same target CSV is then passed to Hector 3.5.0.

## Hector forcing harmonization

Hector retains its own CO2 concentration, CO2 radiative-forcing formulation, carbon pools, and carbon-cycle feedbacks. For each removal branch separately, Hector's total-forcing constraint is iterated until

`RF_TOTAL - RF_CO2 = common non-CO2 forcing target`

for every year 2027-2300. Thus the removal-ON and removal-OFF cases are allowed to have different CO2 forcing, while the non-CO2 forcing contribution is identical and matched to FaIR.

## State treatment

Each model preserves its own historical initialization. Within each model the ON/OFF pair must be identical through 2026; the matched forcing begins in 2027. Historical carbon pools are **not** forcibly made identical across FaIR and Hector because doing so would require artificial pool reassignment and would no longer be a clean independent-model comparison.

## Failure gates

The workflow fails if the V62 carbon trajectory does not mass-balance, if either paired branch is non-finite, if removal ON materially raises atmospheric CO2 relative to removal OFF, if the within-model common-state audit fails, or if the imposed non-CO2 forcing differs from the common target beyond the declared tolerance.

**Cross-model disagreement is not a failure gate.** If FaIR and Hector disagree after forcing harmonization, that disagreement is a scientific result to report.

## Outputs

FaIR produces the common forcing target, paired attribution, state envelope and audit JSON. Hector produces paired attribution, state/forcing audit and convergence JSON. A final comparison job reports milestone differences at 2040, 2100, 2156, 2184, 2200 and 2300 and tests whether the deterministic Hector response falls within the FaIR p05-p95 ensemble range without treating that test as pass/fail.
