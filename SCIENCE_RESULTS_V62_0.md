# Science results - V62.0

## 1. Run10 carbon-cycle close-out

The current externally executed core is GitHub Actions run 34289949707 (all five jobs green) on commit 3dbdcab603cf31ec16bbb2eaee4ab54b82472b17.

### Corrected programme-feedback attribution

The paired quantity is calculated member-by-member as `CO2(removal off) - CO2(removal on)`. Therefore a larger delta means a larger atmospheric CO2 reduction attributable to deliberate CDR.

| Model / year | Legacy delta CO2 (ppm) | Corrected combined delta CO2 (ppm) | Reduction vs legacy | Legacy response fraction | Corrected response fraction |
|---|---:|---:|---:|---:|---:|
| FaIR 2300 | 104.032 | 95.836 | 7.88% | 0.3083 | 0.2840 |
| FaIR 2400 | 114.852 | 103.239 | 10.11% | 0.2835 | 0.2548 |
| Hector 2300 | 82.392 | 75.069 | 8.89% | 0.2437 | 0.2220 |

The correction matters but does not reverse the qualitative result: atmospheric attribution per cumulative tonne declines during deep drawdown as the carbon-cycle state changes.

### Inverse FaIR restoration requirement

| Target | Criterion | Extra post-2183 CDR | Total post-2183 CDR | Cumulative extra CDR | Endpoint CO2 p50 | Endpoint CO2 p90 | Exceeds 15.2 GtCO2/yr historical modeled peak? |
|---:|---|---:|---:|---:|---:|---:|---|
| 2200 | absolute 280 median | 27.3125 | 32.5879 | 437.0 | 279.992 | 282.541 | YES |
| 2200 | absolute 280 p90 | 29.7500 | 35.0254 | 476.0 | 277.336 | 279.992 | YES |
| 2300 | absolute 280 median | 4.3672 | 9.6426 | 506.594 | 279.990 | 283.349 | NO |
| 2300 | absolute 280 p90 | 5.0625 | 10.3379 | 587.25 | 276.546 | 279.982 | NO |
| 2400 | absolute 280 median | 1.7852 | 7.0606 | 385.594 | 279.997 | 283.333 | NO |
| 2400 | absolute 280 p90 | 2.2227 | 7.4981 | 480.094 | 276.614 | 279.991 | NO |

A restoration objective therefore requires both a concentration definition and a deadline. The 2200 deadline is a substantially more demanding deployment problem than 2300 or 2400.

## 2. Oceans and coral reefs

V62 retains the legacy pH, fishery, seaweed and reef modules but explicitly separates their status from the externally executed carbon core. The 2026 AIMS Long-Term Monitoring Program surveyed 121 Great Barrier Reef sites; region-wide hard-coral cover was 35.1% Northern, 31.6% Central and 26.4% Southern. AIMS interpreted 2026 as the beginning of recovery from the 2024 mass-bleaching impacts in parts of the Reef, while emphasizing continuing climate dependence.

The reef module retains the literature/authority screen that reefs usually require roughly 10-15 years of minimal disturbance to re-establish. Thus, *only if* 2026 were the start of a durable low-disturbance interval, the model places hard-coral-cover re-establishment around 2036-2041 and broader ecological/community/structural recovery around 2041-2056. These clocks reset or extend after severe bleaching. A regional heat-stress model is still required before publishing a calendar restoration forecast.

## 3. Human flourishing and AI/robotics

V62 explicitly represents food/hunger, safe water, universal healthcare, housing, education, legal access and workforce transition. It adds robot-doctor and robot-lawyer service-capacity sensitivities. These are not professional-replacement forecasts. WHO guidance supports potentially broad AI use in healthcare but stresses evidence, safety, equity and governance; access-to-justice research similarly identifies opportunities for digital tools alongside implementation and rights risks.

The robot-doctor central sensitivity assumes 30% of routine task volume is eligible for AI/robotic assistance and uses a deliberately transparent 25% systemwide service-capacity gain sensitivity. The robot-lawyer central sensitivity assumes 40% of routine legal-service volume is eligible for AI assistance and maps this to a normalized public-access capacity index of 120. Both assumptions are author-defined and require empirical validation before policy use.

## 4. Carbonite financeability stress

The Carbonite module is a price-stable settlement cryptocurrency/stablecoin policy scenario whose proposed transaction/settlement revenue supports a global restoration charity. It uses Proof of Rent (PoR) terminology based on processor rental, not proof-of-work hash expenditure; preserves geotagged tree/timber-value accounting with permanence buffers; protects basic food and health payments from the modeled fee; and does not require carbon credits.

The new finance screen compares Run10 absolute-280 median annual CDR requirements with transparent CDR unit-cost sensitivities of US$100, 200 and 400 per tonne and adoption shares of 100%, 90%, 75% and 50%. This is a stress test rather than a cost forecast. At the legacy mature-GDP normalization of US$309 trillion and 2.14% gross settlement-envelope share, 100% adoption yields a US$6.613 trillion gross annual envelope. At US$200/tCO2, the 2200 median target consumes about US$6.518 trillion/yr (98.6% of that gross envelope), whereas 2300 uses about US$1.929 trillion and 2400 about US$1.412 trillion. At 90% adoption, the 2200 US$200/tCO2 case exceeds the gross envelope. This reinforces the physical result that an aggressive 2200 restoration deadline is much more constraining.

## 5. No single restoration date

V62 intentionally reports a milestone vector rather than one date. Atmospheric CO2 can be inverse-solved under specified controls; sea level can remain elevated long after atmospheric recovery; coral reefs require disturbance-free biological windows; fisheries depend on stock-specific management; plastics require material-flow intervention; and food, healthcare, water and justice depend on institutions and infrastructure. A single year would collapse unlike state variables into a misleading headline.
