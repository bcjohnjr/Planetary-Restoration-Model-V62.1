#!/usr/bin/env python3
"""Planetary Restoration Model V62.0 — integrated restoration + human flourishing.

This release locks the all-green Run10 FaIR/Hector carbon-cycle close-out as the
externally executed climate core and restores the wider planetary-restoration
architecture from the V59.1/V58/V55 lineage. It also adds explicit scenario
modules for AI/robotic health and legal access, and a completeness gate so named
subsystems cannot silently disappear in later revisions.

Scientific-status rule
----------------------
Every module is tagged as one of:
  EXTERNALLY_EXECUTED       direct model run / CI-verified result
  LEGACY_MECHANISTIC        retained quantitative lineage calculation
  LITERATURE_SCREEN         literature-anchored screening calculation
  ENGINEERING_SCENARIO      engineering design / mass-energy screen
  POLICY_SCENARIO           author-defined policy/finance scenario
  SERVICE_CAPACITY_SCENARIO normalized human-service capacity sensitivity
  DIAGNOSTIC_ONLY           not a publication-grade forecast

No broader module inherits FaIR/Hector calibration merely by being coupled here.
No single deterministic "planet restored by YEAR" is reported.
"""
from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

HERE = Path(__file__).resolve().parent
LEGACY_DIR = HERE
DATA_DIR = HERE
RESULTS_DIR = HERE / "results"
MODEL_VERSION = "62.0"
RELEASE_LABEL = "Integrated Planetary Restoration and Human Flourishing"
RUN10_WORKFLOW_RUN = 34289949707
RUN10_COMMIT = "3dbdcab603cf31ec16bbb2eaee4ab54b82472b17"
GTCO2_PER_PPM = 7.782459079177421


def _import_legacy():
    p = LEGACY_DIR / "planetary_restoration_model_v59_1.py"
    spec = importlib.util.spec_from_file_location("legacy_v59_1_for_v62", p)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import legacy model from {p}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


legacy = _import_legacy()


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _round(v: Any, n: int = 6) -> Any:
    if isinstance(v, float):
        return round(v, n)
    return v


def run10_climate_core() -> Dict[str, Any]:
    """Load the completed Run10 feedback and inverse outputs."""
    fair = _load_json(DATA_DIR / "fair_feedback_sensitivity_summary.json")
    hector = _load_json(DATA_DIR / "hector_feedback_sensitivity_summary.json")
    inv = pd.read_csv(DATA_DIR / "inverse_solutions.csv")
    comp = pd.read_csv(DATA_DIR / "feedback_attribution_comparison.csv")
    selected = pd.read_csv(DATA_DIR / "fair_feedback_attribution_selected.csv")

    combined = selected[selected["experiment"] == "combined_programme_effect"].copy()
    combined_rows = [
        {k: _round(v) for k, v in row.items()}
        for row in combined.to_dict(orient="records")
    ]

    return {
        "classification": "EXTERNALLY_EXECUTED",
        "workflow_status": "ALL_GREEN",
        "workflow_run_id": RUN10_WORKFLOW_RUN,
        "workflow_commit": RUN10_COMMIT,
        "faIR": {
            "model": fair["model"],
            "calibration": fair["calibration"],
            "configs": fair["configs"],
            "gtco2_per_ppm": fair["gtco2_per_ppm"],
            "canonical_cdr_2026_2183_gtco2": fair["canonical_cdr_2026_2183_gtco2"],
            "canonical_reversal_2026_2183_gtco2": fair["canonical_reversal_2026_2183_gtco2"],
            "canonical_reversal_fraction_of_cdr": fair["canonical_reversal_fraction_of_cdr"],
            "common_state_co2_maxabs_ppm_at_2026": fair["common_state_co2_maxabs_ppm_at_2026"],
            "permafrost_formulation": fair["permafrost_formulation"],
            "combined_programme_effect_selected": combined_rows,
            "legacy_2300": fair["legacy_2300"],
            "interpretation": fair["interpretation"],
        },
        "Hector": {
            "model": hector["model"],
            "version": hector["version"],
            "common_state_year": hector["common_state_year"],
            "common_state_co2_ppm": hector["common_state_co2_ppm"],
            "common_state_tas_degc": hector["common_state_tas_degc"],
            "common_state_max_co2_error_ppm": hector["common_state_max_co2_error_ppm"],
            "common_state_max_tas_error_degc": hector["common_state_max_tas_error_degc"],
            "permafrost_method": hector["permafrost_method"],
            "cumulative_exported_reversal_2026_2300_gtco2": hector["cumulative_exported_reversal_2026_2300_gtco2"],
            "cumulative_exported_permafrost_2026_2300_gtco2": hector["cumulative_exported_permafrost_2026_2300_gtco2"],
            "response_fraction_2300": hector["response_fraction_2300"],
            "delta_co2_2300_ppm": hector["delta_co2_2300_ppm"],
            "reversal_window_combined": hector["reversal_window_combined"],
            "interpretation_boundary": hector["interpretation_boundary"],
        },
        "feedback_correction_comparison": [
            {k: _round(v) for k, v in row.items()} for row in comp.to_dict(orient="records")
        ],
        "inverse": [
            {k: _round(v) for k, v in row.items()} for row in inv.to_dict(orient="records")
        ],
        "inverse_interpretation": {
            "control": "constant additional CDR after the canonical 2183 schedule through target year",
            "extra_leakage": "additional CDR carries contemporaneous stored-carbon reversal at the canonical cumulative reversal/CDR fraction",
            "median_is_not_guarantee": True,
            "deadline_result": "2200 requires substantially higher annual post-2183 CDR than 2300 or 2400; all 2200 criteria exceed the historical modeled 15.2 GtCO2/yr programme peak, whereas all 2300/2400 criteria do not.",
        },
        "limitations": [
            "FaIR and Hector do not use an identical cross-model future non-CO2 forcing architecture.",
            "OSCAR remains an open predeclared external-validation gate unless separately revised and justified.",
            "The inverse control is a constant post-2183 rate; other schedules can differ.",
            "A median 280 ppm endpoint is not a guarantee for every ensemble member.",
        ],
    }


def preserved_legacy_architecture(base: Dict[str, Any]) -> Dict[str, Any]:
    v58 = base["v59_0_full_architecture"]["v58_full_architecture"]
    active = v58["legacy_architecture_reference"]["active_recovered_modules"]
    return {
        "classification": "MIXED_LEGACY_SCREENING_ARCHITECTURE",
        "seaweed": copy.deepcopy(v58["seaweed_v58"]),
        "fisheries": copy.deepcopy(v58["fisheries_v57"]),
        "coral_reef": copy.deepcopy(v58["coral_reef_recovery_v58"]),
        "human_system_screens": copy.deepcopy(v58["restored_human_system_screens"]),
        "wastewater_food_waste_bioenergy": copy.deepcopy(active["wastewater_food_waste_bioenergy"]),
        "nutrient_loops_npk": copy.deepcopy(active["nutrient_loops_npk"]),
        "tidal_energy": copy.deepcopy(active["tidal_energy"]),
        "global_maritime": copy.deepcopy(active["global_maritime"]),
        "storage_portfolio": copy.deepcopy(active["storage_portfolio"]),
        "firm_clean_options": copy.deepcopy(active["firm_clean_options"]),
        "shock_resilience": copy.deepcopy(active["shock_resilience"]),
        "tree_wealth": copy.deepcopy(active["tree_wealth"]),
        "national_allocation": copy.deepcopy(active["national_allocation"]),
        "country_equalizer": copy.deepcopy(active["country_equalizer"]),
        "parallel_settlement": copy.deepcopy(active["parallel_settlement"]),
        "sanctions_governance": copy.deepcopy(active["sanctions_governance"]),
        "dollar_transition": copy.deepcopy(active["dollar_transition"]),
        "no_new_burden": copy.deepcopy(active["no_new_burden"]),
        "food_health_budget": copy.deepcopy(active["food_health_budget"]),
        "ai_data_center_transition": copy.deepcopy(active["ai_data_center_transition"]),
        "workforce_transition": copy.deepcopy(active["workforce_transition"]),
        "cross_border_fee": copy.deepcopy(active["cross_border_fee"]),
        "sea_level": copy.deepcopy(base["sea_level_v59_1"]),
        "surface_ocean_ph": copy.deepcopy(base["ocean_ph_v59_1"]),
        "energy_and_grid": copy.deepcopy(v58["v53_1_full_core"]["energy_and_grid"]),
        "monetary_liquidity_stress": copy.deepcopy(v58["v53_1_full_core"]["monetary_liquidity_stress"]),
        "accounting_rules": copy.deepcopy(v58["accounting_rules"]),
    }


def coral_reef_update(legacy_arch: Dict[str, Any]) -> Dict[str, Any]:
    reefs = copy.deepcopy(legacy_arch["coral_reef"])
    reefs["classification"] = "LITERATURE_SCREEN"
    reefs["observed_2026_update"] = {
        "source": "Australian Institute of Marine Science Long-Term Monitoring Program annual summary 2025-26",
        "survey_period": "August 2025-June 2026",
        "reefs_surveyed": 121,
        "hard_coral_cover_percent": {"Northern": 35.1, "Central": 31.6, "Southern": 26.4},
        "interpretation": "Early recovery is visible in Northern and Central regions after the 2024 mass-bleaching mortality, but recovery is not uniform and remains conditional on future heat stress.",
    }
    reefs["publication_boundary_v62"] = {
        "single_gbr_restoration_year_allowed": False,
        "conditional_cover_window_if_2026_starts_durable_low_disturbance_period": [2036, 2041],
        "conditional_ecological_structure_window_if_2026_starts_durable_low_disturbance_period": [2041, 2056],
        "reset_after_new_severe_bleaching": True,
        "regional_heat_stress_model_required_for_calendar_forecast": True,
    }
    return reefs


def ocean_restoration_system(legacy_arch: Dict[str, Any], reefs: Dict[str, Any]) -> Dict[str, Any]:
    seaweed = copy.deepcopy(legacy_arch["seaweed"])
    fisheries = copy.deepcopy(legacy_arch["fisheries"])
    ph = copy.deepcopy(legacy_arch["surface_ocean_ph"])
    return {
        "classification": "MIXED_LITERATURE_ENGINEERING_SCREEN",
        "coral_reefs": reefs,
        "ocean_acidification": {
            "classification": "DIAGNOSTIC_ONLY",
            "legacy_fixed_TS_screen": ph,
            "publication_rounded_minimum_ph": ph.get("publication_rounded", {}).get("minimum_surface_ph", 8.05),
            "publication_rounded_endpoint_ph_near_fair_2400": ph.get("publication_rounded", {}).get("surface_ocean_ph_at_fair_2400_timebound", 8.16),
            "temperature_coupled_carbonate_chemistry_still_required": True,
            "coral_link": "Lower carbonate availability and thermal stress are treated as separate constraints; pH recovery alone does not imply reef restoration.",
        },
        "fisheries": fisheries,
        "seaweed_bioeconomy": seaweed,
        "seaweed_required_streams": {
            "live_farm_carbon_stock": True,
            "strategic_liquid_fuel_reserve_carbon_stock": True,
            "human_food_and_protein": True,
            "edible_fish_habitat_and_coculture": True,
            "aviation_low_carbon_fuel": True,
            "heavy_equipment_low_carbon_fuel": True,
            "marine_fuel": True,
            "durable_storage_BiCRS_substitute": True,
            "materials_feedstock": True,
            "nutrient_capture_eutrophication_relief": True,
            "CSP_HTL_integration": True,
            "grid_harvesting_energy_reduction": True,
            "grid_harvesting_source": "Bily, Pahl & Valdés (2021), Physical Analysis of Seaweed Harvesting - Conventional Vessel vs. Grid Technology",
        },
        "ocean_plastic": {
            "classification": "POLICY_ENGINEERING_SCREEN",
            "objective": "Intercept, remove, sort and reuse/recycle marine plastic where technically and ecologically appropriate, including structural uses in seaweed-farm systems when material specifications permit.",
            "no_false_credit_rule": "Plastic removal is not carbon removal unless a separately verified lifecycle carbon balance supports a carbon claim.",
            "reference_context": "UNEP estimates roughly 11 million metric tonnes of plastic enter aquatic/ocean systems annually; V62 treats cleanup as a material-pollution objective independent of CDR accounting.",
        },
        "eutrophication_and_nutrients": copy.deepcopy(legacy_arch["nutrient_loops_npk"]),
        "coastal_blue_carbon": {
            "classification": "LITERATURE_SCREEN",
            "ecosystems": ["mangroves", "salt marshes", "seagrass"],
            "rule": "Count only additional, monitored, permanence-adjusted carbon; biodiversity/coastal-protection value is tracked separately from carbon tonnes.",
        },
    }


def human_flourishing_system(legacy_arch: Dict[str, Any]) -> Dict[str, Any]:
    hs = copy.deepcopy(legacy_arch["human_system_screens"])
    welfare = hs["Human_Welfare_Floor"]
    demo = hs["Demographics"]
    food_health = copy.deepcopy(legacy_arch["food_health_budget"])
    return {
        "classification": "POLICY_AND_RESOURCE_SCREEN",
        "planning_population_billion": 10.3,
        "food_and_hunger": {
            "dietary_energy_floor_kcal_person_day": 2350,
            "protein_floor_g_person_day": 50,
            "legacy_coverage_fraction": 0.99,
            "diet_scenarios_retained": [
                "optimized omnivore including meat",
                "EAT-Lancet-like mixed diet",
                "vegetarian with dairy/eggs and aquatic foods",
                "plant-forward upper-capacity screen",
            ],
            "rule": "Meat remains an allowed pathway; diet cases are scenario choices rather than moral prescriptions.",
            "seaweed_role": "nutritious supplement/protein/mineral stream subject to species, iodine, contaminant, digestibility and safe-intake constraints",
            "food_waste": "coupled to methane/energy recovery and nutrient loops",
        },
        "water_sanitation": {
            "safe_municipal_water_floor_l_person_day": 50,
            "planning_service_l_person_day": 100,
            "desalination": True,
            "wastewater_reuse": True,
            "food_waste_and_wastewater_methane_capture": copy.deepcopy(legacy_arch["wastewater_food_waste_bioenergy"]),
        },
        "universal_healthcare": {
            "resource_budget": food_health,
            "planning_infrastructure": demo.get("planning_infrastructure_at_10_3b", demo),
            "service_scope": [
                "primary care", "maternal and child health", "emergency care", "surgery", "mental health",
                "vaccination", "antibiotics and antimicrobial stewardship", "cancer prevention and treatment",
                "mRNA cancer-vaccine research and access if/when indications are proven and approved",
                "remote care", "public-health surveillance", "pharmacy and medicine logistics",
            ],
            "boundary": "The model does not assume experimental mRNA cancer vaccines are universal cures; it models R&D and equitable access as an innovation pathway.",
        },
        "housing": {
            "planning_floor_area_m2": 309e9,
            "status": "RESOURCE_SCREEN",
            "couplings": ["low-carbon cement", "steel", "aluminium", "timber", "clean power", "water", "construction robotics"],
        },
        "education": {
            "planning_teachers": 103e6,
            "services": ["universal basic education", "vocational retraining", "scholarships", "AI tutoring with human educator oversight"],
        },
        "legal_access": {
            "objective": "expand affordable access to legal information, document preparation, triage, mediation and human representation",
            "rule": "access-to-justice output is tracked separately from economic output and never treated as a climate benefit",
        },
        "workforce_transition": copy.deepcopy(legacy_arch["workforce_transition"]),
        "disaster_resilience": copy.deepcopy(legacy_arch["shock_resilience"]),
        "social_dividend_allocation_sensitivity": {
            "housing": 0.25,
            "jobs_local_enterprise": 0.20,
            "health": 0.15,
            "food": 0.10,
            "education": 0.10,
            "water_sanitation": 0.08,
            "disaster_resilience": 0.05,
            "ecosystems_biodiversity": 0.05,
            "direct_cash_emergency_relief": 0.02,
            "sum": 1.0,
            "classification": "AUTHOR_DEFINED_ALLOCATION_SENSITIVITY",
        },
    }


def ai_robotics_services() -> Dict[str, Any]:
    """Explicit robot-doctor / robot-lawyer and automation service scenarios.

    These are normalized service-capacity sensitivities, not forecasts of job replacement.
    """
    health_scenarios = []
    for name, eligible, productivity in [
        ("conservative", 0.15, 0.10),
        ("central", 0.30, 0.25),
        ("high_automation", 0.50, 0.50),
    ]:
        health_scenarios.append({
            "scenario": name,
            "routine_task_volume_eligible_for_ai_robotic_assistance_fraction": eligible,
            "assumed_systemwide_service_capacity_gain_fraction": productivity,
            "effective_capacity_multiplier": 1.0 + productivity,
            "human_clinical_oversight": "mandatory for regulated diagnosis/treatment/prescribing unless applicable law and validated safety case explicitly permit otherwise",
            "uses": ["triage", "documentation", "decision support", "remote monitoring", "pharmacy/logistics", "robotic assistance", "translation", "scheduling"],
        })
    legal_scenarios = []
    for name, routine_share in [("conservative", 0.20), ("central", 0.40), ("high_digital_access", 0.60)]:
        legal_scenarios.append({
            "scenario": name,
            "routine_legal_service_volume_eligible_for_ai_assistance_fraction": routine_share,
            "normalized_public_legal_access_capacity_index": 100.0 * (1.0 + 0.5 * routine_share),
            "human_lawyer_judge_oversight": "required for regulated legal advice, representation and adjudication where law requires; all substantive filings require verification",
            "uses": ["triage", "legal information", "research", "drafting", "form completion", "document review", "translation", "mediation support"],
        })
    return {
        "classification": "SERVICE_CAPACITY_SCENARIO",
        "robot_doctors": {
            "label": "AI-assisted and robotic healthcare / robot-doctor scenario",
            "scenarios": health_scenarios,
            "safety_governance": [
                "human oversight", "clinical validation", "bias monitoring", "privacy/data governance",
                "audit logs", "cybersecurity", "liability allocation", "fail-safe operation", "equitable access",
            ],
            "claim_boundary": "AI and robotics augment clinical teams in this screen; physician replacement is not assumed.",
        },
        "robot_lawyers": {
            "label": "AI-assisted legal access / robot-lawyer scenario",
            "scenarios": legal_scenarios,
            "safety_governance": [
                "confidentiality", "source verification", "hallucination checks", "jurisdiction control",
                "unauthorized-practice-of-law safeguards", "human responsibility for representation", "appeal and review",
            ],
            "claim_boundary": "The screen measures accessible service capacity, not autonomous replacement of licensed counsel or judges.",
        },
        "other_robotic_automation": [
            {"sector": "construction", "roles": ["prefabrication", "earthmoving", "inspection", "housing buildout"], "classification": "ENGINEERING_SCENARIO"},
            {"sector": "agriculture", "roles": ["precision weeding", "harvesting", "greenhouse operations", "food logistics"], "classification": "ENGINEERING_SCENARIO"},
            {"sector": "forestry_restoration", "roles": ["planting", "survival monitoring", "firebreak maintenance", "selective harvest"], "classification": "ENGINEERING_SCENARIO"},
            {"sector": "ocean_restoration", "roles": ["seaweed grid harvesting", "plastic interception", "reef monitoring", "fishery MRV"], "classification": "ENGINEERING_SCENARIO"},
            {"sector": "carbon_removal", "roles": ["plant operation", "sampling", "MRV", "maintenance", "geologic storage monitoring"], "classification": "ENGINEERING_SCENARIO"},
            {"sector": "education", "roles": ["AI tutoring", "translation", "adaptive practice", "teacher administration"], "classification": "SERVICE_CAPACITY_SCENARIO"},
            {"sector": "eldercare_and_disability_support", "roles": ["mobility assistance", "monitoring", "logistics", "telepresence"], "classification": "SERVICE_CAPACITY_SCENARIO"},
            {"sector": "manufacturing_and_recycling", "roles": ["sorting", "disassembly", "remanufacturing", "quality inspection"], "classification": "ENGINEERING_SCENARIO"},
            {"sector": "infrastructure_MRV", "roles": ["satellite/drone sensing", "leak detection", "tree geotagging", "biodiversity monitoring"], "classification": "ENGINEERING_SCENARIO"},
        ],
        "source_context": {
            "health": "WHO guidance treats AI as potentially valuable for health while emphasizing validation, human oversight, equity and governance.",
            "legal": "Access-to-justice and professional-ethics sources support digital assistance while requiring competence, confidentiality and verification.",
        },
    }


def cdr_portfolio() -> Dict[str, Any]:
    return {
        "classification": "INTEGRATED_PORTFOLIO_SCREEN",
        "central_programme_peak_gtco2_yr": 15.2,
        "planning_ceiling_cases_gtco2_yr": {"low": 12.0, "central": 16.0, "high": 20.0},
        "ramp_start_gtco2_yr": 2.2,
        "methods": [
            {"id": "DACCS", "role": "durable engineered removal", "energy_intensity_context": "legacy central ~2 MWh/tCO2; technology- and site-dependent"},
            {"id": "enhanced_weathering", "role": "mineral removal with soil/agronomic co-effects"},
            {"id": "ocean_alkalinity_enhancement_AWL", "role": "ocean carbonate chemistry / removal; ecological safeguards required"},
            {"id": "mineral_carbonation", "role": "durable solid carbonate storage"},
            {"id": "biochar", "role": "biogenic carbon storage and soil amendment"},
            {"id": "BiCRS", "role": "biomass carbon removal and storage"},
            {"id": "forestry_reforestation", "role": "biological stock restoration with wildfire/drought/permanence buffers"},
            {"id": "durable_wood_products_and_burial", "role": "harvest-to-durable-storage pathway with chain of custody"},
            {"id": "deep_saline_aquifer_storage", "role": "geologic storage destination with MRV"},
            {"id": "seaweed_durable_storage", "role": "marine biomass durable storage/BiCRS substitute subject to ecological and mass-balance constraints"},
            {"id": "CCU", "role": "utilization tracked separately; only durable storage duration and displacement can receive CDR credit"},
        ],
        "accounting": [
            "No carbon credits are required by the financing architecture.",
            "Removal tonnes are credited only after MRV and permanence treatment.",
            "Avoided emissions, circular materials and ecological benefits are not double-counted as CDR.",
        ],
    }


def energy_transport_materials(legacy_arch: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "classification": "MIXED_ENGINEERING_SCREEN",
        "energy_and_grid": copy.deepcopy(legacy_arch["energy_and_grid"]),
        "storage_portfolio": copy.deepcopy(legacy_arch["storage_portfolio"]),
        "tidal_energy": copy.deepcopy(legacy_arch["tidal_energy"]),
        "firm_clean_options": copy.deepcopy(legacy_arch["firm_clean_options"]),
        "nuclear_claim_boundary": "No special nuclear requirement is claimed; technology options are evaluated within adequacy/material constraints.",
        "shipping": copy.deepcopy(legacy_arch["global_maritime"]),
        "aviation_and_heavy_equipment": {
            "electric_where_feasible": True,
            "liquid_low_carbon_fuels_for_hard_to_electrify_uses": ["seaweed-derived fuels", "e-fuels", "sustainable biogenic fuels"],
            "fuel_reserve_carbon_stock_accounted_separately": True,
        },
        "distributed_AI_compute_and_heat_reuse": copy.deepcopy(legacy_arch["ai_data_center_transition"]),
        "industrial_materials": copy.deepcopy(legacy_arch["human_system_screens"]["Industry_Materials"]),
        "circularity": ["steel", "cement/binder", "aluminium", "plastics", "timber", "electronics", "battery materials"],
        "waste_heat": {
            "uses": ["district heat", "hot water", "greenhouses", "aquaculture", "industrial low-temperature heat"],
            "Los_Jardines_Cella_archetype": True,
        },
    }


def carbonite_financing(climate: Dict[str, Any], legacy_arch: Dict[str, Any]) -> Dict[str, Any]:
    inv = pd.DataFrame(climate["inverse"])
    abs_med = inv[inv["criterion"] == "absolute_280_median"].sort_values("target_year")

    mature_gdp_tn = 309.0  # legacy planning normalization from resource-budget layer
    settlement_envelope_fraction_gdp = 0.0214
    adoption_shares = [1.00, 0.90, 0.75, 0.50]
    cdr_cost_cases = [100, 200, 400]
    rows: List[Dict[str, Any]] = []
    for adoption in adoption_shares:
        envelope = mature_gdp_tn * settlement_envelope_fraction_gdp * adoption
        for _, r in abs_med.iterrows():
            rate = float(r["total_post2183_cdr_rate_gtco2_yr"])
            for cost in cdr_cost_cases:
                annual_cost_tn = rate * cost / 1000.0
                rows.append({
                    "settlement_adoption_share": adoption,
                    "target_year": int(r["target_year"]),
                    "criterion": "absolute_280_median",
                    "total_post2183_cdr_gtco2_yr": rate,
                    "illustrative_cdr_unit_cost_usd_per_tco2": cost,
                    "annual_cdr_cost_usd_tn": annual_cost_tn,
                    "gross_settlement_revenue_envelope_usd_tn": envelope,
                    "cdr_cost_share_of_envelope": annual_cost_tn / envelope if envelope else None,
                    "within_gross_envelope": annual_cost_tn <= envelope,
                })

    us_nonparticipation = {
        "classification": "POLICY_STRESS_SCENARIO_NOT_FORECAST",
        "description": "User-requested stress case in which United States settlement flows do not participate while other participating jurisdictions continue.",
        "treatment": "Do not infer geopolitical outcome; map it onto adoption-share sensitivities and recompute financing capacity rather than assuming 'little consequence'.",
    }

    return {
        "classification": "POLICY_FINANCE_SCENARIO",
        "name": "Carbonite",
        "instrument": "price-stable settlement cryptocurrency / stablecoin",
        "purpose": "redirect a portion of settlement/intermediation revenue into a treaty-governed global restoration charity while providing settlement utility",
        "restoration_charity": True,
        "global_adoption_required_for_full_central_envelope": True,
        "no_carbon_credits": True,
        "proof_of_rent": {
            "name": "Proof of Rent (PoR)",
            "concept": "network resource/consensus mechanism based on renting processor capacity to the network rather than proof-of-work hash expenditure",
            "terminology_rule": "Use Processor / Prospective Processor Power, not Hash / Hash Power, in the PoR architecture.",
        },
        "tree_value_anchor": {
            "geotagged_trees": True,
            "timber_value_component": True,
            "measured_biomass_growth_component": True,
            "value_growth_vs_inflation": "scenario sensitivity, not guaranteed outperformance",
            "automatic_money_creation_from_tree_growth": False,
            "permanence_pool_fraction_range": [0.10, 0.20],
            "wildfire_drought_buffer": True,
            "chain_of_custody": True,
        },
        "fee_architecture": {
            "legacy_settlement_envelope_fraction_mature_gdp": settlement_envelope_fraction_gdp,
            "protected_basic_food_payments_fee_free": True,
            "protected_basic_health_payments_fee_free": True,
            "cross_border_fee_module": copy.deepcopy(legacy_arch["cross_border_fee"]),
            "country_equalizer": copy.deepcopy(legacy_arch["country_equalizer"]),
            "parallel_settlement": copy.deepcopy(legacy_arch["parallel_settlement"]),
            "liquidity_stress": copy.deepcopy(legacy_arch["monetary_liquidity_stress"]),
            "bank_transition": copy.deepcopy(legacy_arch["ai_data_center_transition"].get("current_bank_screen", {})),
            "workforce_transition": copy.deepcopy(legacy_arch["workforce_transition"]),
        },
        "governance": {
            "sanctions": copy.deepcopy(legacy_arch["sanctions_governance"]),
            "national_allocation": copy.deepcopy(legacy_arch["national_allocation"]),
            "dollar_transition_context": copy.deepcopy(legacy_arch["dollar_transition"]),
            "US_nonparticipation_stress": us_nonparticipation,
        },
        "financeability_screen": rows,
        "financeability_boundary": (
            "This screen compares transparent unit-cost cases with a gross settlement revenue envelope. "
            "It is not a proof that all settlement revenue is available for CDR, does not include every capital bottleneck, "
            "and does not establish incidence-neutrality. The 2200 deadline is especially demanding."
        ),
    }


def module_registry() -> List[Dict[str, str]]:
    rows = [
        ("climate_gross_emissions", "Climate", "Gross anthropogenic CO2 emissions pathway", "LEGACY_MECHANISTIC"),
        ("climate_cdr_schedule", "Climate", "Canonical CDR schedule and post-2183 controls", "EXTERNALLY_EXECUTED"),
        ("fair_paired_attribution", "Climate", "FaIR paired removal-on/off attribution", "EXTERNALLY_EXECUTED"),
        ("hector_paired_attribution", "Climate", "Hector paired programme-feedback comparator", "EXTERNALLY_EXECUTED"),
        ("inverse_fair_targets", "Climate", "Inverse FaIR 2200/2300/2400 target solves", "EXTERNALLY_EXECUTED"),
        ("stored_carbon_reversal", "Climate", "Programme-contingent stored-carbon reversal", "EXTERNALLY_EXECUTED"),
        ("dynamic_permafrost", "Climate", "Temperature-responsive permafrost feedback", "EXTERNALLY_EXECUTED"),
        ("nonco2_forcing", "Climate", "Non-CO2 forcing sensitivity/background", "DIAGNOSTIC_ONLY"),
        ("temperature_response", "Climate", "Temperature response / target-year diagnostics", "EXTERNALLY_EXECUTED"),
        ("sea_level", "Cryosphere/Ocean", "Sea-level persistence screen", "LITERATURE_SCREEN"),
        ("ice_melt", "Cryosphere/Ocean", "Glacier/ice-sheet lag represented through sea-level context", "LITERATURE_SCREEN"),
        ("ocean_ph", "Ocean", "Surface-ocean pH / acidification screen", "DIAGNOSTIC_ONLY"),
        ("coral_reefs", "Ocean/Biodiversity", "Coral survival, cover and ecological recovery clocks", "LITERATURE_SCREEN"),
        ("fisheries", "Ocean/Food", "Wild fish-stock rebuilding screen", "LITERATURE_SCREEN"),
        ("seaweed_live_carbon", "Ocean/CDR", "Standing live seaweed farm carbon stock", "ENGINEERING_SCENARIO"),
        ("seaweed_fuel_reserve_carbon", "Ocean/Energy", "Strategic seaweed-derived fuel reserve carbon stock", "ENGINEERING_SCENARIO"),
        ("seaweed_food", "Ocean/Food", "Edible seaweed and protein/mineral stream", "ENGINEERING_SCENARIO"),
        ("seaweed_fish_habitat", "Ocean/Biodiversity", "Managed fish habitat/co-culture services", "ENGINEERING_SCENARIO"),
        ("seaweed_grid_harvesting", "Ocean/Engineering", "Grid Harvesting energy-reduction concept", "ENGINEERING_SCENARIO"),
        ("seaweed_aviation_fuel", "Energy/Aviation", "Seaweed liquid fuels for aviation", "ENGINEERING_SCENARIO"),
        ("seaweed_heavy_equipment_fuel", "Energy/Industry", "Seaweed liquid fuels for heavy equipment", "ENGINEERING_SCENARIO"),
        ("seaweed_marine_fuel", "Energy/Shipping", "Seaweed liquid fuels for marine use", "ENGINEERING_SCENARIO"),
        ("seaweed_CSP_HTL", "Energy/Industry", "Concentrated-solar + HTL integration", "ENGINEERING_SCENARIO"),
        ("ocean_plastic_cleanup", "Ocean/Pollution", "Ocean plastic interception/removal/reuse", "POLICY_SCENARIO"),
        ("eutrophication", "Water/Ocean", "Nutrient capture and eutrophication relief", "LEGACY_MECHANISTIC"),
        ("blue_carbon", "Ocean/Biodiversity", "Mangrove/marsh/seagrass restoration", "LITERATURE_SCREEN"),
        ("DACCS", "CDR", "Direct air capture with storage", "ENGINEERING_SCENARIO"),
        ("enhanced_weathering", "CDR/Land", "Enhanced rock weathering", "ENGINEERING_SCENARIO"),
        ("OAE_AWL", "CDR/Ocean", "Ocean alkalinity enhancement / accelerated weathering of limestone", "ENGINEERING_SCENARIO"),
        ("mineral_carbonation", "CDR/Materials", "Mineral carbonation", "ENGINEERING_SCENARIO"),
        ("biochar", "CDR/Land", "Biochar carbon storage", "ENGINEERING_SCENARIO"),
        ("BiCRS", "CDR", "Biomass carbon removal and storage", "ENGINEERING_SCENARIO"),
        ("saline_aquifer_storage", "CDR/Geology", "Deep saline aquifer storage", "ENGINEERING_SCENARIO"),
        ("CCU", "CDR/Industry", "Carbon utilization accounting", "ENGINEERING_SCENARIO"),
        ("forest_restoration", "Land/CDR", "Tree planting, growth and ecological restoration", "LEGACY_MECHANISTIC"),
        ("tree_harvest_durable_storage", "Land/CDR", "Strategic harvest/use/burial/durable wood", "POLICY_SCENARIO"),
        ("wildfire_permanence", "Land/Risk", "Wildfire/drought permanence risk", "POLICY_SCENARIO"),
        ("soil_emissions_carbon", "Land", "Soil emissions/carbon response", "LEGACY_MECHANISTIC"),
        ("regenerative_agriculture", "Land/Food", "Soil/agronomic restoration pathway", "POLICY_SCENARIO"),
        ("food_diet_omnivore", "Food", "Optimized omnivore pathway including meat", "LITERATURE_SCREEN"),
        ("food_diet_mixed", "Food", "Mixed/EAT-Lancet-like pathway", "LITERATURE_SCREEN"),
        ("food_diet_vegetarian_aquatic", "Food", "Vegetarian + dairy/eggs + aquatic foods", "LITERATURE_SCREEN"),
        ("hunger_elimination", "Food/Human", "Dietary energy/protein access floor", "POLICY_SCENARIO"),
        ("food_waste", "Food/Waste", "Food-waste recovery", "LEGACY_MECHANISTIC"),
        ("wastewater_methane", "Water/Energy", "Wastewater methane capture and energy", "LEGACY_MECHANISTIC"),
        ("desalination", "Water", "Clean-water desalination", "ENGINEERING_SCENARIO"),
        ("water_reuse", "Water", "Wastewater treatment/reuse", "ENGINEERING_SCENARIO"),
        ("universal_healthcare", "Human/Health", "Universal basic health-care resource envelope", "POLICY_SCENARIO"),
        ("vaccines_antibiotics", "Human/Health", "Vaccination, antibiotics and stewardship access", "POLICY_SCENARIO"),
        ("mrna_cancer_vaccine_pipeline", "Human/Health", "mRNA cancer-vaccine R&D/access if validated/approved", "POLICY_SCENARIO"),
        ("robot_doctors", "AI/Health", "AI-assisted and robotic healthcare", "SERVICE_CAPACITY_SCENARIO"),
        ("robot_lawyers", "AI/Justice", "AI-assisted legal access", "SERVICE_CAPACITY_SCENARIO"),
        ("legal_access", "Human/Justice", "Affordable legal information/representation access", "POLICY_SCENARIO"),
        ("education", "Human/Education", "Universal education and vocational training", "POLICY_SCENARIO"),
        ("robot_tutors", "AI/Education", "AI tutoring with educator oversight", "SERVICE_CAPACITY_SCENARIO"),
        ("housing", "Human/Housing", "Housing resource/buildout screen", "POLICY_SCENARIO"),
        ("robot_construction", "AI/Infrastructure", "Construction automation", "ENGINEERING_SCENARIO"),
        ("robot_agriculture", "AI/Food", "Agricultural robotics", "ENGINEERING_SCENARIO"),
        ("robot_environmental_mrv", "AI/MRV", "Robotic/satellite/drone MRV", "ENGINEERING_SCENARIO"),
        ("robot_ocean_cleanup", "AI/Ocean", "Robotic ocean restoration/cleanup", "ENGINEERING_SCENARIO"),
        ("robot_eldercare", "AI/Health", "Robotic eldercare/disability assistance", "SERVICE_CAPACITY_SCENARIO"),
        ("energy_grid", "Energy", "Electricity, grid adequacy and storage", "LEGACY_MECHANISTIC"),
        ("tidal_energy", "Energy", "Tidal-energy screen", "ENGINEERING_SCENARIO"),
        ("shipping_decarbonization", "Transport", "Shipping efficiency/wind/battery/H2/e-fuel/biofuel portfolio", "ENGINEERING_SCENARIO"),
        ("aviation_decarbonization", "Transport", "Aviation electrification where feasible + low-carbon liquid fuel", "ENGINEERING_SCENARIO"),
        ("industrial_materials", "Materials", "Steel/cement/aluminium/circularity", "LEGACY_MECHANISTIC"),
        ("data_center_heat_reuse", "Energy/AI", "Distributed AI data-center waste-heat reuse", "ENGINEERING_SCENARIO"),
        ("Los_Jardines_Cella", "Implementation", "Eight-town distributed restoration/AI demonstration archetype", "ENGINEERING_SCENARIO"),
        ("Carbonite_stablecoin", "Finance", "Carbonite price-stable settlement cryptocurrency", "POLICY_SCENARIO"),
        ("Proof_of_Rent", "Finance/Compute", "Proof of Rent processor-rental mechanism", "POLICY_SCENARIO"),
        ("geotagged_tree_reserve", "Finance/Forestry", "Geotagged tree/timber natural-capital reserve", "POLICY_SCENARIO"),
        ("restoration_charity", "Finance/Human", "Global restoration charity funded by settlement fees", "POLICY_SCENARIO"),
        ("transaction_fee_finance", "Finance", "Settlement/cross-border fee funding", "POLICY_SCENARIO"),
        ("country_equalizer", "Finance/Governance", "Equalizer for differing domestic restoration potential", "POLICY_SCENARIO"),
        ("bank_transition", "Finance", "Bank/data-center/project-finance transition", "POLICY_SCENARIO"),
        ("liquidity_stress", "Finance", "Monetary liquidity/reserve stress", "LEGACY_MECHANISTIC"),
        ("sanctions_governance", "Governance", "Treaty sanctions/governance modes", "POLICY_SCENARIO"),
        ("US_nonparticipation_stress", "Governance/Finance", "US non-participation adoption stress case", "POLICY_SCENARIO"),
        ("protected_food_health_payments", "Finance/Human", "Basic food/health payments protected fee-free", "POLICY_SCENARIO"),
        ("workforce_transition", "Human/Economy", "Financial/industrial workforce transition", "POLICY_SCENARIO"),
        ("disaster_resilience", "Human/Risk", "Drought/shock resilience", "POLICY_SCENARIO"),
        ("Africa_vulnerability_priority", "Regional", "Africa-focused vulnerability/resource-access reporting", "LITERATURE_SCREEN"),
        ("population_scenarios", "Human/Demography", "Population planning and carrying-capacity screens", "LITERATURE_SCREEN"),
        ("MRV_audit_chain", "Governance/MRV", "Measurement, reporting, verification and chain of custody", "POLICY_SCENARIO"),
        ("no_carbon_credit_finance", "Finance", "Financing architecture independent of carbon credits", "POLICY_SCENARIO"),
    ]
    return [
        {"module_id": a, "domain": b, "module": c, "classification": d}
        for a, b, c, d in rows
    ]


REQUIRED_MODULE_IDS = {
    "coral_reefs", "robot_doctors", "robot_lawyers", "Carbonite_stablecoin", "Proof_of_Rent",
    "seaweed_grid_harvesting", "seaweed_aviation_fuel", "seaweed_heavy_equipment_fuel",
    "seaweed_live_carbon", "seaweed_fuel_reserve_carbon", "seaweed_food", "seaweed_fish_habitat",
    "fisheries", "ocean_plastic_cleanup", "ocean_ph", "sea_level", "ice_melt", "hunger_elimination",
    "universal_healthcare", "vaccines_antibiotics", "mrna_cancer_vaccine_pipeline", "legal_access",
    "desalination", "water_reuse", "eutrophication", "forest_restoration", "wildfire_permanence",
    "soil_emissions_carbon", "DACCS", "enhanced_weathering", "OAE_AWL", "mineral_carbonation",
    "biochar", "BiCRS", "saline_aquifer_storage", "CCU", "shipping_decarbonization",
    "aviation_decarbonization", "tidal_energy", "data_center_heat_reuse", "Los_Jardines_Cella",
    "food_diet_omnivore", "population_scenarios", "transaction_fee_finance", "restoration_charity",
    "no_carbon_credit_finance", "MRV_audit_chain", "workforce_transition",
}


def restoration_milestones(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    inv = pd.DataFrame(result["climate_core"]["inverse"])
    med = inv[inv.criterion == "absolute_280_median"].sort_values("target_year")
    rows: List[Dict[str, Any]] = []
    for _, r in med.iterrows():
        rows.append({
            "system": "Atmospheric CO2",
            "milestone": f"FaIR ensemble-median 280 ppm target in {int(r.target_year)}",
            "calendar": int(r.target_year),
            "condition": f"Total post-2183 CDR {r.total_post2183_cdr_rate_gtco2_yr:.3f} GtCO2/yr under Run10 inverse assumptions",
            "status": "EXTERNALLY_EXECUTED_INVERSE",
        })
    rows += [
        {"system": "Coral reefs", "milestone": "Hard-coral-cover re-establishment", "calendar": "2036-2041 only if 2026 starts a durable low-disturbance window", "condition": "No severe resetting heat event; regional heat-stress gate required", "status": "CONDITIONAL_LITERATURE_SCREEN"},
        {"system": "Coral reefs", "milestone": "Ecological/community/structural recovery", "calendar": "2041-2056 only under same hypothetical safe start", "condition": "Longer biological recovery and no severe resetting disturbance", "status": "CONDITIONAL_LITERATURE_SCREEN"},
        {"system": "Fisheries", "milestone": "Typical managed stock rebuilding", "calendar": "~10 years after effective reform (median legacy literature screen)", "condition": "Effective management, habitat, enforcement and stock-specific biology", "status": "LITERATURE_SCREEN_NOT_GLOBAL_FORECAST"},
        {"system": "Ocean pH", "milestone": "Recovery toward higher pH", "calendar": "coupled to CO2 decline; no publication-grade threshold year", "condition": "Temperature-coupled carbonate chemistry required", "status": "DIAGNOSTIC_ONLY"},
        {"system": "Human flourishing", "milestone": "Food/health/water/legal access", "calendar": "policy/deployment dependent; no single physical restoration date", "condition": "financing, governance, workforce and infrastructure adoption", "status": "POLICY_SCENARIO"},
    ]
    return rows


def run_v62() -> Dict[str, Any]:
    base = legacy.run_v59_1()
    climate = run10_climate_core()
    legacy_arch = preserved_legacy_architecture(base)
    reefs = coral_reef_update(legacy_arch)
    human = human_flourishing_system(legacy_arch)
    robotics = ai_robotics_services()
    cdr = cdr_portfolio()
    oceans = ocean_restoration_system(legacy_arch, reefs)
    energy = energy_transport_materials(legacy_arch)
    finance = carbonite_financing(climate, legacy_arch)
    registry = module_registry()

    result: Dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "release_label": RELEASE_LABEL,
        "release_date": "2026-09-09",
        "classification": "INTEGRATED_COUPLED_SCREENING_FRAMEWORK_WITH_EXTERNALLY_EXECUTED_CLIMATE_CORE",
        "headline": {
            "run10_all_green": True,
            "run10_workflow_run": RUN10_WORKFLOW_RUN,
            "faIR_configs": 841,
            "canonical_cdr_2026_2183_gtco2": climate["faIR"]["canonical_cdr_2026_2183_gtco2"],
            "canonical_stored_reversal_2026_2183_gtco2": climate["faIR"]["canonical_reversal_2026_2183_gtco2"],
            "faIR_combined_response_fraction_2300": next(x for x in climate["faIR"]["combined_programme_effect_selected"] if int(x["timebound_year"]) == 2300)["fraction_p50"],
            "Hector_combined_response_fraction_2300": climate["Hector"]["response_fraction_2300"]["combined_programme_effect"],
            "single_planetary_restoration_year": None,
            "reason_no_single_year": "Atmospheric, cryosphere, reef, fishery, pollution, infrastructure and human-service systems have different state variables, lags, thresholds and governance dependencies.",
        },
        "climate_core": climate,
        "cdr_portfolio": cdr,
        "oceans_biodiversity": oceans,
        "land_forestry": {
            "tree_wealth": copy.deepcopy(legacy_arch["tree_wealth"]),
            "forestry_rule": "plant, protect, monitor, strategically harvest where ecologically appropriate, route carbon to durable products/storage, maintain wildfire/drought permanence buffers",
            "soil_emissions_and_carbon": "retained from legacy land/carbon accounting; no extra carbon credit without explicit additionality",
            "MRV": ["geotagging", "remote sensing", "field audit", "growth measurement", "fire/drought reversal accounting"],
        },
        "energy_transport_materials": energy,
        "human_flourishing": human,
        "ai_robotics_services": robotics,
        "finance_governance": finance,
        "module_registry": registry,
        "legacy_preserved_architecture": legacy_arch,
        "accounting_and_claim_rules": [
            "Externally executed climate results and broader screening modules are never assigned the same evidentiary status by default.",
            "Avoided emissions, CDR, ecosystem recovery, pollution cleanup and social services remain separate ledgers.",
            "Cultured fish or seaweed habitat are not counted as wild fish-stock recovery.",
            "Ocean plastic cleanup is not counted as CDR without a verified lifecycle carbon basis.",
            "Tree-value growth does not automatically create money supply.",
            "Carbonite financing does not require carbon credits.",
            "Robot-doctor and robot-lawyer modules model assisted service capacity with human oversight, not automatic professional replacement.",
            "No single deterministic date is reported for restoration of the whole planet.",
        ],
        "open_science_gates": [
            "OSCAR execution or explicit justified revision of that predeclared gate",
            "matched cross-model future non-CO2 forcing protocol if exact FaIR/Hector comparison is claimed",
            "temperature-coupled carbonate chemistry for publication-grade ocean-pH threshold timing",
            "regional marine heatwave / Degree Heating Week coupling before a Great Barrier Reef restoration year is claimed",
            "financeability rerun with technology-specific CDR cost curves, capital turnover, deployment rates and incidence",
            "external validation of AI/robotic health and legal-service productivity assumptions before claiming realized capacity gains",
        ],
    }
    result["restoration_milestones"] = restoration_milestones(result)
    return result


def completeness_check(result: Dict[str, Any]) -> Dict[str, Any]:
    ids = {r["module_id"] for r in result["module_registry"]}
    missing = sorted(REQUIRED_MODULE_IDS - ids)
    return {
        "required_count": len(REQUIRED_MODULE_IDS),
        "registry_count": len(ids),
        "missing": missing,
        "pass": not missing,
    }


def run_tests(result: Dict[str, Any]) -> None:
    cc = result["climate_core"]
    assert cc["workflow_status"] == "ALL_GREEN"
    assert cc["faIR"]["configs"] == 841
    assert abs(cc["faIR"]["gtco2_per_ppm"] - GTCO2_PER_PPM) < 1e-12
    comp = {(x["model"], int(x["year"])): x for x in cc["feedback_correction_comparison"]}
    assert 7.0 < comp[("FaIR 2.2.4", 2300)]["relative_reduction_percent"] < 9.0
    assert 8.0 < comp[("Hector 3.5.0", 2300)]["relative_reduction_percent"] < 10.0
    inv = pd.DataFrame(cc["inverse"])
    a2200 = inv[(inv.target_year == 2200) & (inv.criterion == "absolute_280_median")].iloc[0]
    a2300 = inv[(inv.target_year == 2300) & (inv.criterion == "absolute_280_median")].iloc[0]
    a2400 = inv[(inv.target_year == 2400) & (inv.criterion == "absolute_280_median")].iloc[0]
    assert a2200.total_post2183_cdr_rate_gtco2_yr > 15.2
    assert a2300.total_post2183_cdr_rate_gtco2_yr < 15.2
    assert a2400.total_post2183_cdr_rate_gtco2_yr < 15.2
    assert result["oceans_biodiversity"]["seaweed_required_streams"]["grid_harvesting_energy_reduction"] is True
    assert result["finance_governance"]["proof_of_rent"]["name"] == "Proof of Rent (PoR)"
    assert result["finance_governance"]["no_carbon_credits"] is True
    assert result["ai_robotics_services"]["robot_doctors"]["scenarios"]
    assert result["ai_robotics_services"]["robot_lawyers"]["scenarios"]
    check = completeness_check(result)
    assert check["pass"], f"Missing required modules: {check['missing']}"
    assert result["headline"]["single_planetary_restoration_year"] is None


def write_outputs(result: Dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result2 = copy.deepcopy(result)
    # The full legacy architecture is reproducible in legacy_v60; keep the main JSON focused.
    result2["legacy_preserved_architecture"] = {
        "location": "repository root (flattened runtime lineage)",
        "status": "FULL_LINEAGE_INCLUDED_IN_PACKAGE",
        "selected_integrations_present_in_main_result": True,
    }
    with (RESULTS_DIR / "planetary_restoration_v62_results.json").open("w", encoding="utf-8") as f:
        json.dump(result2, f, indent=2, ensure_ascii=False, allow_nan=False)
    pd.DataFrame(result["module_registry"]).to_csv(RESULTS_DIR / "v62_module_registry.csv", index=False)
    pd.DataFrame(result["restoration_milestones"]).to_csv(RESULTS_DIR / "v62_restoration_milestones.csv", index=False)
    pd.DataFrame(result["finance_governance"]["financeability_screen"]).to_csv(RESULTS_DIR / "v62_finance_stress.csv", index=False)
    pd.DataFrame(result["ai_robotics_services"]["robot_doctors"]["scenarios"]).to_csv(RESULTS_DIR / "v62_robot_doctor_scenarios.csv", index=False)
    pd.DataFrame(result["ai_robotics_services"]["robot_lawyers"]["scenarios"]).to_csv(RESULTS_DIR / "v62_robot_lawyer_scenarios.csv", index=False)
    with (RESULTS_DIR / "v62_completeness_gate.json").open("w", encoding="utf-8") as f:
        json.dump(completeness_check(result), f, indent=2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    result = run_v62()
    run_tests(result)
    if not args.no_write:
        write_outputs(result)
    if args.tests:
        c = completeness_check(result)
        print(f"V62 TESTS PASSED — {c['registry_count']} modules, {c['required_count']} mandatory completeness checks")
    print(json.dumps(result["headline"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
