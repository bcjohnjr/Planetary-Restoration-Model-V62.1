# Planetary Restoration Model V62.0

## Integrated planetary restoration and human flourishing

V62.0 is a new integrated release built on the full V60/V59.1 lineage and the all-green Run10 referee close-out. It deliberately separates evidentiary status: the FaIR/Hector carbon-cycle core is externally executed and CI-verified, while ecological, engineering, finance, human-services and AI/robotics components are literature screens, engineering scenarios or policy sensitivities unless explicitly stated otherwise.

### Run10 locked climate core

GitHub Actions workflow run **34289949707** at commit **3dbdcab603cf31ec16bbb2eaee4ab54b82472b17** completed successfully with all five jobs green: FaIR programme-feedback sensitivity, FaIR inverse targets 2200/2300/2400, and Hector programme-feedback sensitivity.

Key corrected results retained in V62.0:
- FaIR 2.2.4 / fair-calibrate 1.4.1, 841 configurations.
- 2026-2183 canonical deliberate CDR: 2,013.8807 GtCO2.
- Canonical stored-carbon reversal: 83.4038 GtCO2 (4.14145% of cumulative CDR).
- Corrected combined programme-effect FaIR response fraction: 0.395 at 2156, 0.354 at timebound 2184, 0.340 at 2200, 0.284 at 2300 and 0.255 at 2400.
- Hector combined programme-effect response fraction at 2300: 0.222.
- The combined feedback corrections reduce attributable delta-CO2 versus the legacy strict pair by about 7.88% in FaIR at 2300, 10.11% in FaIR at 2400, and 8.89% in Hector at 2300.
- Inverse FaIR absolute-280 median total post-2183 CDR: 32.588 GtCO2/yr for 2200, 9.643 for 2300 and 7.061 for 2400. The 2200 case exceeds the modeled historical programme peak of 15.2 GtCO2/yr; 2300 and 2400 do not.

### What V62 restores and adds

The earlier V59.1 paper intentionally froze the main-paper scope around carbon-cycle closure. V62.0 restores the wider architecture and makes it explicit in the executable model. The registry contains **85 named modules** and the test suite includes **48 mandatory completeness checks**. These include coral reefs; ocean acidification; sea-level and ice-melt persistence; fisheries; ocean plastic; eutrophication; seaweed live carbon, strategic fuel reserves, food, fish habitat, Grid Harvesting, aviation/heavy-equipment/marine fuels and CSP/HTL; forestry, soil, wildfire and geotagged trees; DACCS, enhanced weathering, OAE/AWL, mineral carbonation, biochar, BiCRS, saline aquifers and CCU; energy, storage, tidal, shipping, aviation and data-center heat reuse; food, hunger, water, healthcare, vaccines/antibiotics, cancer-vaccine innovation pathways, housing, education and legal access; robot doctors, robot lawyers and other robotics; Carbonite, Proof of Rent, the restoration charity, transaction-fee finance, country equalization, bank/workforce transition, sanctions/governance and partial-adoption stress cases.

### Claim boundary

V62.0 is an integrated screening and planning framework, not a full Earth-system model and not a forecast that every represented intervention will occur. A module does not inherit FaIR/Hector validation by being coupled to the framework. There is deliberately **no single planetary restoration year**: atmospheric CO2, sea level, coral reefs, fisheries, pollution, infrastructure and human welfare have different state variables and lags.

### Running the model

From the package root:

```bash
python planetary_restoration_model_v62.py --tests
```

or

```bash
./RUN_TESTS.sh
```

The model writes its current structured results to `results/`.

### Manuscript

The manuscript is `manuscript/Financing_simultaneous_planetary_restoration_and_human_flourishing.docx`. The document itself intentionally carries no V62 label in the title, consistent with submission formatting. It presents the Run10 result as the strongest quantitative core and the wider planetary/human architecture as an explicitly classified coupled systems framework.

### GitHub true-flat package note
This GitHub-ready issue vendors every runtime dependency and validation input at the repository root. It does not require a `legacy_v60/` or `data/run10/` directory to execute. Fresh outputs are still generated into `results/` during a run.
