#!/usr/bin/env python3
"""Planetary Restoration Model V54 — seaweed bioeconomy integration.

V54 preserves the validated V53.1 carbon/climate/finance architecture and adds an
explicit seaweed bioeconomy module covering:
  * the user-developed grid/drone harvesting architecture previously screened in v18–v20;
  * edible seaweed production;
  * macroalgae-to-liquid-fuel conversion for aviation/heavy equipment/marine use;
  * concentrated-solar HTL process heat/electricity;
  * strategic low-carbon fuel reserves and standing-farm carbon stocks;
  * durable seaweed-biomass storage as a substitute feedstock for the existing BiCRS allocation;
  * habitat footprint and an explicitly non-credited edible-aquatic-food co-culture screen.

Important accounting boundary
-----------------------------
V53.1's endogenous transition is technology-neutral and already forces aviation/shipping
and other energy sectors down toward residual floors. Therefore V54's PRIMARY case treats
seaweed fuel as an implementation pathway *inside* that transition and does not add its
full avoided-fossil CO2 again. An explicit 50% and 100% "additionality" sensitivity is
reported separately to show what happens only if the seaweed fuel displacement was not
already represented by the V53.1 transition trajectory.

Strategic fuel inventories and standing crop biomass are reported as carbon stocks, not
as durable CDR. Durable seaweed storage is reported as a potential substitute within the
existing BiCRS/durable-biomass CDR allocation, not stacked on top of the CDR headline.
"""
from __future__ import annotations

import argparse
import csv
import json
import hashlib
import math
import os
import shutil
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import planetary_restoration_model_v53_1 as v53

MODEL_VERSION = "54.0"
RELEASE_LABEL = "Planetary Restoration Model Version 54.0 — Seaweed Bioeconomy Integrated"

@dataclass(frozen=True)
class GridHarvesterInputs:
    # v19 physical central case recovered from the earlier integrated workbook.
    wet_throughput_t_h: float = 100.0
    dry_matter_fraction: float = 0.125
    availability: float = 0.75
    total_operating_power_kw: float = 133.74406270551114
    specific_electricity_kwh_wet_t: float = 1.3374406270551114
    specific_electricity_kwh_dry_t: float = 10.69952501644089
    annual_dry_harvest_t_unit: float = 82125.0
    capex_usd_m_unit: float = 7.5
    annual_total_unit_cost_usd_m: float = 2.0363295344550694
    harvest_cost_usd_dry_t: float = 24.79548900401911
    reference_conventional_harvest_cost_usd_dry_t: float = 52.25
    bankable_efficiency_factor_vs_conventional: float = 3.0
    engineering_upper_proxy_factor: float = 3.782477990172189

@dataclass(frozen=True)
class SeaweedBioeconomyInputs:
    # V53.1 physical seaweed footprint/yield is retained as the central production case.
    area_mkm2: float = 0.586
    dry_yield_t_ha_yr: float = 25.0
    dry_biomass_carbon_fraction: float = 0.30
    deployment_start_year: int = 2027
    deployment_maturity_year: int = 2045

    # Biomass allocation; sums to 1.00.
    edible_food_share: float = 0.05
    liquid_fuel_feedstock_share: float = 0.80
    durable_storage_share: float = 0.10
    materials_feed_share: float = 0.05

    # HTL/upgrading screen inherited from the earlier Seaweed_SAF/CSP_HTL work.
    finished_liquid_fuel_yield_mass_fraction: float = 0.17
    finished_fuel_lhv_mj_kg: float = 43.0
    aviation_fuel_share: float = 0.70
    heavy_equipment_fuel_share: float = 0.25
    marine_other_fuel_share: float = 0.05
    fossil_fuel_co2_kg_per_kg: float = 3.153  # hydrocarbon combustion-equivalent screen
    lifecycle_ghg_reduction_fraction: float = 0.70

    # v18 central process energy after grid-harvester improvement = 1452.148 TWh-eq for
    # 1.852624 Gt dry fuel feedstock. Scale linearly in this global screening model.
    v18_reference_fuel_feedstock_gt_dry_yr: float = 1.8526241882352943
    v18_reference_external_process_energy_twh_eq_yr: float = 1452.1481266666665
    direct_solar_heat_share: float = 0.3925465838509317
    electric_h2_share: float = 0.6074534161490683

    # Food screen (same conservative central values as earlier Seaweed_Food worksheet).
    edible_dry_protein_fraction: float = 0.10
    edible_dry_kcal_kg: float = 2000.0
    planning_population_billion: float = 10.3
    reference_daily_diet_kcal: float = 2350.0

    # Standing crop + strategic reserve are temporary/working carbon stocks, not durable CDR.
    crop_cycle_years: float = 0.75
    strategic_reserve_years_of_mature_fuel_output: float = 2.0
    strategic_reserve_build_years: int = 20

    # Durable fraction is allowed to substitute into existing BiCRS, avoiding double count.
    durable_storage_carbon_retention_fraction: float = 0.90

    # Habitat/co-culture screen. This is NOT credited to the core food/fish headline.
    habitat_eligible_area_fraction: float = 1.0
    coculture_edible_aquatic_yield_t_ha_yr: float = 0.50

    # External aviation energy benchmark from the earlier Seaweed_SAF sheet.
    global_aviation_fuel_energy_twh_yr: float = 3755.5555555555557

    # 2026 seaweed-aquaculture ecosystem-services meta-analysis medians. These are
    # EXTERNAL BENCHMARKS ONLY because values are highly site- and method-specific.
    ecosystem_median_net_mitigation_kgc_ha_yr: float = 384.0
    ecosystem_median_burial_export_kgc_ha_yr: float = 725.0
    ecosystem_median_biomass_accumulation_kgc_ha_yr: float = 1546.0
    ecosystem_median_n_removal_kg_ha_yr: float = 83.0
    ecosystem_median_p_removal_kg_ha_yr: float = 23.0


def _assert_allocations(p: SeaweedBioeconomyInputs) -> None:
    total = p.edible_food_share + p.liquid_fuel_feedstock_share + p.durable_storage_share + p.materials_feed_share
    if abs(total - 1.0) > 1e-12:
        raise ValueError(f"Seaweed biomass allocation shares must sum to 1.0, got {total}")
    fs = p.aviation_fuel_share + p.heavy_equipment_fuel_share + p.marine_other_fuel_share
    if abs(fs - 1.0) > 1e-12:
        raise ValueError(f"Fuel allocation shares must sum to 1.0, got {fs}")


def deployment_fraction(year: int, p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> float:
    if year < p.deployment_start_year:
        return 0.0
    if year >= p.deployment_maturity_year:
        return 1.0
    return (year - p.deployment_start_year) / (p.deployment_maturity_year - p.deployment_start_year)


def grid_harvester(total_dry_biomass_gt_yr: float, h: GridHarvesterInputs = GridHarvesterInputs()) -> Dict:
    dry_t = total_dry_biomass_gt_yr * 1e9
    fleet = dry_t / h.annual_dry_harvest_t_unit
    grid_elec_twh = dry_t * h.specific_electricity_kwh_dry_t / 1e9
    # The earlier v18/v19 model deliberately used 3x as the bankable central factor;
    # 3.782x is retained only as an engineering-upper movement-proxy bound.
    conventional_specific = h.specific_electricity_kwh_dry_t * h.bankable_efficiency_factor_vs_conventional
    conventional_twh = dry_t * conventional_specific / 1e9
    grid_cost_bn = dry_t * h.harvest_cost_usd_dry_t / 1e9
    reference_cost_bn = dry_t * h.reference_conventional_harvest_cost_usd_dry_t / 1e9
    return {
        "model_status": "PHYSICAL_ENGINEERING_SCREEN_WITH_PROTOTYPE_VALIDATION_REQUIRED",
        "wet_throughput_t_h": h.wet_throughput_t_h,
        "specific_electricity_kwh_wet_t": h.specific_electricity_kwh_wet_t,
        "specific_electricity_kwh_dry_t": h.specific_electricity_kwh_dry_t,
        "bankable_efficiency_factor_vs_conventional": h.bankable_efficiency_factor_vs_conventional,
        "engineering_upper_proxy_factor": h.engineering_upper_proxy_factor,
        "annual_dry_harvest_t_per_unit": h.annual_dry_harvest_t_unit,
        "required_global_fleet_units": fleet,
        "global_harvest_electricity_twh_yr": grid_elec_twh,
        "conventional_proxy_harvest_electricity_twh_yr": conventional_twh,
        "harvest_electricity_saved_vs_conventional_proxy_twh_yr": conventional_twh - grid_elec_twh,
        "harvest_propulsion_energy_reduction_fraction_vs_3x_proxy": 1.0 - 1.0/h.bankable_efficiency_factor_vs_conventional,
        "global_fleet_capex_usd_bn": fleet * h.capex_usd_m_unit / 1000.0,
        "grid_harvest_cost_usd_bn_yr": grid_cost_bn,
        "reference_conventional_harvest_cost_usd_bn_yr": reference_cost_bn,
        "harvest_cost_saving_usd_bn_yr": reference_cost_bn - grid_cost_bn,
        "central_harvest_cost_usd_dry_t": h.harvest_cost_usd_dry_t,
        "reference_harvest_cost_usd_dry_t": h.reference_conventional_harvest_cost_usd_dry_t,
        "caution": "The original CV-vs-Grid movement arithmetic was not a joule balance and its 3-kn/5.5-t/h pumping figures were inconsistent. V19 replaced that with a 100 wet-t/h pump/drag/cutter screen. The 3.0x central factor is therefore a derated engineering screen, not a measured prototype ratio.",
    }


def seaweed_bioeconomy(p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> Dict:
    _assert_allocations(p)
    production_gt = p.area_mkm2 * 1e6 * 100.0 * p.dry_yield_t_ha_yr / 1e9
    food_gt = production_gt * p.edible_food_share
    fuel_feed_gt = production_gt * p.liquid_fuel_feedstock_share
    durable_gt = production_gt * p.durable_storage_share
    materials_gt = production_gt * p.materials_feed_share

    finished_fuel_mt = fuel_feed_gt * 1000.0 * p.finished_liquid_fuel_yield_mass_fraction
    fuel_energy_twh = finished_fuel_mt * 1e9 * p.finished_fuel_lhv_mj_kg / 3.6e9
    aviation_twh = fuel_energy_twh * p.aviation_fuel_share
    heavy_twh = fuel_energy_twh * p.heavy_equipment_fuel_share
    marine_twh = fuel_energy_twh * p.marine_other_fuel_share
    fossil_equiv_gtco2 = finished_fuel_mt * p.fossil_fuel_co2_kg_per_kg / 1000.0
    avoided_gtco2 = fossil_equiv_gtco2 * p.lifecycle_ghg_reduction_fraction

    process_energy_per_gt = p.v18_reference_external_process_energy_twh_eq_yr / p.v18_reference_fuel_feedstock_gt_dry_yr
    process_twh_eq = fuel_feed_gt * process_energy_per_gt
    solar_heat_twh = process_twh_eq * p.direct_solar_heat_share
    process_electric_h2_twh = process_twh_eq * p.electric_h2_share

    food_mt = food_gt * 1000.0
    protein_mt = food_mt * p.edible_dry_protein_fraction
    kcal_day = food_mt * 1e9 * p.edible_dry_kcal_kg / (p.planning_population_billion * 1e9 * 365.0)
    protein_g_day = protein_mt * 1e12 / (p.planning_population_billion * 1e9 * 365.0)
    full_diet_person_equiv_million = (food_mt * 1e9 * p.edible_dry_kcal_kg) / (p.reference_daily_diet_kcal * 365.0) / 1e6

    # Average standing crop under linear grow-out = annual harvest * crop-cycle / 2.
    standing_dry_gt = production_gt * p.crop_cycle_years / 2.0
    standing_stock_gtco2 = standing_dry_gt * p.dry_biomass_carbon_fraction * (44.0/12.0)
    fuel_carbon_stock_gtco2_per_year_output = finished_fuel_mt * p.fossil_fuel_co2_kg_per_kg / 1000.0
    reserve_stock_gtco2 = fuel_carbon_stock_gtco2_per_year_output * p.strategic_reserve_years_of_mature_fuel_output

    durable_storage_gtco2_yr = durable_gt * p.dry_biomass_carbon_fraction * (44.0/12.0) * p.durable_storage_carbon_retention_fraction
    # Existing V53 BiCRS net intensity uses 0.5 C × 0.90 retained × 44/12 = 1.6488 tCO2/t dry land biomass.
    bicrs_land_biomass_net_tco2_t = 0.50 * 0.90 * (44.0/12.0)
    land_biomass_displaced_gt_yr = durable_storage_gtco2_yr / bicrs_land_biomass_net_tco2_t
    # V53 central assumes 50% of BiCRS biomass is dedicated and 15 dry t/ha/yr.
    dedicated_land_relief_mha = land_biomass_displaced_gt_yr * 0.50 * 1000.0 / 15.0

    habitat_km2 = p.area_mkm2 * 1e6 * p.habitat_eligible_area_fraction
    habitat_ha = habitat_km2 * 100.0
    coculture_mt = habitat_ha * p.coculture_edible_aquatic_yield_t_ha_yr / 1e6

    # External literature benchmark only; do not add to primary CDR or fish results.
    ecos_net_gtco2_yr = habitat_ha * p.ecosystem_median_net_mitigation_kgc_ha_yr * (44.0/12.0) / 1e12
    ecos_burial_gtco2_yr = habitat_ha * p.ecosystem_median_burial_export_kgc_ha_yr * (44.0/12.0) / 1e12
    ecos_biomass_accum_gtco2_yr = habitat_ha * p.ecosystem_median_biomass_accumulation_kgc_ha_yr * (44.0/12.0) / 1e12
    ecos_n_mt_yr = habitat_ha * p.ecosystem_median_n_removal_kg_ha_yr / 1e9
    ecos_p_mt_yr = habitat_ha * p.ecosystem_median_p_removal_kg_ha_yr / 1e9

    h = grid_harvester(production_gt)
    return {
        "classification": "Integrated global seaweed bioeconomy screen. Fuel/food/grid-harvester quantities are engineering scenarios; habitat co-benefits are context-dependent and are not credited to the core fish-recovery result.",
        "area_mkm2": p.area_mkm2,
        "area_km2": p.area_mkm2 * 1e6,
        "dry_yield_t_ha_yr": p.dry_yield_t_ha_yr,
        "total_dry_biomass_gt_yr": production_gt,
        "biomass_allocations_gt_dry_yr": {
            "edible_food": food_gt,
            "liquid_fuel_feedstock": fuel_feed_gt,
            "durable_storage": durable_gt,
            "materials_feed": materials_gt,
        },
        "food": {
            "food_grade_dry_seaweed_mt_yr": food_mt,
            "protein_mt_yr": protein_mt,
            "protein_g_person_day_at_10p3b": protein_g_day,
            "food_energy_kcal_person_day_at_10p3b": kcal_day,
            "full_diet_calorie_equivalent_million_people": full_diet_person_equiv_million,
            "caution": "Seaweed is treated as a nutrient/protein/calorie supplement; species, iodine, metals, processing and regional dietary safety prevent treating all biomass as unrestricted human food.",
        },
        "liquid_fuels": {
            "finished_fuel_mt_yr": finished_fuel_mt,
            "finished_fuel_energy_twh_yr": fuel_energy_twh,
            "aviation_energy_twh_yr": aviation_twh,
            "aviation_share_of_earlier_global_fuel_benchmark": aviation_twh / p.global_aviation_fuel_energy_twh_yr,
            "heavy_equipment_energy_twh_yr": heavy_twh,
            "marine_other_energy_twh_yr": marine_twh,
            "fossil_combustion_co2_equivalent_gtco2_yr": fossil_equiv_gtco2,
            "potential_lifecycle_avoided_fossil_gtco2_yr": avoided_gtco2,
            "lifecycle_reduction_assumption_fraction": p.lifecycle_ghg_reduction_fraction,
            "accounting_boundary": "Potential displacement only. Primary V54 does not add this abatement on top of the technology-neutral V53 transition; 50%/100% additionality are separate sensitivities.",
        },
        "process_energy": {
            "external_process_energy_twh_eq_yr": process_twh_eq,
            "direct_concentrated_solar_heat_twh_th_yr": solar_heat_twh,
            "electricity_plus_hydrogen_twh_e_yr": process_electric_h2_twh,
            "all_electric_counterfactual_twh_eq_yr": process_twh_eq,
            "grid_electricity_equivalent_avoided_by_direct_solar_heat_twh_yr": solar_heat_twh,
            "caution": "Scaled from the earlier v18 HTL/CSP global screen; detailed macroalgae process simulation remains required.",
        },
        "carbon_stocks": {
            "average_standing_farm_dry_biomass_gt": standing_dry_gt,
            "average_standing_farm_carbon_stock_gtco2_equivalent": standing_stock_gtco2,
            "strategic_fuel_reserve_target_gtco2_equivalent": reserve_stock_gtco2,
            "strategic_fuel_reserve_years_of_output": p.strategic_reserve_years_of_mature_fuel_output,
            "combined_working_stock_gtco2_equivalent": standing_stock_gtco2 + reserve_stock_gtco2,
            "durable_seaweed_storage_gtco2_yr": durable_storage_gtco2_yr,
            "durable_storage_accounting": "Substitutes into the existing BiCRS/durable-biomass CDR allocation; it is not added to the V53 total CDR target.",
            "land_biomass_displaced_from_bicrs_gt_dry_yr": land_biomass_displaced_gt_yr,
            "central_dedicated_land_relief_mha": dedicated_land_relief_mha,
            "working_stock_caution": "Standing crop and strategic fuel reserves are temporary/working stocks, not permanent CDR. If harvested/burned or reserve inventories are drawn down, their carbon returns unless replaced.",
        },
        "nutrient_balance": v53.seaweed(),
        "habitat": {
            "farm_habitat_footprint_km2": habitat_km2,
            "farm_habitat_footprint_million_km2": habitat_km2 / 1e6,
            "illustrative_coculture_edible_aquatic_product_mt_yr": coculture_mt,
            "coculture_yield_assumption_t_ha_yr": p.coculture_edible_aquatic_yield_t_ha_yr,
            "status": "SCENARIO_SCREEN_NOT_CREDITED_TO_CORE_FISH_RECOVERY",
            "caution": "Published evidence on habitat/biodiversity enhancement is mixed and site-specific; farm area is physical habitat structure, but increased edible fish production is not assumed as a core result.",
        },
        "external_ecosystem_services_benchmark": {
            "status": "EXTERNAL_BENCHMARK_NOT_CREDITED_TO_PRIMARY_RESULTS",
            "median_net_mitigation_gtco2_yr_if_scaled_to_full_area": ecos_net_gtco2_yr,
            "median_burial_or_deep_export_gtco2_yr_if_scaled_to_full_area": ecos_burial_gtco2_yr,
            "median_biomass_accumulation_gtco2_yr_if_scaled_to_full_area": ecos_biomass_accum_gtco2_yr,
            "median_n_removal_mt_yr_if_scaled_to_full_area": ecos_n_mt_yr,
            "median_p_removal_mt_yr_if_scaled_to_full_area": ecos_p_mt_yr,
            "caution": "2026 meta-analysis medians are highly context-specific. They are shown as a plausibility benchmark only and are not stacked onto V54 CDR, nutrient or fish outputs.",
        },
        "grid_harvester": h,
        "inputs": asdict(p),
    }


def seaweed_parameter_sensitivity() -> List[Dict]:
    cases = [
        ("conservative", 15.0, 0.12, 0.50),
        ("central", 25.0, 0.17, 0.70),
        ("high_productivity", 33.3, 0.20, 0.85),
    ]
    rows=[]
    for name,dy,fy,lca in cases:
        p=SeaweedBioeconomyInputs(dry_yield_t_ha_yr=dy, finished_liquid_fuel_yield_mass_fraction=fy, lifecycle_ghg_reduction_fraction=lca)
        r=seaweed_bioeconomy(p)
        rows.append({
            "case":name,
            "dry_yield_t_ha_yr":dy,
            "finished_fuel_yield_mass_fraction":fy,
            "lifecycle_ghg_reduction_fraction":lca,
            "dry_biomass_gt_yr":r["total_dry_biomass_gt_yr"],
            "finished_fuel_mt_yr":r["liquid_fuels"]["finished_fuel_mt_yr"],
            "finished_fuel_energy_twh_yr":r["liquid_fuels"]["finished_fuel_energy_twh_yr"],
            "aviation_energy_twh_yr":r["liquid_fuels"]["aviation_energy_twh_yr"],
            "aviation_benchmark_share":r["liquid_fuels"]["aviation_share_of_earlier_global_fuel_benchmark"],
            "heavy_equipment_energy_twh_yr":r["liquid_fuels"]["heavy_equipment_energy_twh_yr"],
            "potential_lifecycle_avoided_fossil_gtco2_yr":r["liquid_fuels"]["potential_lifecycle_avoided_fossil_gtco2_yr"],
            "grid_harvest_electricity_twh_yr":r["grid_harvester"]["global_harvest_electricity_twh_yr"],
            "grid_harvest_saving_twh_yr":r["grid_harvester"]["harvest_electricity_saved_vs_conventional_proxy_twh_yr"],
        })
    return rows


def food_allocation_sensitivity() -> List[Dict]:
    """Trade-off screen between direct human food and fuel allocation.

    The first three cases retain 10% durable storage and 5% materials/feed; fuel receives
    the residual. The all-food row is a theoretical nutritional ceiling, not a proposed diet.
    """
    base=SeaweedBioeconomyInputs()
    cases=[
        ("central_5pct_food",0.05,0.80,0.10,0.05),
        ("food_priority_20pct",0.20,0.65,0.10,0.05),
        ("food_emergency_50pct",0.50,0.35,0.10,0.05),
        ("all_food_theoretical_ceiling",1.00,0.00,0.00,0.00),
    ]
    rows=[]
    for name,food,fuel,durable,mat in cases:
        p=SeaweedBioeconomyInputs(edible_food_share=food, liquid_fuel_feedstock_share=fuel, durable_storage_share=durable, materials_feed_share=mat)
        r=seaweed_bioeconomy(p)
        rows.append({
            "case":name,
            "food_share":food,
            "fuel_share":fuel,
            "durable_storage_share":durable,
            "materials_feed_share":mat,
            "food_grade_dry_seaweed_mt_yr":r["food"]["food_grade_dry_seaweed_mt_yr"],
            "protein_mt_yr":r["food"]["protein_mt_yr"],
            "protein_g_person_day_at_10p3b":r["food"]["protein_g_person_day_at_10p3b"],
            "food_energy_kcal_person_day_at_10p3b":r["food"]["food_energy_kcal_person_day_at_10p3b"],
            "full_diet_calorie_equivalent_million_people":r["food"]["full_diet_calorie_equivalent_million_people"],
            "finished_fuel_energy_twh_yr":r["liquid_fuels"]["finished_fuel_energy_twh_yr"],
            "aviation_energy_twh_yr":r["liquid_fuels"]["aviation_energy_twh_yr"],
            "heavy_equipment_energy_twh_yr":r["liquid_fuels"]["heavy_equipment_energy_twh_yr"],
            "caution":"Calorie equivalents are capacity metrics, not a recommendation that people subsist on seaweed. Species selection, iodine, arsenic/heavy metals, digestibility and processing constrain safe human intake.",
        })
    return rows


def habitat_coculture_sensitivity() -> List[Dict]:
    rows=[]
    for y in (0.25,0.50,1.00):
        p=SeaweedBioeconomyInputs(coculture_edible_aquatic_yield_t_ha_yr=y)
        r=seaweed_bioeconomy(p)
        rows.append({
            "coculture_yield_t_ha_yr":y,
            "farm_habitat_footprint_km2":r["habitat"]["farm_habitat_footprint_km2"],
            "illustrative_edible_aquatic_product_mt_yr":r["habitat"]["illustrative_coculture_edible_aquatic_product_mt_yr"],
            "status":"SCENARIO_SCREEN_NOT_CREDITED_TO_CORE_FISH_RECOVERY",
        })
    return rows


def strategic_reserve_stock_gtco2(year: int, p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> float:
    """Strategic fuel inventory, physically capped by cumulative produced fuel.

    The desired inventory rises linearly over ``strategic_reserve_build_years``, but
    each year's addition cannot exceed that year's gross finished-fuel production.
    This prevents the reserve-build screen from allocating more fuel to storage than
    the seaweed system actually produces during early deployment.
    """
    if year < p.deployment_start_year:
        return 0.0
    mature=seaweed_bioeconomy(p)
    target=mature["carbon_stocks"]["strategic_fuel_reserve_target_gtco2_equivalent"]
    annual_mature_fuel_carbon=mature["liquid_fuels"]["fossil_combustion_co2_equivalent_gtco2_yr"]
    stock=0.0
    for y in range(p.deployment_start_year, year+1):
        schedule=min(1.0,(y-p.deployment_start_year+1)/float(p.strategic_reserve_build_years))
        desired_stock=target*schedule
        gross_available=annual_mature_fuel_carbon*deployment_fraction(y,p)
        add=min(max(0.0,desired_stock-stock),gross_available)
        stock=min(target,stock+add)
    return stock


def reserve_stock_fraction(year: int, p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> float:
    target=seaweed_bioeconomy(p)["carbon_stocks"]["strategic_fuel_reserve_target_gtco2_equivalent"]
    return 0.0 if target<=0 else strategic_reserve_stock_gtco2(year,p)/target


def working_stock_gtco2(year: int, p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> float:
    mature = seaweed_bioeconomy(p)["carbon_stocks"]
    stand = mature["average_standing_farm_carbon_stock_gtco2_equivalent"] * deployment_fraction(year, p)
    reserve = strategic_reserve_stock_gtco2(year, p)
    return stand + reserve


def working_stock_change_gtco2(year: int, p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> float:
    if year < p.deployment_start_year:
        return 0.0
    return max(0.0, working_stock_gtco2(year, p) - working_stock_gtco2(year-1, p))


def mature_fuel_abatement_gtco2_yr(p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> float:
    return seaweed_bioeconomy(p)["liquid_fuels"]["potential_lifecycle_avoided_fossil_gtco2_yr"]


def annual_fuel_delivery(year: int, p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> Dict:
    """Gross fuel output less fuel placed into the strategic reserve that year."""
    mature=seaweed_bioeconomy(p)
    dep=deployment_fraction(year,p)
    gross_mt=mature["liquid_fuels"]["finished_fuel_mt_yr"]*dep
    reserve_build_gtco2=max(0.0, strategic_reserve_stock_gtco2(year,p)-strategic_reserve_stock_gtco2(year-1,p)) if year>=p.deployment_start_year else 0.0
    reserve_build_mt=reserve_build_gtco2*1000.0/p.fossil_fuel_co2_kg_per_kg
    delivered_mt=max(0.0,gross_mt-reserve_build_mt)
    frac=(delivered_mt/gross_mt) if gross_mt>0 else 0.0
    return {
        "gross_finished_fuel_mt_yr":gross_mt,
        "reserve_addition_fuel_mt_yr":reserve_build_mt,
        "delivered_finished_fuel_mt_yr":delivered_mt,
        "delivered_fraction_of_gross_fuel":frac,
        "delivered_fuel_energy_twh_yr":mature["liquid_fuels"]["finished_fuel_energy_twh_yr"]*dep*frac,
        "delivered_aviation_energy_twh_yr":mature["liquid_fuels"]["aviation_energy_twh_yr"]*dep*frac,
        "delivered_heavy_equipment_energy_twh_yr":mature["liquid_fuels"]["heavy_equipment_energy_twh_yr"]*dep*frac,
        "delivered_marine_other_energy_twh_yr":mature["liquid_fuels"]["marine_other_energy_twh_yr"]*dep*frac,
    }


def annual_additionality_abatement_gtco2(year: int, additionality_fraction: float,
                                          include_working_stock_build: bool = True,
                                          p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> float:
    delivery = annual_fuel_delivery(year,p)
    dep = deployment_fraction(year,p)
    delivered_fraction = delivery["delivered_fraction_of_gross_fuel"]
    # During reserve build, fuel placed into inventory cannot simultaneously displace fossil fuel.
    avoided = mature_fuel_abatement_gtco2_yr(p) * dep * delivered_fraction * additionality_fraction
    stock = working_stock_change_gtco2(year, p) if include_working_stock_build else 0.0
    return avoided + stock


def _run_design_with_additionality(additionality_fraction: float, include_working_stock_build: bool = True,
                                     p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs()) -> Dict:
    original = v53.gross_emissions_path
    def patched(year, s):
        return max(0.0, original(year, s) - annual_additionality_abatement_gtco2(year, additionality_fraction, include_working_stock_build, p))
    v53.gross_emissions_path = patched
    try:
        r = v53.run_v52_case("accelerated", "central", "baseline", 50.0)
        h = dict(r["headline"])
    finally:
        v53.gross_emissions_path = original
    return {
        "additionality_fraction": additionality_fraction,
        "working_stock_build_credited": include_working_stock_build,
        "mature_fuel_abatement_gtco2_yr_if_additional": mature_fuel_abatement_gtco2_yr(p),
        "first_below_280_year": h["first_below_280_year"],
        "target_band_entry_year": h["target_band_entry_year"],
        "peak_co2_ppm": h["peak_co2_ppm"],
        "peak_co2_year": h["peak_co2_year"],
        "peak_warming_c": h["peak_warming_c"],
        "peak_warming_year": h["peak_warming_year"],
        "warming_at_280_c": h["warming_at_280_c"],
        "cumulative_cdr_to_target_gtco2": h["cumulative_cdr_to_target_gtco2"],
        "restoration_warming_2100_c": h["restoration_warming_2100_c"],
        "classification": "Sensitivity only. Full credit is valid only to the extent the seaweed fuel displacement was absent from the technology-neutral V53 transition; otherwise it double-counts mitigation.",
    }


def annual_seaweed_rows(p: SeaweedBioeconomyInputs = SeaweedBioeconomyInputs(), end_year: int = 2060) -> List[Dict]:
    mature = seaweed_bioeconomy(p)
    fuel = mature["liquid_fuels"]
    stocks = mature["carbon_stocks"]
    rows=[]
    for y in range(v53.START_YEAR, end_year+1):
        dep=deployment_fraction(y,p)
        rs=reserve_stock_fraction(y,p)
        delivery=annual_fuel_delivery(y,p)
        rows.append({
            "year":y,
            "deployment_fraction":dep,
            "dry_biomass_gt_yr":mature["total_dry_biomass_gt_yr"]*dep,
            "finished_fuel_mt_yr":fuel["finished_fuel_mt_yr"]*dep,
            "reserve_addition_fuel_mt_yr":delivery["reserve_addition_fuel_mt_yr"],
            "delivered_finished_fuel_mt_yr":delivery["delivered_finished_fuel_mt_yr"],
            "fuel_energy_twh_yr":fuel["finished_fuel_energy_twh_yr"]*dep,
            "delivered_fuel_energy_twh_yr":delivery["delivered_fuel_energy_twh_yr"],
            "delivered_aviation_energy_twh_yr":delivery["delivered_aviation_energy_twh_yr"],
            "delivered_heavy_equipment_energy_twh_yr":delivery["delivered_heavy_equipment_energy_twh_yr"],
            "potential_lifecycle_avoided_fossil_gtco2_yr":fuel["potential_lifecycle_avoided_fossil_gtco2_yr"]*dep*delivery["delivered_fraction_of_gross_fuel"],
            "standing_farm_stock_gtco2_equiv":stocks["average_standing_farm_carbon_stock_gtco2_equivalent"]*dep,
            "strategic_reserve_stock_gtco2_equiv":strategic_reserve_stock_gtco2(y,p),
            "combined_working_stock_gtco2_equiv":working_stock_gtco2(y,p),
            "annual_working_stock_build_gtco2_equiv":working_stock_change_gtco2(y,p),
        })
    return rows


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_v53_core_summary(root: Path = HERE) -> Dict:
    path=root/"planetary_restoration_v53_1_results.json"
    d=json.loads(path.read_text(encoding="utf-8"))
    ens=d.get("full_advanced_sensitivity_ensemble",{})
    return {
        "source_file":str(path.relative_to(root)),
        "source_sha256":_sha256(path),
        "model_version":d.get("model_version"),
        "release_label":d.get("release_label"),
        "release_status":d.get("release_status"),
        "classification":d.get("classification"),
        "headline":d.get("headline",{}),
        "ensemble_summary":{k:v for k,v in ens.items() if k not in ("draw_rows","parameter_ranges","transition_case_weights","land_case_weights")},
        "ensemble_parameter_ranges":ens.get("parameter_ranges",{}),
        "ensemble_transition_case_weights":ens.get("transition_case_weights",{}),
        "ensemble_land_case_weights":ens.get("land_case_weights",{}),
    }


def validate_v53_deterministic_against_frozen(frozen: Dict) -> Dict:
    fresh=v53.run_v52_case("accelerated","central","baseline",50.0)["headline"]
    old=frozen["headline"]
    keys=("first_below_280_year","target_band_entry_year","peak_co2_ppm","peak_warming_c","cumulative_cdr_to_target_gtco2")
    diffs={}
    ok=True
    for k in keys:
        a=old.get(k); b=fresh.get(k)
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):
            delta=float(b)-float(a); diffs[k]={"frozen":a,"fresh":b,"delta":delta}
            tol=0.0 if "year" in k else 1e-9
            if abs(delta)>tol: ok=False
        else:
            diffs[k]={"frozen":a,"fresh":b,"match":a==b}; ok=ok and (a==b)
    return {
        "status":"PASS" if ok else "FAIL",
        "interpretation":"The deterministic V53.1 accelerated-design core is re-executed and compared against the frozen submitted package. The expensive 700-draw V53.1 uncertainty ensemble is preserved byte-for-byte rather than needlessly regenerated because the V54 primary seaweed case is substitution-only.",
        "comparisons":diffs,
    }


def bicrs_land_relief_sensitivity() -> List[Dict]:
    """Test whether seaweed durable storage relieves V53 agricultural-land constraints."""
    mature=seaweed_bioeconomy()
    seaweed_durable=mature["carbon_stocks"]["durable_seaweed_storage_gtco2_yr"]
    orig_land=v53._biomass_land_and_water
    orig_constrain=v53.constrain_portfolio
    holder={"year":v53.START_YEAR}
    def patched_land(pathway,cdr_gt,c):
        if pathway=="BiCRS / BECCS / durable biomass storage":
            sea_sub=seaweed_durable*deployment_fraction(holder["year"])
            return orig_land(pathway,max(0.0,cdr_gt-sea_sub),c)
        return orig_land(pathway,cdr_gt,c)
    def patched_constrain(year,rows,c):
        holder["year"]=year
        return orig_constrain(year,rows,c)
    rows=[]
    for case in ("accelerated","evidence","constraint"):
        base=v53.run_v52_case(case,"central","baseline",50.0)["headline"]
        v53._biomass_land_and_water=patched_land; v53.constrain_portfolio=patched_constrain
        try:
            rel=v53.run_v52_case(case,"central","baseline",50.0)["headline"]
        finally:
            v53._biomass_land_and_water=orig_land; v53.constrain_portfolio=orig_constrain
        rows.append({
            "scenario":case,
            "baseline_first_below_280_year":base["first_below_280_year"],
            "with_seaweed_bicrs_land_relief_first_below_280_year":rel["first_below_280_year"],
            "baseline_peak_co2_ppm":base["peak_co2_ppm"],
            "with_land_relief_peak_co2_ppm":rel["peak_co2_ppm"],
            "peak_co2_change_ppm":rel["peak_co2_ppm"]-base["peak_co2_ppm"],
            "baseline_cumulative_cdr_gtco2":base["cumulative_cdr_to_target_gtco2"],
            "with_land_relief_cumulative_cdr_gtco2":rel["cumulative_cdr_to_target_gtco2"],
            "milestone_year_change":rel["first_below_280_year"]-base["first_below_280_year"],
            "classification":"Land/water constraint sensitivity only; seaweed durable storage substitutes for part of BiCRS feedstock without adding extra CDR.",
        })
    return rows


def run_v54(rerun_v53_ensemble_samples: int = 0) -> Dict:
    # Preserve the submitted V53.1 700-draw uncertainty ensemble byte-for-byte by default.
    # Re-execute the deterministic core for a numerical equality check. A caller may request
    # an expensive fresh V53 ensemble explicitly, but V54 does not require one for its primary
    # substitution-only accounting.
    if rerun_v53_ensemble_samples and rerun_v53_ensemble_samples > 0:
        rerun=v53.run_v53_release(rerun_v53_ensemble_samples)
        primary={
            "source_file":"fresh in-memory V53.1 rerun",
            "source_sha256":None,
            "model_version":rerun.get("model_version"),
            "release_label":rerun.get("release_label"),
            "release_status":rerun.get("release_status"),
            "classification":rerun.get("classification"),
            "headline":rerun.get("headline",{}),
            "ensemble_summary":{k:v for k,v in rerun.get("full_advanced_sensitivity_ensemble",{}).items() if k!="draw_rows"},
        }
    else:
        primary=frozen_v53_core_summary()
    validation=validate_v53_deterministic_against_frozen(frozen_v53_core_summary())
    sea = seaweed_bioeconomy()
    primary_substitution = _run_design_with_additionality(0.0, False)
    working_stock_only = _run_design_with_additionality(0.0, True)
    sensitivities = [_run_design_with_additionality(x, True) for x in (0.5, 1.0)]
    return {
        "model_version": MODEL_VERSION,
        "release_label": RELEASE_LABEL,
        "classification": "V53.1 core + explicit seaweed bioeconomy implementation module. Primary climate accounting avoids double-counting the technology-neutral transition; additionality cases are sensitivities.",
        "v53_1_core": primary,
        "v53_1_core_validation": validation,
        "seaweed_bioeconomy": sea,
        "seaweed_annual_deployment": annual_seaweed_rows(),
        "seaweed_parameter_sensitivity": seaweed_parameter_sensitivity(),
        "food_allocation_sensitivity": food_allocation_sensitivity(),
        "habitat_coculture_sensitivity": habitat_coculture_sensitivity(),
        "bicrs_land_relief_sensitivity": bicrs_land_relief_sensitivity(),
        "primary_substitution_case": primary_substitution,
        "working_stock_only_sensitivity": working_stock_only,
        "additionality_sensitivity": sensitivities,
        "headline_comparison": {
            "v53_1_primary_accelerated_first_below_280_year": primary["headline"]["first_below_280_year"],
            "v54_primary_substitution_first_below_280_year": primary_substitution["first_below_280_year"],
            "v54_working_stock_only_first_below_280_year": working_stock_only["first_below_280_year"],
            "v54_50pct_additionality_first_below_280_year": sensitivities[0]["first_below_280_year"],
            "v54_100pct_additionality_first_below_280_year": sensitivities[1]["first_below_280_year"],
            "v53_1_primary_peak_co2_ppm": primary["headline"]["peak_co2_ppm"],
            "v54_working_stock_only_peak_co2_ppm": working_stock_only["peak_co2_ppm"],
            "v54_100pct_additionality_peak_co2_ppm": sensitivities[1]["peak_co2_ppm"],
            "v53_1_primary_cumulative_cdr_to_target_gtco2": primary["headline"]["cumulative_cdr_to_target_gtco2"],
            "v54_working_stock_only_cumulative_cdr_to_target_gtco2": working_stock_only["cumulative_cdr_to_target_gtco2"],
            "v54_100pct_additionality_cumulative_cdr_to_target_gtco2": sensitivities[1]["cumulative_cdr_to_target_gtco2"],
            "interpretation": "The primary date is unchanged because V53.1 already assumed a successful technology-neutral aviation/energy transition. If 50% or 100% of modeled seaweed-fuel displacement is genuinely additional, the deterministic accelerated-design 280-ppm milestone advances by roughly 2 or 4 years in this screen. Peak warming does not necessarily fall because faster fossil phase-down also unmasks aerosol cooling in the non-CO2 module.",
        },
        "accounting_boundaries": {
            "fuel_displacement": "Not added to primary transition emissions to avoid double counting.",
            "working_carbon_stocks": "Reported as temporary/working stocks; not added to durable CDR headline.",
            "durable_seaweed_storage": "Substitutes into existing BiCRS allocation; not stacked onto 15.2 GtCO2/yr mature incremental CDR target.",
            "habitat_and_coculture": "Physical habitat footprint is reported; coculture food is a scenario screen and does not alter the core fish-recovery or population headline.",
            "economics": "Grid-harvester cost and process-energy screens are reported separately; V53.1 long-horizon fiscal ledger is not silently rewritten with unvalidated seaweed commodity prices.",
        },
    }


def _write_csv(path: Path, rows: List[Dict]) -> None:
    if not rows:
        return
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys:keys.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:
            q={k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for k,v in r.items()}
            w.writerow(q)


def write_external_validation_inputs(root: Path) -> None:
    """Prepare FaIR/Hector-ready net-CO2 trajectories for V54 sensitivities.

    The primary substitution case is exactly the frozen V53.1 trajectory. The 50% and
    100% additionality files subtract V54 delivered-fuel abatement plus temporary working
    stock build from the frozen net-CO2 flux. They are inputs for external benchmarking,
    not externally validated outputs themselves.
    """
    src=root/"external_validation_workflow"/"validation_input"/"external_validation_net_co2_trajectory_extended_to_2400.csv"
    if not src.exists():
        return
    rows=[]
    with src.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    outdir=src.parent
    for frac,label in ((0.0,"working_stock_only"),(0.5,"50pct_additionality"),(1.0,"100pct_additionality")):
        out=[]
        for row in rows:
            y=int(float(row["year"]))
            inc=annual_additionality_abatement_gtco2(y,frac,True)
            base=float(row["net_co2_gtco2"])
            q=dict(row)
            q["v54_incremental_abatement_gtco2"]=inc
            q["v53_1_net_co2_gtco2"]=base
            q["net_co2_gtco2"]=base-inc
            q["v54_sensitivity_label"]=label
            out.append(q)
        _write_csv(outdir/f"v54_{label}_net_co2_trajectory_extended_to_2400.csv",out)


def write_outputs(result: Dict, root: Path) -> None:
    data=root/"data";data.mkdir(exist_ok=True)
    write_external_validation_inputs(root)
    (data/"planetary_restoration_v54_results.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    _write_csv(data/"v54_seaweed_annual_deployment.csv",result["seaweed_annual_deployment"])
    _write_csv(data/"v54_seaweed_additionality_sensitivity.csv",result["additionality_sensitivity"])
    _write_csv(data/"v54_seaweed_parameter_sensitivity.csv",result["seaweed_parameter_sensitivity"])
    _write_csv(data/"v54_food_allocation_sensitivity.csv",result["food_allocation_sensitivity"])
    _write_csv(data/"v54_habitat_coculture_sensitivity.csv",result["habitat_coculture_sensitivity"])
    _write_csv(data/"v54_bicrs_land_relief_sensitivity.csv",result["bicrs_land_relief_sensitivity"])
    _write_csv(data/"v54_working_stock_only_sensitivity.csv",[result["working_stock_only_sensitivity"]])
    sea=result["seaweed_bioeconomy"]
    flat=[]
    def walk(prefix,obj):
        if isinstance(obj,dict):
            for k,v in obj.items():walk(f"{prefix}.{k}" if prefix else k,v)
        elif isinstance(obj,(str,int,float,bool)) or obj is None:
            flat.append({"metric":prefix,"value":obj})
    walk("",sea)
    _write_csv(data/"v54_seaweed_bioeconomy_metrics.csv",flat)

    h=result["headline_comparison"]; s=sea
    md=f"""# Planetary Restoration Model V54 — seaweed integration results\n\n## What was restored from the earlier model\n\nV54 explicitly restores the **grid/drone seaweed harvester** that existed in the earlier v18–v20 model and had been lost from V53.1. The central engineering screen uses a 100 wet-t/h unit, 10.70 kWh per dry tonne, and a **3.0x bankable efficiency factor** relative to the conventional-harvest proxy. The older 3.782x value is retained only as an engineering-upper movement proxy, not as a validated joule ratio.\n\n## Central seaweed bioeconomy results\n\n- Farm area: **{s['area_mkm2']:.3f} million km²**.\n- Dry biomass: **{s['total_dry_biomass_gt_yr']:.3f} Gt/yr**.\n- Grid-harvester electricity: **{s['grid_harvester']['global_harvest_electricity_twh_yr']:.1f} TWh/yr**, versus **{s['grid_harvester']['conventional_proxy_harvest_electricity_twh_yr']:.1f} TWh/yr** on the 3x conventional proxy; saving **{s['grid_harvester']['harvest_electricity_saved_vs_conventional_proxy_twh_yr']:.1f} TWh/yr**.\n- Grid-harvester cost saving: **US${s['grid_harvester']['harvest_cost_saving_usd_bn_yr']:.1f} bn/yr** versus the earlier conventional harvest-cost reference.\n- Finished low-carbon liquid fuel: **{s['liquid_fuels']['finished_fuel_mt_yr']:.1f} Mt/yr**, **{s['liquid_fuels']['finished_fuel_energy_twh_yr']:.0f} TWh/yr**.\n- Aviation allocation: **{s['liquid_fuels']['aviation_energy_twh_yr']:.0f} TWh/yr**, about **{100*s['liquid_fuels']['aviation_share_of_earlier_global_fuel_benchmark']:.1f}%** of the earlier global aviation-energy benchmark.\n- Heavy-equipment allocation: **{s['liquid_fuels']['heavy_equipment_energy_twh_yr']:.0f} TWh/yr**.\n- Marine/other liquid fuel: **{s['liquid_fuels']['marine_other_energy_twh_yr']:.0f} TWh/yr**.\n- Potential lifecycle avoided fossil CO2 if fully additional: **{s['liquid_fuels']['potential_lifecycle_avoided_fossil_gtco2_yr']:.3f} GtCO2/yr** at the central 70% lifecycle reduction assumption.\n- Food-grade seaweed: **{s['food']['food_grade_dry_seaweed_mt_yr']:.1f} Mt dry/yr**, equivalent to **{s['food']['full_diet_calorie_equivalent_million_people']:.0f} million full-diet calorie-equivalents**, but the model treats it as a supplement across billions because species/iodine/trace-element constraints matter.\n- Average standing-farm working carbon stock: **{s['carbon_stocks']['average_standing_farm_carbon_stock_gtco2_equivalent']:.3f} GtCO2-eq**.\n- Two-year strategic fuel-reserve target: **{s['carbon_stocks']['strategic_fuel_reserve_target_gtco2_equivalent']:.3f} GtCO2-eq**.\n- Combined standing-farm + reserve working stock: **{s['carbon_stocks']['combined_working_stock_gtco2_equivalent']:.3f} GtCO2-eq**. These are **not counted as permanent CDR**.\n- Durable seaweed storage available inside the existing BiCRS allocation: **{s['carbon_stocks']['durable_seaweed_storage_gtco2_yr']:.3f} GtCO2/yr**, with about **{s['carbon_stocks']['central_dedicated_land_relief_mha']:.2f} Mha** of central dedicated-land relief.\n- Physical farm habitat footprint: **{s['habitat']['farm_habitat_footprint_km2']:,.0f} km²**. The illustrative co-culture screen is **{s['habitat']['illustrative_coculture_edible_aquatic_product_mt_yr']:.1f} Mt/yr**, but it is deliberately **not credited** to the core fish-recovery result because habitat outcomes are site-specific.\n- HTL/CSP process screen: **{s['process_energy']['electricity_plus_hydrogen_twh_e_yr']:.0f} TWh/yr** electric/H2 plus **{s['process_energy']['direct_concentrated_solar_heat_twh_th_yr']:.0f} TWh-th/yr** direct concentrated-solar heat.\n\n## Does it improve the planetary-restoration date?\n\nThe primary V54 accounting says **not automatically**. V53.1's emissions transition was technology-neutral and already assumed aviation/shipping and other energy sectors successfully decarbonize. Crediting seaweed fuel again would double-count the same mitigation. Therefore the primary deterministic accelerated-design milestone remains **{h['v54_primary_substitution_first_below_280_year']}**.\n\nAs a transparent additionality sensitivity:\n\n- 50% of the modeled fuel displacement additional to V53.1: **{h['v54_50pct_additionality_first_below_280_year']}**.\n- 100% additional: **{h['v54_100pct_additionality_first_below_280_year']}**.\n\nThat is an improvement of up to about **{h['v53_1_primary_accelerated_first_below_280_year']-h['v54_100pct_additionality_first_below_280_year']} years** in the deterministic screen, while reducing required cumulative CDR. It is a sensitivity, not the new primary forecast.\n\n## Scientific boundary\n\nThe grid harvester is an engineering screen, not a prototype-validated energy ratio. Macroalgae HTL yields, lifecycle GHG intensity, nutrient supply, farm ecology and very large-scale logistics all remain validation requirements. Seaweed-farm habitat effects are mixed across published studies, so V54 reports the habitat footprint but does not automatically translate all farm area into extra fish biomass.\n"""
    (root/"SEAWEED_BIOECONOMY_V54.md").write_text(md,encoding="utf-8")


def main(argv=None) -> int:
    ap=argparse.ArgumentParser(description=RELEASE_LABEL)
    ap.add_argument("--rerun-v53-ensemble-samples",type=int,default=0,help="Optional expensive fresh V53.1 ensemble; default preserves the submitted 700-draw core.")
    ap.add_argument("--no-write",action="store_true")
    args=ap.parse_args(argv)
    result=run_v54(args.rerun_v53_ensemble_samples)
    if not args.no_write:write_outputs(result,HERE)
    print(json.dumps({"headline_comparison":result["headline_comparison"],"seaweed_bioeconomy":result["seaweed_bioeconomy"]},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
