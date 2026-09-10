#!/usr/bin/env python3
"""Planetary Restoration Model Version 53.1 — Nature-readiness internal candidate.

This is the sole Version 53.1 computational source of truth. It integrates the core
reservoir-memory carbon cycle, CDR deployment, food/land/blue-water constraints,
energy/material/workforce screens, transition capital, settlement finance, stored-carbon
permanence/reversal, lagged permafrost commitment, dynamic CH4/N2O/aerosol forcing,
global-mean temperature, surface-ocean pH/alkalinity, symmetric avoided-damage screens,
public/private Sources & Uses, and the post-restoration social-dividend policy screen.

Version 53.1 carries the V52 reconciled architecture and the V53 adversarial-audit hardening, plus Nature-readiness release hygiene and main-text non-CO2 endpoint reporting. Every annual CSV is projected
from one immutable annual state object. The release deliberately publishes an Accelerated
Planetary Restoration Design, an Evidence-Anchored Deployment Case, and a Constraint-Binding
Stress Case as co-equal scenarios. It is a reduced-complexity global screening framework,
not a calibrated full Earth-system or integrated-assessment forecast.

Run: python planetary_restoration_model_v53_1.py
"""
from __future__ import annotations

MODEL_VERSION = "53.1"
RELEASE_LABEL = "Planetary Restoration Model Version 53.1"

import csv
import json
import math
import os
import random
from collections import defaultdict
from dataclasses import dataclass, asdict, field, replace
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple


# ============================================================================================
# SECTION 1  Physical constants, scenario inputs and the Joos reservoir-memory carbon cycle
#   (merged from planetary_physics_core.py)
# ============================================================================================

from dataclasses import dataclass, asdict, replace
from typing import Dict, List, Tuple, Optional
import csv
import json
import math
import os
import random

# --- Scientific constants / cited anchors -------------------------------------------------
CO2_MASS_GTC_PER_PPM = 2.123  # standard atmospheric conversion used by GCB/IRF applications
CO2_GTC_TO_GTCO2 = 3.664
PREINDUSTRIAL_CO2_PPM = 278.0
TARGET_CO2_PPM = 280.0
START_CO2_PPM = 428.73  # NOAA global monthly mean, May 2026
START_YEAR = 2026
EMISSIONS_ANCHOR_GTCO2 = 42.2  # Global Carbon Budget 2025 preliminary total anthropogenic CO2
OBSERVED_NATURAL_SINK_GTC_YR = 6.3  # GCB 2025 preliminary land 3.1 + ocean 3.2 GtC/yr

# Joos et al. (2013) / IPCC AR5 CO2 impulse-response coefficients.
JOOS_A = (0.2173, 0.2240, 0.2824, 0.2763)
JOOS_TAU_YR = (math.inf, 394.4, 36.54, 4.304)

SOURCE_URLS = {
    "NOAA_CO2": "https://gml.noaa.gov/ccgg/trends/global.html",
    "GCB_2025": "https://essd.copernicus.org/articles/18/3211/2026/",
    "JOOS_2013": "https://doi.org/10.5194/acp-13-2793-2013",
    "IPCC_AR5_IRF": "https://www.ipcc.ch/site/assets/uploads/2018/07/WGI_AR5.Chap_.8_SM.pdf",
    "SOCDR_2026": "https://www.stateofcdr.org/report/3rd-edition",
    "SOCDR_CH8": "https://www.stateofcdr.org/asset/SoCDR-Ed3_Chapter-8_Final.pdf",
    "MCKINSEY_DC": "https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights/the-cost-of-compute-a-7-trillion-dollar-race-to-scale-data-centers",
}


@dataclass(frozen=True)
class Scenario:
    name: str = "Accelerated restoration design"
    emissions_anchor_gtco2: float = EMISSIONS_ANCHOR_GTCO2
    residual_emissions_gtco2: float = 1.5
    residual_year: int = 2050
    cdr_mode: str = "accelerated"  # accelerated | evidence_benchmark | capped
    mature_incremental_cdr_gtco2: float = 15.2
    cdr_maturity_year: int = 2043
    desalination_dispatch_fraction: float = 0.0  # 0 = contingency not dispatched, 1 = full backstop
    observed_natural_sink_gtc_yr: float = OBSERVED_NATURAL_SINK_GTC_YR
    end_year: int = 2400
    emissions_mode: str = "endogenous"  # endogenous | prescribed
    transition_case_key: str = "iea_nze_reference"


@dataclass(frozen=True)
class FinanceInputs:
    mature_gdp_usd_tn: float = 309.0
    mature_gdp_low_usd_tn: float = 270.0
    mature_gdp_high_usd_tn: float = 350.0
    cdr_cost_usd_t: float = 185.0
    cdr_cost_low_usd_t: float = 150.0
    cdr_cost_high_usd_t: float = 220.0
    settlement_envelope_fraction_gdp: float = 0.0214
    gdp_2026_usd_tn: float = 126.3


@dataclass(frozen=True)
class WaterInputs:
    population_billion: float = 10.3
    municipal_l_per_person_day: float = 100.0
    wastewater_collected_km3: float = 357.0
    wastewater_reused_km3: float = 214.29
    desalination_backstop_km3: float = 250.0
    treatment_kwh_m3: float = 0.27
    reuse_polishing_kwh_m3: float = 0.20
    desalination_kwh_m3: float = 3.0


@dataclass(frozen=True)
class SeaweedInputs:
    area_mkm2: float = 0.586
    dry_yield_t_ha_yr: float = 25.0
    dry_biomass_carbon_fraction: float = 0.30
    molar_c_to_n: float = 20.0
    molar_c_to_p: float = 801.0
    eutrophic_n_available_mt_yr: float = 4.42
    eutrophic_p_available_mt_yr: float = 0.555
    fertilizer_recovery_n_fraction: float = 0.65
    fertilizer_recovery_p_fraction: float = 0.855


@dataclass(frozen=True)
class NutrientInputs:
    recycled_p_supply_low_mt: float = 14.40
    recycled_p_supply_central_mt: float = 17.92
    recycled_p_supply_high_mt: float = 23.13
    maintenance_p_low_mt: float = 14.249
    maintenance_p_central_mt: float = 17.500
    maintenance_p_high_mt: float = 19.685


@dataclass(frozen=True)
class PlasticInputs:
    buoyant_stock_mt: float = 3.20
    legacy_surface_macroplastic_mt: float = 1.84
    legacy_removal_fraction: float = 0.90
    campaign_start_year: int = 2027
    campaign_end_year: int = 2040
    gross_new_buoyant_input_mt_yr: float = 0.50
    interception_fraction: float = 0.80
    structural_qualification_yield: float = 0.55
    seaweed_area_mkm2: float = 0.586
    storm_share: float = 0.20
    structure_polymer_t_km2: float = 100.0
    marine_cleanup_electricity_twh_yr: float = 60.0


@dataclass(frozen=True)
class BaseSystemInputs:
    # Explicit external screen from the wider physical model; not re-derived here.
    pre_cdr_transformed_electricity_twh_yr: float = 86181.327
    pre_cdr_low_twh_yr: float = 78000.0
    pre_cdr_high_twh_yr: float = 95000.0


# Mature design allocation = 15.2 GtCO2/yr. All quantities scale from the scenario's funded CDR.
# tuple: name, Gt/yr design allocation, electricity MWh/t central/low/high, heat MWhth/t,
#        cost note
CDR_PORTFOLIO = [
    ("DACCS", 4.75, 0.80, 0.35, 1.30, 1.50),
    ("Enhanced silicate weathering", 1.90, 0.40, 0.20, 0.80, 0.00),
    ("Ocean alkalinity / carbonate weathering", 0.95, 0.50, 0.10, 2.00, 0.00),
    ("Biochar", 1.425, 0.05, 0.02, 0.12, 0.00),
    ("BiCRS / BECCS / durable biomass storage", 2.85, 0.10, -0.20, 0.30, 0.00),
    ("Biological restoration", 1.425, 0.01, 0.005, 0.03, 0.00),
    ("Direct/passive mineral carbonation", 1.90, 0.50, 0.15, 1.00, 0.00),
]
DESIGN_PORTFOLIO_TOTAL = sum(x[1] for x in CDR_PORTFOLIO)

# Highest-ambition total CDR median from State of CDR 2026, Chapter 8.
# We subtract the present 2.2 Gt/yr baseline when comparing with this model's *incremental* programme.
SOCDR_TOTAL_CDR_ANCHORS = {
    2026: 2.2,
    2030: 2.9,
    2035: 3.9,
    2050: 8.8,
    2100: 15.3,
}
SOCDR_CURRENT_BASELINE = 2.2


# --- General helpers ---------------------------------------------------------------------
def piecewise_linear(year: int, anchors: Dict[int, float]) -> float:
    years = sorted(anchors)
    if year <= years[0]:
        return anchors[years[0]]
    if year >= years[-1]:
        return anchors[years[-1]]
    for y0, y1 in zip(years, years[1:]):
        if y0 <= year <= y1:
            f = (year - y0) / (y1 - y0)
            return anchors[y0] + f * (anchors[y1] - anchors[y0])
    raise RuntimeError("piecewise interpolation failed")


def emissions_path(year: int, s: Scenario) -> float:
    if year <= START_YEAR:
        return s.emissions_anchor_gtco2
    if year >= s.residual_year:
        return s.residual_emissions_gtco2
    f = (year - START_YEAR) / (s.residual_year - START_YEAR)
    return s.emissions_anchor_gtco2 + f * (s.residual_emissions_gtco2 - s.emissions_anchor_gtco2)


def incremental_cdr_path(year: int, s: Scenario) -> float:
    if s.cdr_mode == "evidence_benchmark":
        total = piecewise_linear(year, SOCDR_TOTAL_CDR_ANCHORS)
        return max(0.0, total - SOCDR_CURRENT_BASELINE)
    if year <= START_YEAR:
        return 0.0
    if year >= s.cdr_maturity_year:
        return s.mature_incremental_cdr_gtco2
    f = (year - START_YEAR) / (s.cdr_maturity_year - START_YEAR)
    return max(0.0, s.mature_incremental_cdr_gtco2 * f)


# --- Carbon-cycle reservoir-memory emulator -----------------------------------------------
def _state_for_effective_age(age_yr: float, atmospheric_excess_gtc: float) -> List[float]:
    weights = [JOOS_A[0]]
    for ai, tau in zip(JOOS_A[1:], JOOS_TAU_YR[1:]):
        weights.append(ai * math.exp(-age_yr / tau))
    scale = atmospheric_excess_gtc / sum(weights)
    return [w * scale for w in weights]


def _decay_flux_gtc_yr(state: List[float]) -> float:
    return sum(state[i] / JOOS_TAU_YR[i] for i in range(1, 4))


def initialize_carbon_state(start_ppm: float = START_CO2_PPM,
                            observed_sink_gtc_yr: float = OBSERVED_NATURAL_SINK_GTC_YR) -> Dict:
    """Initialize the four Joos reservoirs to observed concentration and sink strength.

    A single effective historical age is solved so the state simultaneously matches
    the observed 2026 atmospheric excess and the GCB 2025 preliminary natural
    land+ocean sink. This avoids pretending that the 2026 atmosphere is a fresh pulse.
    """
    excess_gtc = (start_ppm - PREINDUSTRIAL_CO2_PPM) * CO2_MASS_GTC_PER_PPM
    lo, hi = 0.0, 250.0
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        st = _state_for_effective_age(mid, excess_gtc)
        sink = _decay_flux_gtc_yr(st)
        if sink > observed_sink_gtc_yr:
            lo = mid
        else:
            hi = mid
    age = 0.5 * (lo + hi)
    state = _state_for_effective_age(age, excess_gtc)
    return {
        "effective_age_years": age,
        "state_gtc": state,
        "total_excess_gtc": sum(state),
        "implied_sink_gtc_yr": _decay_flux_gtc_yr(state),
    }


def _advance_reservoirs(state: List[float], net_flux_gtco2: float) -> Tuple[List[float], float]:
    """Advance one year with exact box decay and a mid-year anthropogenic pulse."""
    new_state = [state[0]]
    natural_flux_to_sinks_gtc = 0.0
    for i in range(1, 4):
        decayed = state[i] * math.exp(-1.0 / JOOS_TAU_YR[i])
        natural_flux_to_sinks_gtc += state[i] - decayed
        new_state.append(decayed)
    pulse_gtc = net_flux_gtco2 / CO2_GTC_TO_GTCO2
    new_state[0] += JOOS_A[0] * pulse_gtc
    for i in range(1, 4):
        # mid-year pulse receives half a year of decay before the end-year observation
        new_state[i] += JOOS_A[i] * pulse_gtc * math.exp(-0.5 / JOOS_TAU_YR[i])
    return new_state, natural_flux_to_sinks_gtc


def _required_net_flux_for_target(state: List[float], target_ppm: float) -> float:
    """Net anthropogenic flux needed during the year to end at target ppm."""
    decayed = [state[0]] + [state[i] * math.exp(-1.0 / JOOS_TAU_YR[i]) for i in range(1, 4)]
    target_excess_gtc = (target_ppm - PREINDUSTRIAL_CO2_PPM) * CO2_MASS_GTC_PER_PPM
    response_sum = JOOS_A[0] + sum(
        JOOS_A[i] * math.exp(-0.5 / JOOS_TAU_YR[i]) for i in range(1, 4)
    )
    needed_pulse_gtc = (target_excess_gtc - sum(decayed)) / response_sum
    return needed_pulse_gtc * CO2_GTC_TO_GTCO2


def unconstrained_reference_carbon_cycle(s: Scenario, maintain_after_target_years: int = 30) -> Dict:
    init = initialize_carbon_state(START_CO2_PPM, s.observed_natural_sink_gtc_yr)
    state = list(init["state_gtc"])
    rows: List[Dict] = []
    peak_ppm = START_CO2_PPM
    peak_year = START_YEAR
    crossing_year: Optional[int] = None
    cumulative_incremental_cdr = 0.0
    maintenance_years = 0

    for year in range(START_YEAR, s.end_year + 1):
        emissions = emissions_path(year, s)
        planned_cdr = incremental_cdr_path(year, s)
        phase = "drawdown"
        if crossing_year is None:
            cdr = planned_cdr
            net = emissions - cdr
        else:
            phase = "target_maintenance"
            net_required = _required_net_flux_for_target(state, TARGET_CO2_PPM)
            cdr = max(0.0, emissions - net_required)
            # if keeping target would require net negative CDR (adding CO2), cap CDR at zero
            net = emissions - cdr
            maintenance_years += 1

        state, natural_sink_gtc = _advance_reservoirs(state, net)
        co2 = PREINDUSTRIAL_CO2_PPM + sum(state) / CO2_MASS_GTC_PER_PPM
        cumulative_incremental_cdr += cdr if crossing_year is None else 0.0

        if co2 > peak_ppm:
            peak_ppm, peak_year = co2, year
        if crossing_year is None and co2 <= TARGET_CO2_PPM:
            crossing_year = year

        rows.append({
            "year": year,
            "phase": phase,
            "gross_emissions_gtco2": emissions,
            "incremental_cdr_gtco2": cdr,
            "net_anthropogenic_gtco2": net,
            "natural_reservoir_flux_to_sinks_gtc": natural_sink_gtc,
            "co2_ppm": co2,
            "reservoir_permanent_gtc": state[0],
            "reservoir_slow_gtc": state[1],
            "reservoir_medium_gtc": state[2],
            "reservoir_fast_gtc": state[3],
        })
        if crossing_year is not None and maintenance_years >= maintain_after_target_years:
            break

    return {
        "scenario": asdict(s),
        "model_class": "GCB-calibrated Joos four-reservoir impulse-response emulator with reservoir memory",
        "publication_boundary": "Reduced-complexity carbon-cycle screen; exact restoration timing requires a calibrated FaIR/OSCAR/Earth-system ensemble.",
        "initialization": init,
        "peak_co2_ppm": peak_ppm,
        "peak_year": peak_year,
        "crossing_year": crossing_year,
        "cumulative_incremental_cdr_to_target_gtco2": cumulative_incremental_cdr,
        "rows": rows,
    }


# --- Coupled CDR, energy and materials ----------------------------------------------------
def cdr_portfolio(cdr_gtco2: float) -> Dict:
    scale = 0.0 if DESIGN_PORTFOLIO_TOTAL == 0 else cdr_gtco2 / DESIGN_PORTFOLIO_TOTAL
    rows = []
    elec = elec_low = elec_high = heat = 0.0
    for name, design_gt, e, elo, ehi, h in CDR_PORTFOLIO:
        amount = design_gt * scale
        et = amount * e * 1000.0
        elt = amount * elo * 1000.0
        eht = amount * ehi * 1000.0
        ht = amount * h * 1000.0
        rows.append({
            "pathway": name,
            "cdr_gtco2_yr": amount,
            "electricity_mwh_t": e,
            "electricity_twh_yr": et,
            "electricity_low_twh_yr": elt,
            "electricity_high_twh_yr": eht,
            "heat_mwhth_t": h,
            "heat_twhth_yr": ht,
        })
        elec += et; elec_low += elt; elec_high += eht; heat += ht
    return {
        "cdr_gtco2_yr": cdr_gtco2,
        "scale_vs_15_2_design": scale,
        "rows": rows,
        "electricity_twh_yr": elec,
        "electricity_low_twh_yr": elec_low,
        "electricity_high_twh_yr": elec_high,
        "low_grade_heat_twhth_yr": heat,
    }


def minerals(portfolio: Dict) -> Dict:
    by = {r["pathway"]: r["cdr_gtco2_yr"] for r in portfolio["rows"]}
    ew = by["Enhanced silicate weathering"]
    oae = by["Ocean alkalinity / carbonate weathering"]
    mc = by["Direct/passive mineral carbonation"]
    # Practical net-removal intensities for basalt (tCO2/t rock); central 0.15.
    ew_low, ew_c, ew_high = ew/0.25, ew/0.15, ew/0.08
    # Feedstock ratios (t feedstock/t CO2), route-dependent screens.
    oae_low, oae_c, oae_high = oae*1.5, oae*2.3, oae*4.0
    mc_low, mc_c, mc_high = mc*1.2, mc*1.75, mc*3.0
    return {
        "enhanced_weathering_rock_gt_yr": ew_c,
        "enhanced_weathering_low_gt_yr": ew_low,
        "enhanced_weathering_high_gt_yr": ew_high,
        "oae_feedstock_gt_yr": oae_c,
        "mineral_carbonation_feedstock_gt_yr": mc_c,
        "total_central_gt_yr": ew_c + oae_c + mc_c,
        "total_low_gt_yr": ew_low + oae_low + mc_low,
        "total_high_gt_yr": ew_high + oae_high + mc_high,
        "constraint": "Mass balance only; route-specific quarry, grinding, transport, port, contamination and lifecycle-emission solves remain required.",
    }


def biomass(portfolio: Dict) -> Dict:
    by = {r["pathway"]: r["cdr_gtco2_yr"] for r in portfolio["rows"]}
    biochar = by["Biochar"]
    bicrs = by["BiCRS / BECCS / durable biomass storage"]
    cfrac = 0.50
    biochar_net = cfrac * 0.30 * 0.80 * (44.0/12.0)
    bicrs_net = cfrac * 0.90 * (44.0/12.0)
    biochar_biomass = biochar / biochar_net
    bicrs_biomass = bicrs / bicrs_net
    total = biochar_biomass + bicrs_biomass
    return {
        "biochar_net_tco2_per_t_biomass": biochar_net,
        "bicrs_net_tco2_per_t_biomass": bicrs_net,
        "biochar_biomass_gt_yr": biochar_biomass,
        "bicrs_biomass_gt_yr": bicrs_biomass,
        "land_biomass_total_gt_yr": total,
        "land_biomass_energy_equivalent_ej_yr": total * 18.0,
        "constraint": "Sustainable regional supply, biodiversity, nutrients, transport and competing uses are not proven by the global mass balance.",
    }


def water(w: WaterInputs = WaterInputs()) -> Dict:
    municipal = w.population_billion * 1e9 * w.municipal_l_per_person_day * 365 / 1e12
    treatment = w.wastewater_collected_km3 * w.treatment_kwh_m3
    reuse = w.wastewater_reused_km3 * w.reuse_polishing_kwh_m3
    desal = w.desalination_backstop_km3 * w.desalination_kwh_m3
    return {
        "municipal_water_km3_yr": municipal,
        "wastewater_collected_km3_yr": w.wastewater_collected_km3,
        "wastewater_reused_km3_yr": w.wastewater_reused_km3,
        "desalination_backstop_km3_yr": w.desalination_backstop_km3,
        "wastewater_treatment_twh_yr": treatment,
        "reuse_polishing_twh_yr": reuse,
        "desalination_backstop_twh_yr": desal,
        "core_water_electricity_twh_yr": treatment + reuse,
        "full_backstop_water_electricity_twh_yr": treatment + reuse + desal,
    }


def seaweed(sw: SeaweedInputs = SeaweedInputs()) -> Dict:
    potential_gt = sw.area_mkm2 * 1e6 * 100.0 * sw.dry_yield_t_ha_yr / 1e9
    # mass N per dry tonne from C:N molar ratio: C_mass * (14/12)/CN
    n_mass_fraction = sw.dry_biomass_carbon_fraction * (14.0/12.0) / sw.molar_c_to_n
    p_mass_fraction = sw.dry_biomass_carbon_fraction * (31.0/12.0) / sw.molar_c_to_p
    n_need_mt = potential_gt * 1000.0 * n_mass_fraction
    p_need_mt = potential_gt * 1000.0 * p_mass_fraction
    supported_by_n_gt = sw.eutrophic_n_available_mt_yr / (1000.0 * n_mass_fraction)
    supported_by_p_gt = sw.eutrophic_p_available_mt_yr / (1000.0 * p_mass_fraction)
    nutrient_supported_gt = min(potential_gt, supported_by_n_gt, supported_by_p_gt)
    supplemental_n = max(0.0, n_need_mt - sw.eutrophic_n_available_mt_yr)
    supplemental_p = max(0.0, p_need_mt - sw.eutrophic_p_available_mt_yr)
    return {
        "area_yield_potential_gt_dry_yr": potential_gt,
        "dry_biomass_n_mass_fraction": n_mass_fraction,
        "dry_biomass_p_mass_fraction": p_mass_fraction,
        "n_required_for_full_potential_mt_yr": n_need_mt,
        "p_required_for_full_potential_mt_yr": p_need_mt,
        "credited_eutrophic_n_mt_yr": sw.eutrophic_n_available_mt_yr,
        "credited_eutrophic_p_mt_yr": sw.eutrophic_p_available_mt_yr,
        "nutrient_supported_biomass_without_other_sources_gt_yr": nutrient_supported_gt,
        "supplemental_or_natural_n_needed_for_full_potential_mt_yr": supplemental_n,
        "supplemental_or_natural_p_needed_for_full_potential_mt_yr": supplemental_p,
        "fertilizer_n_from_credited_capture_mt_yr": sw.eutrophic_n_available_mt_yr * sw.fertilizer_recovery_n_fraction,
        "fertilizer_p_from_credited_capture_mt_yr": sw.eutrophic_p_available_mt_yr * sw.fertilizer_recovery_p_fraction,
        "constraint": "Full area-yield production is not claimed to be supplied solely by eutrophic nutrient capture; additional natural or managed nutrient flux must be demonstrated regionally.",
    }


def nutrients(n: NutrientInputs = NutrientInputs()) -> Dict:
    supplies = [n.recycled_p_supply_low_mt, n.recycled_p_supply_central_mt, n.recycled_p_supply_high_mt]
    reqs = [n.maintenance_p_low_mt, n.maintenance_p_central_mt, n.maintenance_p_high_mt]
    matrix = [[s/r for r in reqs] for s in supplies]
    flat = [x for row in matrix for x in row]
    worst_primary = max(0.0, max(reqs) - min(supplies))
    return {
        "recycled_p_supply_mt": supplies,
        "maintenance_p_requirement_mt": reqs,
        "coverage_matrix": matrix,
        "central_coverage": n.recycled_p_supply_central_mt/n.maintenance_p_central_mt,
        "full_factorial_min_coverage": min(flat),
        "full_factorial_max_coverage": max(flat),
        "worst_case_primary_p_requirement_mt_yr": worst_primary,
    }


def plastics(p: PlasticInputs = PlasticInputs()) -> Dict:
    years = list(range(p.campaign_start_year, p.campaign_end_year + 1))
    n_years = len(years)
    legacy_removed = p.legacy_surface_macroplastic_mt * p.legacy_removal_fraction

    intercepted_no_prevention = p.gross_new_buoyant_input_mt_yr * p.interception_fraction * n_years
    residual_no_prevention = p.gross_new_buoyant_input_mt_yr * (1-p.interception_fraction) * n_years

    intercepted_with_prevention = 0.0
    residual_with_prevention = 0.0
    annual_rows = []
    for i, year in enumerate(years):
        f = i/(n_years-1) if n_years > 1 else 1.0
        gross = p.gross_new_buoyant_input_mt_yr * (1-f)
        intercepted = gross * p.interception_fraction
        residual = gross * (1-p.interception_fraction)
        intercepted_with_prevention += intercepted
        residual_with_prevention += residual
        annual_rows.append({"year": year, "gross_new_input_mt": gross, "intercepted_mt": intercepted, "residual_mt": residual})

    qualified_no_prevention = (legacy_removed + intercepted_no_prevention) * p.structural_qualification_yield
    qualified_with_prevention = (legacy_removed + intercepted_with_prevention) * p.structural_qualification_yield
    storm_area_km2 = p.seaweed_area_mkm2 * 1e6 * p.storm_share
    demand_mt = storm_area_km2 * p.structure_polymer_t_km2 / 1e6

    return {
        "campaign_years": n_years,
        "legacy_removed_mt": legacy_removed,
        "intercepted_new_no_prevention_mt": intercepted_no_prevention,
        "residual_new_no_prevention_mt": residual_no_prevention,
        "qualified_marine_polymer_no_prevention_mt": qualified_no_prevention,
        "intercepted_new_with_prevention_mt": intercepted_with_prevention,
        "residual_new_with_prevention_mt": residual_with_prevention,
        "qualified_marine_polymer_with_prevention_mt": qualified_with_prevention,
        "net_buoyant_stock_reduction_no_prevention_fraction": (legacy_removed-residual_no_prevention)/p.buoyant_stock_mt,
        "net_buoyant_stock_reduction_with_prevention_fraction": (legacy_removed-residual_with_prevention)/p.buoyant_stock_mt,
        "storm_structure_polymer_demand_mt": demand_mt,
        "marine_share_of_demand_no_prevention": qualified_no_prevention/demand_mt,
        "marine_share_of_demand_with_prevention": qualified_with_prevention/demand_mt,
        "land_recycled_polymer_needed_with_prevention_mt": max(0.0, demand_mt-qualified_with_prevention),
        "cleanup_electricity_twh_yr": p.marine_cleanup_electricity_twh_yr,
        "annual_prevention_rows": annual_rows,
    }


def integrated_energy(s: Scenario, portfolio: Dict, base: BaseSystemInputs = BaseSystemInputs()) -> Dict:
    w = water()
    p = plastics()
    desal = w["desalination_backstop_twh_yr"] * max(0.0, min(1.0, s.desalination_dispatch_fraction))
    core = base.pre_cdr_transformed_electricity_twh_yr + portfolio["electricity_twh_yr"] + p["cleanup_electricity_twh_yr"] + w["core_water_electricity_twh_yr"]
    with_dispatch = core + desal
    return {
        "pre_cdr_transformed_electricity_twh_yr": base.pre_cdr_transformed_electricity_twh_yr,
        "pre_cdr_status": "EXTERNAL_SCREEN_INPUT",
        "cdr_direct_electricity_twh_yr": portfolio["electricity_twh_yr"],
        "cdr_low_grade_heat_twhth_yr": portfolio["low_grade_heat_twhth_yr"],
        "marine_cleanup_electricity_twh_yr": p["cleanup_electricity_twh_yr"],
        "core_water_electricity_twh_yr": w["core_water_electricity_twh_yr"],
        "desalination_backstop_twh_yr": w["desalination_backstop_twh_yr"],
        "desalination_dispatch_fraction": s.desalination_dispatch_fraction,
        "desalination_dispatched_twh_yr": desal,
        "core_transformed_electricity_twh_yr": core,
        "transformed_electricity_with_selected_desalination_twh_yr": with_dispatch,
        "full_desalination_backstop_transformed_electricity_twh_yr": core + w["desalination_backstop_twh_yr"],
        "reliability_status": "Annual energy balance only; regional hourly generation/storage/transmission optimization remains required.",
    }


# --- Finance / settlement / banking -------------------------------------------------------


def national_balance(country_wealth: Dict[str, float], timber_index: float = 100.0) -> Dict:
    total = sum(country_wealth.values())
    if total <= 0 or timber_index <= 0:
        raise ValueError("wealth and timber index must be positive")
    pre = {k:v/total for k,v in country_wealth.items()}
    total_gsu = total*100.0/timber_index
    converted = {k:pre[k]*total_gsu for k in country_wealth}
    post = {k:converted[k]/total_gsu for k in converted}
    return {
        "timber_index":timber_index,"total_gsu":total_gsu,"pre_shares":pre,"converted_gsu":converted,
        "post_shares":post,"max_share_error":max(abs(pre[k]-post[k]) for k in pre)
    }


def banking_transition() -> Dict:
    total_capex=6.7; ai_capex=5.2; annualized=total_capex/5
    rows=[]
    for debt_share in (0.30,0.50,0.70):
        for nim in (0.015,0.020,0.025):
            stock=total_capex*debt_share
            rows.append({"debt_share":debt_share,"net_interest_margin":nim,
                         "annual_debt_originations_usd_tn":annualized*debt_share,
                         "illustrative_2030_debt_stock_usd_tn":stock,
                         "illustrative_net_interest_income_usd_bn_yr":stock*nim*1000})
    return {"data_center_capex_2026_2030_usd_tn":total_capex,"ai_specific_capex_usd_tn":ai_capex,
            "annualized_capex_usd_tn_yr":annualized,"scenarios":rows,
            "status":"Financing opportunity screen; bank-system profit neutrality is not determined."}


# --- External screens explicitly isolated -------------------------------------------------
def external_social_ecological_screens() -> List[Dict]:
    return [
        {"domain":"Planning population","value":10.3,"unit":"billion people","status":"EXTERNAL_SCREEN_INPUT"},
        {"domain":"Meat + dairy carrying capacity","value":11.24,"unit":"billion people","status":"EXTERNAL_SCREEN_INPUT"},
        {"domain":"Vegetarian / aquatic carrying capacity","value":12.55,"unit":"billion people","status":"EXTERNAL_SCREEN_INPUT"},
        {"domain":"Plant-based upper capacity","value":13.0,"unit":"billion people","status":"EXTERNAL_SCREEN_INPUT"},
        {"domain":"Healthy-food resource envelope","value":18.54,"unit":"USD tn/yr","status":"EXTERNAL_SCREEN_INPUT"},
        {"domain":"Health-care resource envelope","value":25.75,"unit":"USD tn/yr","status":"EXTERNAL_SCREEN_INPUT"},
        {"domain":"Starvation/minimum-calorie deprivation target","value":2032,"unit":"year","status":"POLICY_DEPLOYMENT_TARGET"},
        {"domain":"Wild-fish median recovery","value":10,"unit":"years","status":"LITERATURE_SCREEN"},
        {"domain":"Healthy-stock horizon","value":2050,"unit":"year","status":"LITERATURE_SCREEN"},
        {"domain":"Routine unabated fossil combustion endpoint","value":2050,"unit":"year","status":"POLICY_SCENARIO_ENDPOINT"},
        {"domain":"Life expectancy sensitivity","value":79.9,"unit":"years in 2054","status":"EXTERNAL_SCREEN_INPUT"},
        {"domain":"Healthy-life gain sensitivity","value":3.0,"unit":"years","status":"EXTERNAL_SCREEN_INPUT"},
    ]


# --- Scenario runs / ensemble -------------------------------------------------------------


# ============================================================================================
# SECTION 2  Two-layer energy-balance temperature response
#   (merged from climate_response.py)
# ============================================================================================

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Sequence

import math

CLIMATE_PREINDUSTRIAL_PPM = 278.0
F_2XCO2_W_M2 = 3.71  # Myhre et al. (1998) doubling forcing
MYHRE_ALPHA = F_2XCO2_W_M2 / math.log(2.0)

CLIMATE_SOURCES = {
    "MYHRE_1998": "https://doi.org/10.1029/98GL01908",
    "HELD_2010": "https://doi.org/10.1175/2009JCLI3466.1",
    "GEOFFROY_2013": "https://doi.org/10.1175/JCLI-D-12-00195.1",
    "IPCC_AR6_WG1_CH7": "https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-7/",
    "IGCC_2025": "https://essd.copernicus.org/articles/17/2641/2025/",
    "NOAA_CO2": "https://gml.noaa.gov/ccgg/trends/global.html",
}

# Historical globally averaged CO2, ppm. Ice-core/firn record spliced to the
# NOAA global marine surface record. Used only to spin the thermal model up.
HISTORICAL_CO2_PPM = {
    1850: 285.2, 1875: 288.0, 1900: 295.7, 1925: 305.0, 1950: 311.3,
    1960: 316.9, 1970: 325.7, 1980: 338.8, 1990: 354.4, 2000: 369.6,
    2010: 389.9, 2015: 400.8, 2020: 412.4, 2025: 424.6, 2026: 428.73,
}

# Net non-CO2 anthropogenic effective radiative forcing, W/m2, anchored to the
# AR6 assessment (total anthropogenic ERF minus the CO2 contribution). This is a
# SCENARIO INPUT, not a model result.
# Net non-CO2 is negative through the mid-20th century, when sulphate aerosol
# loading grew faster than the non-CO2 greenhouse gases, and turns positive as
# air-quality controls cut aerosols while methane, N2O, halocarbons and ozone
# accumulate. Getting that sign history right matters: a monotonic positive path
# overstates mid-century warming and therefore overstates present-day warming.
HISTORICAL_NON_CO2_ERF = {
    1850: 0.00, 1900: 0.00, 1930: -0.05, 1950: -0.15, 1970: -0.35,
    1980: -0.30, 1990: -0.15, 2000: 0.00, 2010: 0.30, 2019: 0.56, 2026: 0.60,
}


@dataclass(frozen=True)
class ClimateParams:
    """Geoffroy et al. (2013) two-layer structure with heat capacities and ocean
    exchange from the CMIP5 multi-model mean. The climate feedback parameter is set
    from the AR6 best-estimate equilibrium sensitivity of 3.0 K rather than the CMIP5
    mean, because AR6 narrowed sensitivity using multiple lines of evidence and the
    CMIP5/CMIP6 means are known to climate_run warm."""
    name: str = "Two-layer central (Geoffroy structure, AR6 ECS 3.0 K)"
    heat_capacity_upper: float = 7.3        # W yr m-2 K-1
    heat_capacity_deep: float = 106.0       # W yr m-2 K-1
    climate_feedback: float = 1.237         # lambda, W m-2 K-1; AR6 best-estimate ECS 3.0 K
    ocean_heat_exchange: float = 0.73       # gamma, W m-2 K-1
    deep_ocean_efficacy: float = 1.28       # epsilon
    spinup_start_year: int = 1850

    @property
    def equilibrium_climate_sensitivity(self) -> float:
        return F_2XCO2_W_M2 / self.climate_feedback

    @property
    def transient_climate_response(self) -> float:
        return F_2XCO2_W_M2 / (
            self.climate_feedback + self.deep_ocean_efficacy * self.ocean_heat_exchange)


# Structural cases spanning the AR6 likely equilibrium-sensitivity range
# (2.5-4.0 K best-estimate range; 3.0 K best estimate).
def climate_parameter_cases() -> List[ClimateParams]:
    return [
        ClimateParams(),
        ClimateParams(name="Low sensitivity (ECS ~2.5 K)", climate_feedback=1.48,
                      ocean_heat_exchange=0.85),
        ClimateParams(name="High sensitivity (ECS ~4.0 K)", climate_feedback=0.93,
                      ocean_heat_exchange=0.62),
    ]


@dataclass(frozen=True)
class NonCO2Scenario:
    """Non-CO2 forcing pathway. Explicitly a scenario, not a model output.

    Aerosol cooling is lost early in a fossil phase-out, so the net non-CO2 term
    typically rises before long-lived greenhouse gases decline enough to bring it
    down. Setting `unmasking_peak_w_m2` equal to `start_w_m2` disables that effect.
    """
    name: str = "Central: aerosol unmasking then GHG decline"
    start_w_m2: float = 0.60
    unmasking_peak_w_m2: float = 0.95
    unmasking_peak_year: int = 2045
    long_run_w_m2: float = 0.20
    long_run_year: int = 2120


def non_co2_forcing(year: int, sc: NonCO2Scenario, start_year: int = 2026) -> float:
    if year <= start_year:
        return _climate_interp(year, HISTORICAL_NON_CO2_ERF)
    if year <= sc.unmasking_peak_year:
        f = (year - start_year) / max(1, sc.unmasking_peak_year - start_year)
        return sc.start_w_m2 + f * (sc.unmasking_peak_w_m2 - sc.start_w_m2)
    if year >= sc.long_run_year:
        return sc.long_run_w_m2
    f = (year - sc.unmasking_peak_year) / max(1, sc.long_run_year - sc.unmasking_peak_year)
    return sc.unmasking_peak_w_m2 + f * (sc.long_run_w_m2 - sc.unmasking_peak_w_m2)


def _climate_interp(year: int, table: Dict[int, float]) -> float:
    ys = sorted(table)
    if year <= ys[0]:
        return table[ys[0]]
    if year >= ys[-1]:
        return table[ys[-1]]
    for a, b in zip(ys, ys[1:]):
        if a <= year <= b:
            f = (year - a) / (b - a)
            return table[a] + f * (table[b] - table[a])
    raise RuntimeError("interpolation failed")


def co2_forcing(ppm: float, reference_ppm: float = CLIMATE_PREINDUSTRIAL_PPM) -> float:
    return MYHRE_ALPHA * math.log(max(1e-9, ppm) / reference_ppm)


def _climate_step(t: float, td: float, forcing: float, p: ClimateParams, dt: float = 1.0):
    """One forward-Euler year. Sub-stepped for numerical stability."""
    substeps = 12
    h = dt / substeps
    for _ in range(substeps):
        heat_to_deep = p.ocean_heat_exchange * (t - td)
        dt_dt = (forcing - p.climate_feedback * t
                 - p.deep_ocean_efficacy * heat_to_deep) / p.heat_capacity_upper
        dtd_dt = heat_to_deep / p.heat_capacity_deep
        t += h * dt_dt
        td += h * dtd_dt
    heat_to_deep = p.ocean_heat_exchange * (t - td)
    imbalance = forcing - p.climate_feedback * t
    return t, td, imbalance, p.deep_ocean_efficacy * heat_to_deep


def climate_spinup(p: ClimateParams = ClimateParams(), end_year: int = START_YEAR - 1,
           sc: NonCO2Scenario = NonCO2Scenario()) -> Dict:
    """Integrate from 1850 so present-day warming is a result, not an input."""
    t = td = 0.0
    rows = []
    for year in range(p.spinup_start_year, end_year + 1):
        ppm = _climate_interp(year, HISTORICAL_CO2_PPM)
        forcing = co2_forcing(ppm) + _climate_interp(year, HISTORICAL_NON_CO2_ERF)
        t, td, imbalance, heat_uptake = _climate_step(t, td, forcing, p)
        rows.append({"year": year, "co2_ppm": ppm, "total_forcing_w_m2": forcing,
                     "surface_warming_c": t, "deep_ocean_warming_c": td,
                     "earth_energy_imbalance_w_m2": imbalance,
                     "ocean_heat_uptake_w_m2": heat_uptake})
    return {"surface_warming_c": t, "deep_ocean_warming_c": td, "rows": rows}


def climate_run(co2_rows: Sequence[Dict], p: ClimateParams = ClimateParams(),
        sc: NonCO2Scenario = NonCO2Scenario(),
        initial: Optional[Dict] = None) -> Dict:
    """Project warming along a CO2 trajectory produced by the carbon module.

    `co2_rows` must contain `year` and `co2_ppm`.
    """
    init = initial or climate_spinup(p, end_year=START_YEAR - 1, sc=sc)
    t = init["surface_warming_c"]
    td = init["deep_ocean_warming_c"]

    rows: List[Dict] = []
    peak_t = t
    peak_year = co2_rows[0]["year"] if co2_rows else None
    years_above_15 = 0
    years_above_20 = 0
    cross_below_15: Optional[int] = None
    cross_below_20: Optional[int] = None
    warming_at_co2_target: Optional[float] = None

    for rec in co2_rows:
        year = rec["year"]
        ppm = rec["co2_ppm"]
        f_co2 = co2_forcing(ppm)
        f_other = non_co2_forcing(year, sc)
        t, td, imbalance, heat_uptake = _climate_step(t, td, f_co2 + f_other, p)

        if t > peak_t:
            peak_t, peak_year = t, year
        if t > 1.5:
            years_above_15 += 1
        elif cross_below_15 is None and peak_t > 1.5:
            cross_below_15 = year
        if t > 2.0:
            years_above_20 += 1
        elif cross_below_20 is None and peak_t > 2.0:
            cross_below_20 = year
        if warming_at_co2_target is None and ppm <= 280.0:
            warming_at_co2_target = t

        rows.append({"year": year, "co2_ppm": ppm, "co2_forcing_w_m2": f_co2,
                     "non_co2_forcing_w_m2": f_other,
                     "total_forcing_w_m2": f_co2 + f_other,
                     "surface_warming_c": t, "deep_ocean_warming_c": td,
                     "earth_energy_imbalance_w_m2": imbalance,
                     "ocean_heat_uptake_w_m2": heat_uptake})

    final = rows[-1] if rows else {}
    return {
        "classification": "Two-layer global-mean energy-balance emulator spun up from 1850; "
                          "no regional pattern, sea level, ice sheet or permafrost response",
        "params": asdict(p),
        "equilibrium_climate_sensitivity_c": p.equilibrium_climate_sensitivity,
        "transient_climate_response_c": p.transient_climate_response,
        "non_co2_scenario": asdict(sc),
        "non_co2_status": "SCENARIO_INPUT",
        "start_warming_c": init["surface_warming_c"],
        "peak_warming_c": peak_t,
        "peak_warming_year": peak_year,
        "years_above_1p5": years_above_15,
        "years_above_2p0": years_above_20,
        "year_falling_below_1p5": cross_below_15,
        "year_falling_below_2p0": cross_below_20,
        "warming_at_co2_target_c": warming_at_co2_target,
        "final_year": final.get("year"),
        "final_warming_c": final.get("surface_warming_c"),
        "final_deep_ocean_warming_c": final.get("deep_ocean_warming_c"),
        "final_earth_energy_imbalance_w_m2": final.get("earth_energy_imbalance_w_m2"),
        "committed_warming_note": (
            "Deep-ocean warming and the associated thermosteric sea-level commitment lag "
            "surface temperature by centuries. Returning CO2 to 280 ppm does not return the "
            "climate system to a pre-industrial state."),
        "rows": rows,
        "sources": CLIMATE_SOURCES,
    }


def climate_validation(p: ClimateParams = ClimateParams(),
               sc: NonCO2Scenario = NonCO2Scenario()) -> Dict:
    """Check the spun-up model against observed warming and energy imbalance.

    Targets are assessment values, not tuning targets: the parameters are the
    published Geoffroy CMIP5 means and are not adjusted to hit these numbers.
    """
    sp = climate_spinup(p, sc=sc)
    by_year = {r["year"]: r for r in sp["rows"]}
    decade = [by_year[y]["surface_warming_c"] for y in range(2010, 2020)]
    return {
        "warming_2010_2019_c": sum(decade) / len(decade),
        "warming_2010_2019_reference_c": 1.07,
        "warming_2010_2019_reference_source": "IPCC AR6 WG1 SPM A.1.3, human-induced warming",
        "warming_2024_c": by_year[2024]["surface_warming_c"],
        "warming_2024_reference_c": 1.36,
        "warming_2024_reference_source": "Indicators of Global Climate Change 2024",
        "energy_imbalance_2024_w_m2": by_year[2024]["earth_energy_imbalance_w_m2"],
        "energy_imbalance_reference_w_m2": 0.9,
        "energy_imbalance_reference_range_w_m2": [0.7, 1.7],
        "energy_imbalance_reference_source": "AR6 WG1 Ch7 / IGCC assessed Earth energy imbalance",
        "equilibrium_climate_sensitivity_c": p.equilibrium_climate_sensitivity,
        "equilibrium_climate_sensitivity_reference": "AR6 best estimate 3.0 C, likely range 2.5-4.0 C",
        "transient_climate_response_c": p.transient_climate_response,
        "transient_climate_response_reference": "AR6 best estimate 1.8 C, likely range 1.4-2.2 C",
    }


# ============================================================================================
# SECTION 3  Endogenous sectoral capital-turnover emissions transition
#   (merged from emissions_transition.py)
# ============================================================================================

from dataclasses import dataclass, asdict
from functools import lru_cache
from typing import Dict, List, Tuple
import math

TRANSITION_START_YEAR = 2026
TRANSITION_END_YEAR = 2400
TOTAL_CO2_ANCHOR_GT = 42.2
ENERGY_CO2_ANCHOR_GT = 38.4
RESIDUAL_FLOOR_GT = 1.5
IEA_NZE_2035_ENERGY_CO2_GT = 18.0

TRANSITION_SOURCES = {
    "IEA_GER_2026": "https://www.iea.org/reports/global-energy-review-2026/co2-emissions",
    "IEA_WEO_2025_NZE": "https://www.iea.org/reports/world-energy-outlook-2025/net-zero-emissions-by-2050",
    "IEA_WEI_2024": "https://www.iea.org/reports/world-energy-investment-2024/overview-and-key-findings",
    "IEA_ELECTRICITY_2025": "https://www.iea.org/reports/electricity-2025/emissions",
}

@dataclass(frozen=True)
class TransitionSector:
    name: str
    energy_related: bool
    anchor_emissions_gt: float
    residual_floor_gt: float
    capital_lifetime_years: float
    full_transition_capex_usd_tn: float
    annual_service_growth: float
    allocation_priority: float
    max_early_retirement_fraction: float
    learning_rate: float

# The sector split below is a transparent screening decomposition constrained to
# the 38.4-Gt energy-related and 42.2-Gt total anchors.  It is not an IEA sector
# table and should not be presented as one.
TRANSITION_SECTORS: Tuple[TransitionSector, ...] = (
    TransitionSector("Power", True, 13.8, 0.10, 30, 20.0, 0.018, 1.20, 0.16, 0.12),
    TransitionSector("Industry", True, 9.2, 0.45, 25, 18.0, 0.012, 1.00, 0.12, 0.10),
    TransitionSector("Road transport", True, 6.1, 0.10, 15, 12.0, 0.015, 1.00, 0.20, 0.15),
    TransitionSector("Buildings", True, 3.0, 0.10, 25, 10.0, 0.012, 0.90, 0.12, 0.12),
    TransitionSector("Aviation and shipping", True, 2.2, 0.35, 25, 10.0, 0.018, 0.70, 0.08, 0.08),
    TransitionSector("Other energy", True, 4.1, 0.25, 20, 10.0, 0.010, 0.90, 0.16, 0.10),
    TransitionSector("Land-use CO2", False, 3.8, 0.15, 30, 8.0, 0.000, 0.70, 0.10, 0.05),
)
assert abs(sum(s.anchor_emissions_gt for s in TRANSITION_SECTORS) - TOTAL_CO2_ANCHOR_GT) < 1e-12
assert abs(sum(s.anchor_emissions_gt for s in TRANSITION_SECTORS if s.energy_related) - ENERGY_CO2_ANCHOR_GT) < 1e-12
assert abs(sum(s.residual_floor_gt for s in TRANSITION_SECTORS) - RESIDUAL_FLOOR_GT) < 1e-12

INVESTMENT_ANCHORS_USD_TN = {2026: 2.0, 2030: 4.0, 2035: 4.8, 2050: 4.0, 2100: 3.0}

# POST-COMPLETION INVESTMENT. transition_piecewise holds the final anchor flat, so
# investment continues at 3.0 USD tn/yr for as long as the run lasts. The weighted dirty
# capital stock reaches zero in 2051, after which that spending converts nothing: with
# dirty[s]=0 both natural_clean and early retirement are zero regardless of allocation.
# Over a 2186 horizon this is ~429 of ~534 USD tn of total transition investment, and it
# is carried as a cost in the advanced economic balance.
#
# That is a modelling CHOICE, not an arithmetic error, and it has two defensible readings:
#
#   "replacement"  the clean system needs ongoing replacement capital indefinitely.
#                  Physically reasonable - but then the no-action comparator must carry
#                  its own fossil replacement capex. It currently carries zero, so on
#                  this reading the programme cost is NOT incremental to the
#                  counterfactual and the net-benefit figures are a lower bound.
#
#   "taper"        the schedule simply never ended. Investment declines to a maintenance
#                  level once the stock is converted, and post-completion spending stops
#                  being charged to the programme.
#
# Audited transition-accounting convention: the anchor schedule is a *gross clean-investment
# opportunity envelope*. Only capital actually allocated to remaining abatable dirty
# stock is charged as incremental transition programme cost. Once the modeled dirty
# stock is fully converted, scheduled replacement investment is ordinary replacement
# capital that the counterfactual also requires and is not charged to restoration.
# Both scheduled and actually allocated investment are reported so the boundary is visible.
POST_COMPLETION_INVESTMENT_MODE = "incremental_only"

@dataclass(frozen=True)
class TransitionCase:
    key: str
    name: str
    investment_multiplier: float = 1.0
    early_retirement_multiplier: float = 0.8
    post_2035_acceleration_multiplier: float = 1.0
    investment_start_delay_years: int = 0
    classification: str = "SCREEN"

TRANSITION_CASES: Dict[str, TransitionCase] = {
    "iea_nze_reference": TransitionCase(
        "iea_nze_reference", "IEA-2025-NZE-calibrated transition reference", 1.0, 0.8, 1.0, 0,
        "Reference reduced-form capital-turnover screen calibrated to IEA 2035 energy-related CO2 and a 2050 residual floor."),
    "high_acceleration": TransitionCase(
        "high_acceleration", "Accelerated capital-turnover design", 1.15, 0.95, 1.25, 0,
        "High-investment / high-early-retirement design stress."),
    "current_investment_constrained": TransitionCase(
        "current_investment_constrained", "Current-investment constrained", 0.68, 0.65, 0.80, 0,
        "Lower-investment transition stress."),
    "natural_turnover": TransitionCase(
        "natural_turnover", "Natural turnover only", 0.45, 0.0, 0.25, 0,
        "Minimal early-retirement stress; decarbonization relies mainly on ordinary asset turnover."),
    "delayed_finance": TransitionCase(
        "delayed_finance", "Delayed-finance stress", 0.75, 0.70, 0.75, 5,
        "Five-year clean-investment delay followed by constrained catch-up."),
}


def transition_piecewise(year: int, anchors: Dict[int, float]) -> float:
    years = sorted(anchors)
    if year <= years[0]: return anchors[years[0]]
    if year >= years[-1]: return anchors[years[-1]]
    for y0, y1 in zip(years, years[1:]):
        if y0 <= year <= y1:
            f = (year-y0)/(y1-y0)
            return anchors[y0] + f*(anchors[y1]-anchors[y0])
    raise RuntimeError("transition_piecewise interpolation failed")


def _transition_raw_run(case: TransitionCase, effectiveness: float, reference_post_multiplier: float,
             end_year: int = TRANSITION_END_YEAR) -> Dict:
    dirty = {s.name: 1.0 for s in TRANSITION_SECTORS}
    cumulative_investment = {s.name: 0.0 for s in TRANSITION_SECTORS}
    rows: List[Dict] = []
    sector_rows: List[Dict] = []
    cum_capital = 0.0
    residual_floor_year = None
    post_target = reference_post_multiplier * case.post_2035_acceleration_multiplier

    for year in range(TRANSITION_START_YEAR, end_year+1):
        if year == TRANSITION_START_YEAR:
            scheduled_investment = 0.0
        elif year <= TRANSITION_START_YEAR + case.investment_start_delay_years:
            scheduled_investment = 0.0
        else:
            shifted_year = year - case.investment_start_delay_years
            scheduled_investment = transition_piecewise(
                max(TRANSITION_START_YEAR, shifted_year), INVESTMENT_ANCHORS_USD_TN
            ) * case.investment_multiplier

        # Acceleration is ramped after 2035 instead of switching discontinuously.
        ramp = max(0.0, min(1.0, (year-2035)/15.0))
        acceleration = 1.0 + (post_target-1.0)*ramp

        # Allocate investment toward high abatement per unit of full-transition capital.
        scores: Dict[str, float] = {}
        for s in TRANSITION_SECTORS:
            potential = s.anchor_emissions_gt * ((1+s.annual_service_growth)**(year-TRANSITION_START_YEAR))
            abatable = max(0.0, (potential-s.residual_floor_gt)*dirty[s.name])
            scores[s.name] = s.allocation_priority * abatable / s.full_transition_capex_usd_tn
        denom = sum(scores.values())
        # Charge only capital that can actually be allocated to remaining abatement.
        # When denom == 0 the clean system may still need ordinary replacement capital,
        # but that is not incremental to the no-action counterfactual.
        investment = scheduled_investment if denom > 1e-15 else 0.0
        cum_capital += investment

        total = 0.0
        energy = 0.0
        dirty_weighted = 0.0
        for s in TRANSITION_SECTORS:
            allocation = investment * scores[s.name]/denom if denom > 0 else 0.0
            cumulative_investment[s.name] += allocation
            initial_learning_scale = max(0.5, 0.03*s.full_transition_capex_usd_tn)
            doublings = math.log(max(1.0, cumulative_investment[s.name]/initial_learning_scale), 2.0) if cumulative_investment[s.name] > initial_learning_scale else 0.0
            learning_factor = max(0.45, (1.0-s.learning_rate)**doublings)
            effective_full_capex = s.full_transition_capex_usd_tn * learning_factor

            if year > TRANSITION_START_YEAR:
                conversion_capacity = allocation/effective_full_capex * effectiveness * acceleration
                natural_opportunity = dirty[s.name] / s.capital_lifetime_years
                natural_clean = min(natural_opportunity, conversion_capacity)
                remaining = max(0.0, conversion_capacity-natural_clean)
                early_cap = s.max_early_retirement_fraction * case.early_retirement_multiplier * acceleration * dirty[s.name]
                early = min(max(0.0, dirty[s.name]-natural_clean), early_cap, remaining)
                dirty[s.name] = max(0.0, dirty[s.name]-natural_clean-early)
                if dirty[s.name] < 0.005:
                    dirty[s.name] = 0.0
            else:
                natural_clean = early = 0.0

            potential = s.anchor_emissions_gt * ((1+s.annual_service_growth)**(year-TRANSITION_START_YEAR))
            emissions = s.residual_floor_gt + (potential-s.residual_floor_gt)*dirty[s.name]
            total += emissions
            if s.energy_related: energy += emissions
            dirty_weighted += dirty[s.name]*s.anchor_emissions_gt/TOTAL_CO2_ANCHOR_GT
            sector_rows.append({
                "year": year, "sector": s.name, "energy_related": s.energy_related,
                "gross_emissions_gtco2": emissions, "dirty_stock_fraction": dirty[s.name],
                "annual_transition_investment_usd_tn": allocation,
                "cumulative_transition_investment_usd_tn": cumulative_investment[s.name],
                "learning_factor": learning_factor, "natural_clean_retirement_fraction": natural_clean,
                "early_retirement_fraction": early,
            })
        if residual_floor_year is None and total <= RESIDUAL_FLOOR_GT + 1e-9:
            residual_floor_year = year
        rows.append({
            "year": year, "gross_emissions_gtco2": total, "energy_related_co2_gtco2": energy,
            "scheduled_clean_investment_envelope_usd_tn": scheduled_investment,
            "transition_investment_usd_tn": investment, "cumulative_transition_capital_usd_tn": cum_capital,
            "weighted_dirty_stock_fraction": dirty_weighted,
        })
    return {"rows": rows, "sector_rows": sector_rows, "residual_floor_year": residual_floor_year,
            "cumulative_transition_capital_to_2050_usd_tn": (next((r["cumulative_transition_capital_usd_tn"] for r in rows if r["year"]==2050), rows[-1]["cumulative_transition_capital_usd_tn"]))}


@lru_cache(maxsize=1)
def transition_reference_calibration() -> Dict:
    # First calibrate investment effectiveness to the IEA 2035 energy-related CO2 anchor.
    lo, hi = 0.1, 3.0
    neutral = TransitionCase("cal", "cal", 1.0, 0.8, 1.0, 0)
    for _ in range(70):
        mid=(lo+hi)/2
        run=_transition_raw_run(neutral, mid, 1.0, 2035)
        e=run["rows"][-1]["energy_related_co2_gtco2"]
        if e > IEA_NZE_2035_ENERGY_CO2_GT: lo=mid
        else: hi=mid
    effectiveness=(lo+hi)/2

    # Then calibrate a smooth post-2035 acceleration so total CO2 reaches the
    # 1.5-Gt residual floor by 2050 under the reference investment envelope.
    lo, hi = 1.0, 12.0
    for _ in range(70):
        mid=(lo+hi)/2
        run=_transition_raw_run(neutral, effectiveness, mid, 2050)
        total=run["rows"][-1]["gross_emissions_gtco2"]
        if total > RESIDUAL_FLOOR_GT + 1e-9: lo=mid
        else: hi=mid
    post=(lo+hi)/2
    return {"investment_effectiveness": effectiveness, "reference_post_2035_acceleration": post,
            "target_2035_energy_related_gtco2": IEA_NZE_2035_ENERGY_CO2_GT,
            "target_2050_total_residual_gtco2": RESIDUAL_FLOOR_GT}


@lru_cache(maxsize=32)
def transition_run_case(case_key: str = "iea_nze_reference", end_year: int = TRANSITION_END_YEAR) -> Dict:
    if case_key not in TRANSITION_CASES: raise KeyError(f"unknown transition case: {case_key}")
    cal=transition_reference_calibration(); case=TRANSITION_CASES[case_key]
    out=_transition_raw_run(case, cal["investment_effectiveness"], cal["reference_post_2035_acceleration"], end_year)
    by={r["year"]:r for r in out["rows"]}
    out.update({
        "case_key": case_key, "case": case.name, "case_parameters": asdict(case),
        "calibration": cal,
        "classification": ("Reduced-form endogenous sectoral capital-turnover and investment-allocation screen. "
                           "The reference is calibrated to the IEA WEO 2025 NZE 2035 energy-related CO2 anchor and a 2050 residual floor; alternative cases reuse the same technology calibration."),
        "validation": {
            "energy_related_co2_2026_gt": by[2026]["energy_related_co2_gtco2"],
            "energy_related_co2_2035_gt": by[2035]["energy_related_co2_gtco2"],
            "energy_related_co2_2035_reference_gt": IEA_NZE_2035_ENERGY_CO2_GT,
            "total_co2_2026_gt": by[2026]["gross_emissions_gtco2"],
        },
        "sources": TRANSITION_SOURCES,
    })
    return out


def transition_emissions_for_year(year: int, case_key: str = "iea_nze_reference") -> float:
    run=transition_run_case(case_key, TRANSITION_END_YEAR)
    return next(r["gross_emissions_gtco2"] for r in run["rows"] if r["year"]==year)


def transition_case_summary() -> List[Dict]:
    out=[]
    for key in TRANSITION_CASES:
        r=transition_run_case(key)
        out.append({
            "case_key":key,"case":r["case"],"residual_floor_year":r["residual_floor_year"],
            "gross_emissions_2030_gtco2":next(x["gross_emissions_gtco2"] for x in r["rows"] if x["year"]==2030),
            "energy_related_co2_2035_gtco2":next(x["energy_related_co2_gtco2"] for x in r["rows"] if x["year"]==2035),
            "cumulative_transition_capital_to_2050_usd_tn":r["cumulative_transition_capital_to_2050_usd_tn"],
        })
    return out


# ============================================================================================
# SECTION 4  FaIR-v2-form state-dependent gas-cycle structural cross-check
#   (merged from fair_form_validation.py)
# ============================================================================================

from dataclasses import dataclass, asdict
from typing import Dict, List, Sequence
import math, random

FAIR_A = (0.2173, 0.2240, 0.2824, 0.2763)
FAIR_TAU = (1.0e9, 394.4, 36.54, 4.304)
FAIR_GTC_PER_PPM = 2.123
FAIR_PREINDUSTRIAL_PPM = 278.0
FAIR_TARGET_PPM = 280.0
IIRF_MAX = 100.0

# Leach et al. 2021 FaIRv2 default carbon-cycle parameters (Table 5).
DEFAULT_R0 = 33.9
DEFAULT_RU = 0.0188
DEFAULT_RT = 2.67
DEFAULT_RA = 0.0

# Approximate cumulative anthropogenic emissions through 2025, GtC.
# GCB2025 gives 745 +/-65 GtC for 1850-2024 plus ~11.5 GtC in 2025.
# Pre-1850 land-use emissions are omitted; this is therefore a warm-start
# approximation and is explicitly varied in the structural fair_form_ensemble.
WARMSTART_CUMULATIVE_GTC = 756.5

FAIR_SOURCES = {
    "FAIR_V2": "https://doi.org/10.5194/gmd-14-3007-2021",
    "FAIR_DOCS": "https://docs.fairmodel.net/en/stable/",
    "FAIR_CALIBRATION": "https://zenodo.org/records/18828694",
    "GCB_2025": "https://essd.copernicus.org/articles/18/3211/2026/",
}

@dataclass(frozen=True)
class FairCarbonParams:
    name: str = "FaIR-v2 default-form central"
    r0: float = DEFAULT_R0
    ru: float = DEFAULT_RU
    rt: float = DEFAULT_RT
    ra: float = DEFAULT_RA
    temperature_anomaly_c: float = 1.5
    cumulative_emissions_start_gtc: float = WARMSTART_CUMULATIVE_GTC
    iirf_max: float = IIRF_MAX


def _fair_g_parameters() -> tuple[float, float]:
    horizon = 100.0
    numerator = 0.0
    g1 = 0.0
    for a, tau in zip(FAIR_A, FAIR_TAU):
        if tau > 1e8:
            numerator += a * horizon
            # infinite lifetime contribution to g1 tends to zero
        else:
            e = math.exp(-horizon / tau)
            numerator += a * tau * (1.0 - e)
            g1 += a * tau * (1.0 - (1.0 + horizon / tau) * e)
    g0 = math.exp(-numerator / g1)
    return g0, g1

G0, G1 = _fair_g_parameters()


def fair_lifetime_scale(cumulative_emissions_gtc: float, gas_boxes_gtc: Sequence[float], p: FairCarbonParams) -> Dict[str, float]:
    airborne = sum(gas_boxes_gtc)
    uptake = cumulative_emissions_gtc - airborne
    iirf = p.r0 + p.ru * uptake + p.rt * p.temperature_anomaly_c + p.ra * airborne
    iirf_capped = max(0.0, min(p.iirf_max, iirf))
    alpha = G0 * math.exp(iirf_capped / G1)
    return {"airborne_gtc": airborne, "uptake_gtc": uptake, "iirf100_years": iirf, "iirf100_capped_years": iirf_capped, "alpha": alpha}


def fair_advance(boxes: Sequence[float], net_flux_gtc_yr: float, cumulative_gtc: float, p: FairCarbonParams, dt: float = 1.0):
    st = fair_lifetime_scale(cumulative_gtc, boxes, p)
    alpha = st["alpha"]
    out = []
    for old, a, tau in zip(boxes, FAIR_A, FAIR_TAU):
        scaled_tau = alpha * tau
        if scaled_tau > 1e8:
            new = old + a * net_flux_gtc_yr * dt
        else:
            decay = math.exp(-dt / scaled_tau)
            new = old * decay + a * net_flux_gtc_yr * scaled_tau * (1.0 - decay)
        out.append(new)
    return out, cumulative_gtc + net_flux_gtc_yr * dt, st


def fair_form_run(net_flux_rows: Sequence[Dict], initial_boxes_gtc: Sequence[float],
        params: FairCarbonParams = FairCarbonParams(),
        temperature_by_year: Dict[int, float] | None = None) -> Dict:
    """Integrate the FaIR-form gas cycle along a prescribed net-flux path.

    ``temperature_by_year`` supplies an endogenous warming trajectory for the
    iIRF100 temperature term. Holding temperature fixed at its present-day value
    for a century-scale drawdown to pre-industrial CO2 is internally inconsistent,
    because warming falls as the concentration falls. When the mapping is absent
    the module falls back to the frozen value in ``params`` and says so.
    """
    boxes = list(initial_boxes_gtc)
    cumulative = params.cumulative_emissions_start_gtc
    rows = []
    peak_ppm = FAIR_PREINDUSTRIAL_PPM + sum(boxes) / FAIR_GTC_PER_PPM
    peak_year = net_flux_rows[0]["year"] if net_flux_rows else None
    crossing = None
    for rec in net_flux_rows:
        net_gtc = rec["net_anthropogenic_gtco2"] / 3.664
        step_params = params
        if temperature_by_year is not None and rec["year"] in temperature_by_year:
            step_params = FairCarbonParams(
                **{**asdict(params), "temperature_anomaly_c": temperature_by_year[rec["year"]]})
        boxes, cumulative, state = fair_advance(boxes, net_gtc, cumulative, step_params)
        ppm = FAIR_PREINDUSTRIAL_PPM + sum(boxes) / FAIR_GTC_PER_PPM
        if ppm > peak_ppm:
            peak_ppm, peak_year = ppm, rec["year"]
        if crossing is None and ppm <= FAIR_TARGET_PPM:
            crossing = rec["year"]
        rows.append({
            "year": rec["year"], "net_anthropogenic_gtco2": rec["net_anthropogenic_gtco2"],
            "co2_ppm": ppm, "alpha_lifetime": state["alpha"],
            "iirf100_years": state["iirf100_years"], "iirf100_capped_years": state["iirf100_capped_years"],
            "cumulative_net_emissions_gtc": cumulative, "airborne_gtc": sum(boxes),
            "cumulative_uptake_gtc": cumulative - sum(boxes),
        })
        if crossing is not None:
            break
    return {
        "classification": "FaIR-v2-form state-dependent carbon-cycle structural cross-check; not the official calibrated/constrained FaIR package",
        "params": asdict(params), "g0": G0, "g1": G1,
        "temperature_treatment": ("endogenous trajectory from the coupled energy-balance module"
                                  if temperature_by_year is not None
                                  else "frozen at the present-day value (internally inconsistent over a drawdown)"),
        "peak_co2_ppm": peak_ppm, "peak_year": peak_year, "crossing_year": crossing,
        "rows": rows, "sources": FAIR_SOURCES,
    }


def fair_form_parameter_cases() -> List[FairCarbonParams]:
    return [
        FairCarbonParams(),
        FairCarbonParams(name="Faster uptake structural case", r0=DEFAULT_R0*(1-0.154), ru=DEFAULT_RU*math.exp(-0.442), rt=DEFAULT_RT*(1-0.615), temperature_anomaly_c=1.2, cumulative_emissions_start_gtc=691.5),
        FairCarbonParams(name="Slower uptake structural case", r0=DEFAULT_R0*(1+0.154), ru=DEFAULT_RU*math.exp(0.442), rt=DEFAULT_RT*(1+0.615), temperature_anomaly_c=2.0, cumulative_emissions_start_gtc=821.5),
    ]


def fair_form_ensemble(net_flux_rows: Sequence[Dict], initial_boxes_gtc: Sequence[float], n: int = 600, seed: int = 20260901) -> Dict:
    rng = random.Random(seed)
    crossing = []
    peak = []
    for i in range(n):
        # Published FaIRv2 prior sampling forms from Leach et al. (2021),
        # combined with an explicit warm-start/temperature structural range.
        r0 = max(1.0, DEFAULT_R0 * rng.gauss(1.0, 0.154))
        ru = DEFAULT_RU * math.exp(rng.gauss(0.0, 0.442))
        rt = max(0.0, DEFAULT_RT * rng.gauss(1.0, 0.615))
        temp = rng.uniform(1.2, 2.0)
        cum = rng.gauss(WARMSTART_CUMULATIVE_GTC, 65.0)
        p = FairCarbonParams(name=f"prior_structural_{i}", r0=r0, ru=ru, rt=rt, temperature_anomaly_c=temp, cumulative_emissions_start_gtc=cum)
        rr = fair_form_run(net_flux_rows, initial_boxes_gtc, p)
        if rr["crossing_year"] is not None:
            crossing.append(rr["crossing_year"])
        peak.append(rr["peak_co2_ppm"])
    crossing.sort(); peak.sort()
    def pct(xs, q):
        if not xs: return None
        pos=(len(xs)-1)*q
        lo=int(math.floor(pos)); hi=int(math.ceil(pos))
        if lo==hi: return xs[lo]
        return xs[lo]+(pos-lo)*(xs[hi]-xs[lo])
    return {
        "classification": "FaIR-v2-form prior structural sensitivity, not an AR6/fastmip posterior probability distribution",
        "n": n, "crossing_year_p05": pct(crossing,0.05), "crossing_year_p50": pct(crossing,0.50), "crossing_year_p95": pct(crossing,0.95),
        "peak_co2_ppm_p05": pct(peak,0.05), "peak_co2_ppm_p50": pct(peak,0.50), "peak_co2_ppm_p95": pct(peak,0.95),
        "n_crossed_by_horizon": len(crossing), "sources": FAIR_SOURCES,
    }


# ============================================================================================
# SECTION 5  Pathway learning curves and scarcity economics
#   (merged from cdr_learning.py)
# ============================================================================================

from dataclasses import dataclass
import math
from typing import Dict


@dataclass(frozen=True)
class EconomicAssumption:
    initial_cost_usd_t: float
    learning_rate: float
    initial_cumulative_gt: float
    floor_cost_usd_t: float
    learnable_cost_share: float
    scarcity_cost_share: float
    scarcity_elasticity: float
    status: str = "MODEL_ASSUMPTION"
    note: str = ""


DEFAULT_LEARNING: Dict[str, EconomicAssumption] = {
    "DACCS": EconomicAssumption(600.0, 0.07, 0.05, 120.0, 0.80, 0.00, 0.0, "LITERATURE_INFORMED_ASSUMPTION",
                                "Whole-system learning assumption; no land-scarcity term."),
    "Enhanced silicate weathering": EconomicAssumption(200.0, 0.03, 0.02, 100.0, 0.35, 0.35, 0.45,
                                note="Manufacturing/logistics learning plus cropland/logistics scarcity."),
    "Ocean alkalinity / carbonate weathering": EconomicAssumption(250.0, 0.05, 0.01, 100.0, 0.50, 0.15, 0.35,
                                note="Learning is scenario-based; feedstock/port scarcity not yet dynamically coupled."),
    "Biochar": EconomicAssumption(160.0, 0.03, 1.00, 70.0, 0.30, 0.50, 0.65,
                                note="Process learning is offset by biomass/feedstock scarcity at high utilization."),
    "BiCRS / BECCS / durable biomass storage": EconomicAssumption(160.0, 0.04, 0.10, 80.0, 0.35, 0.50, 0.75,
                                note="Plant learning plus land, biomass and water scarcity."),
    "Biological restoration": EconomicAssumption(60.0, 0.01, 10.0, 35.0, 0.10, 0.80, 1.00,
                                note="Little manufacturing learning; land/site scarcity dominates marginal cost."),
    "Direct/passive mineral carbonation": EconomicAssumption(200.0, 0.04, 0.02, 100.0, 0.40, 0.25, 0.45,
                                note="Process learning plus mineral/feedstock scarcity; current utilization proxy is incomplete."),
}


def _learning_factor(cumulative_gt: float, a: EconomicAssumption) -> float:
    base = max(a.initial_cumulative_gt, 1e-9)
    ratio = max(1.0, cumulative_gt / base)
    exponent = math.log(1.0 - a.learning_rate) / math.log(2.0)
    return ratio ** exponent


def _scarcity_multiplier(utilization_fraction: float, a: EconomicAssumption) -> float:
    """Convex scarcity multiplier, equal to 1 at zero utilization.

    This is a stress-function, not an estimated supply curve. It rises as the
    relevant land/feedstock/site resource approaches saturation and is capped
    to prevent numerical singularities in global sensitivity runs.
    """
    if a.scarcity_cost_share <= 0.0 or a.scarcity_elasticity <= 0.0:
        return 1.0
    u = min(0.98, max(0.0, utilization_fraction))
    return min(6.0, (1.0 - u) ** (-a.scarcity_elasticity))


def pathway_economic_detail(cumulative_gt: float, utilization_fraction: float, a: EconomicAssumption) -> Dict[str, float]:
    learn_share = a.learnable_cost_share
    scarcity_share = a.scarcity_cost_share
    if learn_share < 0 or scarcity_share < 0 or learn_share + scarcity_share > 1.0 + 1e-12:
        raise ValueError("invalid cost-share decomposition")
    static_share = max(0.0, 1.0 - learn_share - scarcity_share)
    lf = _learning_factor(cumulative_gt, a)
    sm = _scarcity_multiplier(utilization_fraction, a)

    learned_component = a.initial_cost_usd_t * learn_share * lf
    static_component = a.initial_cost_usd_t * static_share
    scarcity_base_component = a.initial_cost_usd_t * scarcity_share
    scarcity_component = scarcity_base_component * sm
    without_scarcity = learned_component + static_component + scarcity_base_component
    total = max(a.floor_cost_usd_t, learned_component + static_component + scarcity_component)

    return {
        "marginal_cost_usd_t": total,
        "cost_without_scarcity_usd_t": max(a.floor_cost_usd_t, without_scarcity),
        "learning_factor": lf,
        "scarcity_multiplier": sm,
        "resource_utilization_fraction": min(1.0, max(0.0, utilization_fraction)),
        "learned_component_usd_t": learned_component,
        "static_component_usd_t": static_component,
        "scarcity_component_usd_t": scarcity_component,
    }


def wright_cost(cumulative_gt: float, a: EconomicAssumption) -> float:
    """Backward-compatible learning-only cost with zero scarcity utilization."""
    return pathway_economic_detail(cumulative_gt, 0.0, a)["marginal_cost_usd_t"]


def pathway_economics(cumulative_deployment_gt: Dict[str, float],
                      resource_utilization: Dict[str, float] | None = None,
                      assumptions: Dict[str, EconomicAssumption] = DEFAULT_LEARNING) -> Dict[str, Dict[str, float]]:
    resource_utilization = resource_utilization or {}
    return {
        k: pathway_economic_detail(
            cumulative_deployment_gt.get(k, a.initial_cumulative_gt),
            resource_utilization.get(k, 0.0),
            a,
        )
        for k, a in assumptions.items()
    }


def pathway_costs(cumulative_deployment_gt: Dict[str, float],
                  resource_utilization: Dict[str, float] | None = None,
                  assumptions: Dict[str, EconomicAssumption] = DEFAULT_LEARNING) -> Dict[str, float]:
    return {k: v["marginal_cost_usd_t"] for k, v in pathway_economics(cumulative_deployment_gt, resource_utilization, assumptions).items()}


# ============================================================================================
# SECTION 6  Food-first land, blue water and biogeophysical constraints
#   (merged from land_nexus.py)
# ============================================================================================

from dataclasses import dataclass, asdict
from typing import Dict, List

EARTH_SURFACE_KM2 = 510.1e6


@dataclass(frozen=True)
class LandUseCase:
    name: str
    agricultural_land_mha: float = 4800.0   # FAOSTAT 2023 anchor
    cropland_baseline_mha: float = 1600.0
    pasture_baseline_mha: float = 3200.0
    population_start_billion: float = 8.3
    population_planning_billion: float = 10.3
    population_planning_year: int = 2085
    crop_yield_multiplier_2050: float = 1.35
    livestock_land_intensity_2050: float = 0.70

    # FAO AQUASTAT screening anchors. These are current global irrigation
    # requirement/withdrawal quantities, not claims of sustainable availability.
    irrigated_area_baseline_mha: float = 261.0
    irrigation_requirement_baseline_km3_yr: float = 1500.0
    irrigation_withdrawal_baseline_km3_yr: float = 2673.0
    food_water_productivity_multiplier_2050: float = 1.20

    # Land-dependent CDR assumptions.
    biochar_dedicated_biomass_fraction: float = 0.10
    beccs_dedicated_biomass_fraction: float = 0.50
    dedicated_biomass_yield_t_ha_yr: float = 15.0
    biological_restoration_net_tco2_ha_yr: float = 5.0
    ew_rock_net_tco2_per_t_rock: float = 0.15
    ew_application_t_ha_yr: float = 20.0
    ew_adoptable_cropland_fraction: float = 0.50

    # Supplemental irrigation for dedicated biomass. The hard screen is based on
    # the IPCC-reviewed order-of-magnitude BECCS water impact (~183 km3/yr in a
    # low-overshoot pathway), used here only as a stress anchor.
    biomass_irrigated_fraction: float = 0.15
    biomass_irrigation_m3_ha_yr: float = 3000.0
    incremental_cdr_blue_water_screen_km3_yr: float = 183.0

    # Restoration is assumed rainfed for credited CDR in the central case. Its
    # change in ET is reported diagnostically because P-E effects are location-specific.
    restoration_supplemental_irrigated_fraction: float = 0.0
    restoration_supplemental_irrigation_m3_ha_yr: float = 0.0
    restoration_et_increment_mm_yr: float = 100.0

    # New boreal afforestation is excluded from credited central biological CDR.
    # An explicit stress diagnostic quantifies the *uncompensated albedo-only*
    # forcing if a stated fraction were instead located in boreal/snow regions.
    credited_new_boreal_afforestation_fraction: float = 0.0
    albedo_stress_boreal_fraction: float = 0.10
    boreal_local_albedo_forcing_w_m2: float = 2.3


LAND_CASES: Dict[str, LandUseCase] = {
    "central": LandUseCase("central"),
    "low_efficiency": LandUseCase(
        "low_efficiency",
        crop_yield_multiplier_2050=1.15,
        livestock_land_intensity_2050=0.85,
        food_water_productivity_multiplier_2050=1.05,
        dedicated_biomass_yield_t_ha_yr=12.0,
        biological_restoration_net_tco2_ha_yr=4.0,
        ew_adoptable_cropland_fraction=0.40,
        biomass_irrigated_fraction=0.25,
        biomass_irrigation_m3_ha_yr=4000.0,
        incremental_cdr_blue_water_screen_km3_yr=150.0,
        restoration_et_increment_mm_yr=150.0,
        albedo_stress_boreal_fraction=0.20,
    ),
    "high_efficiency": LandUseCase(
        "high_efficiency",
        crop_yield_multiplier_2050=1.50,
        livestock_land_intensity_2050=0.60,
        food_water_productivity_multiplier_2050=1.35,
        dedicated_biomass_yield_t_ha_yr=18.0,
        biological_restoration_net_tco2_ha_yr=6.0,
        ew_adoptable_cropland_fraction=0.60,
        biomass_irrigated_fraction=0.10,
        biomass_irrigation_m3_ha_yr=2500.0,
        incremental_cdr_blue_water_screen_km3_yr=220.0,
        restoration_et_increment_mm_yr=75.0,
        albedo_stress_boreal_fraction=0.05,
    ),
}

LAND_DEPENDENT = {"Biochar", "BiCRS / BECCS / durable biomass storage", "Biological restoration"}


def _lerp(year: int, y0: int, y1: int, v0: float, v1: float) -> float:
    if year <= y0:
        return v0
    if year >= y1:
        return v1
    return v0 + (v1 - v0) * (year - y0) / (y1 - y0)


def food_land(year: int, c: LandUseCase) -> Dict[str, float]:
    pop = _lerp(year, 2026, c.population_planning_year, c.population_start_billion, c.population_planning_billion)
    yield_mult = _lerp(year, 2026, 2050, 1.0, c.crop_yield_multiplier_2050)
    livestock_intensity = _lerp(year, 2026, 2050, 1.0, c.livestock_land_intensity_2050)
    water_productivity = _lerp(year, 2026, 2050, 1.0, c.food_water_productivity_multiplier_2050)
    pop_ratio = pop / c.population_start_billion

    cropland = c.cropland_baseline_mha * pop_ratio / yield_mult
    pasture = c.pasture_baseline_mha * pop_ratio * livestock_intensity
    food_total = cropland + pasture
    remaining = max(0.0, c.agricultural_land_mha - food_total)

    # Global-scale screening estimate: keep the current irrigated share embedded in
    # the baseline and scale water requirement/withdrawal with cropland and a stated
    # water-productivity improvement. This is not a basin allocation.
    cropland_ratio = cropland / c.cropland_baseline_mha if c.cropland_baseline_mha else 0.0
    irrigation_requirement = c.irrigation_requirement_baseline_km3_yr * cropland_ratio / water_productivity
    irrigation_withdrawal = c.irrigation_withdrawal_baseline_km3_yr * cropland_ratio / water_productivity

    return {
        "population_billion": pop,
        "crop_yield_multiplier": yield_mult,
        "livestock_land_intensity_factor": livestock_intensity,
        "food_water_productivity_multiplier": water_productivity,
        "food_cropland_mha": cropland,
        "food_pasture_mha": pasture,
        "food_agricultural_land_mha": food_total,
        "remaining_agricultural_land_mha": remaining,
        "food_land_deficit_mha": max(0.0, food_total - c.agricultural_land_mha),
        "screened_food_irrigation_requirement_km3_yr": irrigation_requirement,
        "screened_food_irrigation_withdrawal_km3_yr": irrigation_withdrawal,
    }


def _biomass_land_and_water(pathway: str, cdr_gt: float, c: LandUseCase) -> Dict[str, float]:
    if pathway == "Biochar":
        net = 0.50 * 0.30 * 0.80 * (44.0 / 12.0)
        biomass_gt = cdr_gt / net if net else 0.0
        dedicated = biomass_gt * c.biochar_dedicated_biomass_fraction
    elif pathway == "BiCRS / BECCS / durable biomass storage":
        net = 0.50 * 0.90 * (44.0 / 12.0)
        biomass_gt = cdr_gt / net if net else 0.0
        dedicated = biomass_gt * c.beccs_dedicated_biomass_fraction
    else:
        return {"land_mha": 0.0, "blue_water_km3_yr": 0.0, "dedicated_biomass_gt_yr": 0.0}
    land_mha = dedicated * 1000.0 / c.dedicated_biomass_yield_t_ha_yr
    blue_water = land_mha * 1e6 * c.biomass_irrigated_fraction * c.biomass_irrigation_m3_ha_yr / 1e9
    return {"land_mha": land_mha, "blue_water_km3_yr": blue_water, "dedicated_biomass_gt_yr": dedicated}


def _restoration_water_and_biophysics(restoration_land_mha: float, c: LandUseCase) -> Dict[str, float]:
    supplemental_blue = (
        restoration_land_mha * 1e6 * c.restoration_supplemental_irrigated_fraction
        * c.restoration_supplemental_irrigation_m3_ha_yr / 1e9
    )
    # 1 mm over 1 Mha = 0.01 km3.
    et_increment = restoration_land_mha * c.restoration_et_increment_mm_yr * 0.01
    boreal_stress_area_mha = restoration_land_mha * c.albedo_stress_boreal_fraction
    boreal_stress_area_km2 = boreal_stress_area_mha * 1e4
    global_mean_albedo_only_forcing = (
        c.boreal_local_albedo_forcing_w_m2 * boreal_stress_area_km2 / EARTH_SURFACE_KM2
    )
    return {
        "supplemental_blue_water_km3_yr": supplemental_blue,
        "et_increment_diagnostic_km3_yr": et_increment,
        "boreal_albedo_stress_area_mha": boreal_stress_area_mha,
        "uncompensated_boreal_albedo_only_global_forcing_w_m2": global_mean_albedo_only_forcing,
    }


def constrain_portfolio(year: int, rows: List[Dict], c: LandUseCase) -> Dict:
    """Return a portfolio adjusted to land and blue-water stress screens.

    Allocation order:
      1) food land is protected;
      2) enhanced weathering may co-use only an adoptable cropland share;
      3) dedicated biomass + biological restoration share residual agricultural land;
      4) additional managed blue-water use is capped by a literature-informed CDR
         stress screen;
      5) hydrological ET and boreal albedo are reported diagnostically, not converted
         to universal CO2-equivalent penalties.
    """
    food = food_land(year, c)
    adjusted = [dict(r) for r in rows]

    # 1) Enhanced-weathering cropland co-use.
    ew_scale = 1.0
    for r in adjusted:
        if r["pathway"] == "Enhanced silicate weathering":
            rock_gt = r["cdr_gtco2_yr"] / c.ew_rock_net_tco2_per_t_rock if c.ew_rock_net_tco2_per_t_rock else 0.0
            area_mha = rock_gt * 1000.0 / c.ew_application_t_ha_yr
            adoptable = min(c.cropland_baseline_mha, food["food_cropland_mha"]) * c.ew_adoptable_cropland_fraction
            ew_scale = min(1.0, adoptable / area_mha) if area_mha > 0 else 1.0
            r["cdr_gtco2_yr"] *= ew_scale
            r["land_constraint_scale"] = ew_scale
            r["ew_spreading_area_mha"] = area_mha * ew_scale
            r["ew_adoptable_cropland_mha"] = adoptable
            r["resource_utilization_fraction"] = min(0.999, (area_mha * ew_scale / adoptable) if adoptable > 0 else 0.999)

    # 2) Land conversion and managed blue-water demand before common constraints.
    land_demand = 0.0
    blue_water_demand = 0.0
    per_path: Dict[str, Dict[str, float]] = {}
    remaining = food["remaining_agricultural_land_mha"]
    for r in adjusted:
        p = r["pathway"]
        if p in ("Biochar", "BiCRS / BECCS / durable biomass storage"):
            bw = _biomass_land_and_water(p, r["cdr_gtco2_yr"], c)
            per_path[p] = bw
            land_demand += bw["land_mha"]
            blue_water_demand += bw["blue_water_km3_yr"]
        elif p == "Biological restoration":
            land = r["cdr_gtco2_yr"] * 1000.0 / c.biological_restoration_net_tco2_ha_yr
            rw = _restoration_water_and_biophysics(land, c)
            per_path[p] = {
                "land_mha": land,
                "blue_water_km3_yr": rw["supplemental_blue_water_km3_yr"],
                "dedicated_biomass_gt_yr": 0.0,
            }
            land_demand += land
            blue_water_demand += rw["supplemental_blue_water_km3_yr"]

    land_scale = min(1.0, remaining / land_demand) if land_demand > 0 else 1.0
    blue_after_land = blue_water_demand * land_scale
    water_scale = (
        min(1.0, c.incremental_cdr_blue_water_screen_km3_yr / blue_after_land)
        if blue_after_land > 0 else 1.0
    )

    for r in adjusted:
        p = r["pathway"]
        if p in LAND_DEPENDENT:
            scale = land_scale
            # Blue-water scarcity constrains only pathways that actually require
            # managed supplemental irrigation. Rainfed restoration is not reduced
            # merely because dedicated biomass irrigation is water-limited.
            if p in ("Biochar", "BiCRS / BECCS / durable biomass storage"):
                scale *= water_scale
            elif p == "Biological restoration" and c.restoration_supplemental_irrigated_fraction > 0:
                scale *= water_scale
            r["cdr_gtco2_yr"] *= scale
            r["land_constraint_scale"] = r.get("land_constraint_scale", 1.0) * scale

    # 3) Recompute realized resource use and attach pathway scarcity utilization.
    realized_land = realized_blue = restoration_land = dedicated_land = 0.0
    restoration_diag = _restoration_water_and_biophysics(0.0, c)
    for r in adjusted:
        p = r["pathway"]
        util = r.get("resource_utilization_fraction", 0.0)
        if p in ("Biochar", "BiCRS / BECCS / durable biomass storage"):
            bw = _biomass_land_and_water(p, r["cdr_gtco2_yr"], c)
            realized_land += bw["land_mha"]
            dedicated_land += bw["land_mha"]
            realized_blue += bw["blue_water_km3_yr"]
            land_u = bw["land_mha"] / remaining if remaining > 0 else (1.0 if bw["land_mha"] > 0 else 0.0)
            water_u = bw["blue_water_km3_yr"] / c.incremental_cdr_blue_water_screen_km3_yr if c.incremental_cdr_blue_water_screen_km3_yr > 0 else 0.0
            util = min(0.999, max(land_u, water_u))
        elif p == "Biological restoration":
            land = r["cdr_gtco2_yr"] * 1000.0 / c.biological_restoration_net_tco2_ha_yr
            restoration_land += land
            realized_land += land
            restoration_diag = _restoration_water_and_biophysics(restoration_land, c)
            realized_blue += restoration_diag["supplemental_blue_water_km3_yr"]
            util = min(0.999, land / remaining if remaining > 0 else (1.0 if land > 0 else 0.0))
            r["credited_new_boreal_afforestation_fraction"] = c.credited_new_boreal_afforestation_fraction
        r["resource_utilization_fraction"] = util
        r["resource_scarcity_binding"] = util >= 0.95

    water_utilization = (
        realized_blue / c.incremental_cdr_blue_water_screen_km3_yr
        if c.incremental_cdr_blue_water_screen_km3_yr > 0 else 0.0
    )

    # Enhanced weathering co-uses cropland rather than converting residual land, so it
    # never enters the land_scale test above. Its spreading footprint is large and close
    # to its adoptable-area limit, so it is surfaced explicitly here.
    ew_row = next((r for r in adjusted if r["pathway"] == "Enhanced silicate weathering"), None)
    ew_area = ew_row.get("ew_spreading_area_mha", 0.0) if ew_row else 0.0
    ew_adoptable = ew_row.get("ew_adoptable_cropland_mha", 0.0) if ew_row else 0.0

    return {
        "ew_spreading_area_mha": ew_area,
        "ew_adoptable_cropland_mha": ew_adoptable,
        "ew_share_of_food_cropland_fraction": (
            ew_area / food["food_cropland_mha"] if food["food_cropland_mha"] > 0 else 0.0),
        "ew_adoptable_area_utilization_fraction": (ew_area/ew_adoptable) if ew_adoptable > 0 else 0.0,
        "year": year,
        "case": asdict(c),
        "food": food,
        "unconstrained_cdr_land_mha": land_demand,
        "realized_cdr_land_mha": realized_land,
        "dedicated_biomass_land_mha": dedicated_land,
        "biological_restoration_land_mha": restoration_land,
        "unconstrained_incremental_blue_water_km3_yr": blue_water_demand,
        "realized_incremental_blue_water_km3_yr": realized_blue,
        "incremental_blue_water_screen_km3_yr": c.incremental_cdr_blue_water_screen_km3_yr,
        "incremental_blue_water_utilization_fraction": water_utilization,
        "restoration_et_increment_diagnostic_km3_yr": restoration_diag["et_increment_diagnostic_km3_yr"],
        "boreal_albedo_stress_area_mha": restoration_diag["boreal_albedo_stress_area_mha"],
        "uncompensated_boreal_albedo_only_global_forcing_w_m2": restoration_diag["uncompensated_boreal_albedo_only_global_forcing_w_m2"],
        "land_scale": land_scale,
        "water_scale": water_scale,
        "adjusted_rows": adjusted,
        "effective_total_cdr_gtco2": sum(r["cdr_gtco2_yr"] for r in adjusted),
        "binding": food["food_land_deficit_mha"] > 0 or land_scale < 0.999999 or water_scale < 0.999999 or ew_scale < 0.999999,
        "interpretation": (
            "Global feasibility screen. Food land is protected and incremental managed CDR blue-water use is stress-tested. "
            "Restoration ET and boreal albedo are diagnostics only; publication-grade claims require gridded land suitability, biodiversity and basin hydrology."
        ),
    }


# ============================================================================================
# SECTION 7  Timber-reference reserve redemption stress
#   (merged from monetary_stress.py)
# ============================================================================================

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class MonetaryCase:
    name: str
    timber_index_change: float
    total_reserve_ratio: float
    liquid_reserve_share: float
    liquid_asset_haircut: float
    redemption_fraction: float
    timber_orderly_liquidation_fraction: float
    fire_sale_discount: float
    emergency_liquidity_ratio: float = 0.0
    stress_window_days: int = 5


MONETARY_DEFAULT_CASES = [
    MonetaryCase("Base", 0.00, 1.10, 0.70, 0.00, 0.10, 0.05, 0.10, 0.00, 5),
    MonetaryCase("Timber +30%, moderate redemption", 0.30, 1.10, 0.65, 0.03, 0.25, 0.05, 0.20, 0.05, 5),
    MonetaryCase("Timber -30%, moderate redemption", -0.30, 1.10, 0.65, 0.05, 0.25, 0.05, 0.20, 0.05, 5),
    MonetaryCase("Liquidity shock", 0.00, 1.00, 0.45, 0.10, 0.40, 0.03, 0.40, 0.10, 5),
    MonetaryCase("Severe combined", 0.30, 0.75, 0.20, 0.15, 0.65, 0.01, 0.60, 0.05, 5),
    MonetaryCase("Thirty-day run", -0.20, 1.00, 0.45, 0.08, 0.60, 0.15, 0.35, 0.10, 30),
]


def simulate_case(case: MonetaryCase, supply_units: float = 100.0,
                  base_reference_usd_per_unit: float = 1.0,
                  minimum_post_redemption_net_reserve_ratio: float = 1.0,
                  allowed_redemption_discount_fraction: float = 0.02) -> Dict:
    reference = base_reference_usd_per_unit * (1.0 + case.timber_index_change)
    if reference <= 0:
        raise ValueError("timber reference must remain positive")

    initial_token_liability = supply_units * reference
    total_reserve_mark = initial_token_liability * case.total_reserve_ratio
    liquid_reserve_mark = total_reserve_mark * case.liquid_reserve_share
    timber_reserve_mark = total_reserve_mark - liquid_reserve_mark

    liquid_cash_available = liquid_reserve_mark * (1.0 - case.liquid_asset_haircut)
    emergency_credit_limit = initial_token_liability * case.emergency_liquidity_ratio
    redemption_units_requested = supply_units * case.redemption_fraction
    redemption_claim = redemption_units_requested * reference

    # Pay from liquid reserve first.
    paid_from_liquid = min(redemption_claim, liquid_cash_available)
    remaining_claim = redemption_claim - paid_from_liquid
    remaining_liquid = liquid_cash_available - paid_from_liquid

    # Then draw emergency credit; this is a liability, not free capital.
    emergency_draw = min(remaining_claim, emergency_credit_limit)
    remaining_claim -= emergency_draw

    # Timber can be sold in an orderly amount within the stress window.
    orderly_timber_mark_capacity = timber_reserve_mark * case.timber_orderly_liquidation_fraction
    orderly_timber_mark_sold = min(remaining_claim, orderly_timber_mark_capacity)
    orderly_timber_cash = orderly_timber_mark_sold
    remaining_claim -= orderly_timber_cash
    remaining_timber_mark = timber_reserve_mark - orderly_timber_mark_sold

    # If redemption continues, forced timber sales realize only the haircut value.
    if remaining_claim > 0 and remaining_timber_mark > 0:
        realization_rate = max(0.0, 1.0 - case.fire_sale_discount)
        timber_mark_needed = remaining_claim / realization_rate if realization_rate > 0 else float("inf")
        fire_sale_timber_mark_sold = min(remaining_timber_mark, timber_mark_needed)
        fire_sale_cash = fire_sale_timber_mark_sold * realization_rate
    else:
        fire_sale_timber_mark_sold = 0.0
        fire_sale_cash = 0.0
    remaining_claim = max(0.0, remaining_claim - fire_sale_cash)
    remaining_timber_mark -= fire_sale_timber_mark_sold

    redemption_paid = paid_from_liquid + emergency_draw + orderly_timber_cash + fire_sale_cash
    coverage = 1.0 if redemption_claim <= 0 else min(1.0, redemption_paid / redemption_claim)
    effective_redemption_price = reference * coverage

    redeemed_units_paid = redemption_paid / reference
    remaining_units = max(0.0, supply_units - redeemed_units_paid)
    remaining_token_liability = remaining_units * reference

    # Net reserve assets deduct emergency borrowing as a senior liability.
    remaining_net_assets = max(0.0, remaining_liquid + remaining_timber_mark - emergency_draw)
    post_net_reserve_ratio = (
        float("inf") if remaining_token_liability <= 0 else remaining_net_assets / remaining_token_liability
    )

    minimum_price = reference * (1.0 - allowed_redemption_discount_fraction)
    pass_liquidity = (
        coverage >= 0.999999
        and effective_redemption_price >= minimum_price
        and post_net_reserve_ratio >= minimum_post_redemption_net_reserve_ratio
    )

    return {
        "case": case.name,
        "stress_window_days": case.stress_window_days,
        "timber_index_change_fraction": case.timber_index_change,
        "reference_usd_per_unit": reference,
        "total_reserve_ratio": case.total_reserve_ratio,
        "liquid_reserve_share": case.liquid_reserve_share,
        "liquid_asset_haircut_fraction": case.liquid_asset_haircut,
        "timber_orderly_liquidation_fraction": case.timber_orderly_liquidation_fraction,
        "fire_sale_discount_fraction": case.fire_sale_discount,
        "emergency_liquidity_ratio": case.emergency_liquidity_ratio,
        "redemption_fraction_supply": case.redemption_fraction,
        "redemption_claim_usd_per_100_units": redemption_claim,
        "paid_from_liquid_usd": paid_from_liquid,
        "emergency_credit_draw_usd": emergency_draw,
        "orderly_timber_cash_usd": orderly_timber_cash,
        "fire_sale_timber_cash_usd": fire_sale_cash,
        "redemption_coverage_fraction": coverage,
        "effective_redemption_price_usd_per_unit": effective_redemption_price,
        "effective_price_fraction_of_reference": effective_redemption_price / reference,
        "post_redemption_net_reserve_ratio": post_net_reserve_ratio,
        "liquidity_test_pass": pass_liquidity,
    }


def monetary_stress_table(cases: List[MonetaryCase] = MONETARY_DEFAULT_CASES) -> Dict:
    rows = [simulate_case(c) for c in cases]
    return {
        "reference_rule": "USD reference value moves with the timber index; redemption is tested against that moving reference rather than a fixed $1.",
        "reserve_rule": "Liquid reserves and illiquid timber reserves are separated; emergency liquidity is debt and forced timber sales incur a fire-sale discount.",
        "rows": rows,
        "all_cases_pass": all(r["liquidity_test_pass"] for r in rows),
        "failed_cases": [r["case"] for r in rows if not r["liquidity_test_pass"]],
        "status": "Liquidity/redemption stress screen only. It does not prove purchasing-power stability, reserve quality, convertibility, monetary-policy credibility or legal adoption.",
    }


# ============================================================================================
# SECTION 8  Settlement fee-base, leakage and collection stress
#   (merged from settlement_collection.py)
# ============================================================================================

from dataclasses import dataclass, asdict
from typing import Dict, List
import math

@dataclass(frozen=True)
class SettlementCase:
    name: str
    turnover_multiple_of_gdp: float
    exempt_transaction_share: float
    baseline_retained_share: float
    fee_semi_elasticity: float
    max_fee_fraction: float = 0.03

SETTLEMENT_COLLECTION_CASES = [
    SettlementCase("Central collection", 8.0, 0.25, 0.90, 20.0, 0.03),
    SettlementCase("Lower turnover / higher leakage", 3.0, 0.40, 0.70, 35.0, 0.03),
    SettlementCase("High turnover / low leakage", 12.0, 0.20, 0.95, 12.0, 0.03),
    SettlementCase("Severe migration stress", 1.5, 0.50, 0.50, 60.0, 0.03),
]

SETTLEMENT_SOURCES = {
    "classification": "Author-defined collection stress mechanics; turnover and elasticity parameters require empirical payment-network calibration before macroeconomic claims.",
}

def retained_share(fee_fraction: float, case: SettlementCase) -> float:
    return max(0.0, min(1.0, case.baseline_retained_share * math.exp(-case.fee_semi_elasticity * max(0.0, fee_fraction))))


def annual_collection_usd_tn(fee_fraction: float, gdp_usd_tn: float, case: SettlementCase) -> float:
    gross_turnover = gdp_usd_tn * case.turnover_multiple_of_gdp
    non_exempt = gross_turnover * (1.0 - case.exempt_transaction_share)
    retained = non_exempt * retained_share(fee_fraction, case)
    return fee_fraction * retained


def solve_required_fee(target_usd_tn: float, gdp_usd_tn: float, case: SettlementCase) -> Dict:
    if target_usd_tn < 0 or gdp_usd_tn <= 0:
        raise ValueError("target must be non-negative and GDP positive")
    if target_usd_tn == 0:
        return {"case": case.name, "required_fee_fraction": 0.0, "retained_share": case.baseline_retained_share,
                "collection_usd_tn": 0.0, "shortfall_usd_tn": 0.0, "funding_fraction": 1.0, "pass": True}

    # Find the lowest fee that reaches the target. Collection can be non-monotonic
    # because leakage accelerates with the fee, so search a fine grid first.
    ngrid = 6000
    fees = [case.max_fee_fraction * i / ngrid for i in range(ngrid + 1)]
    vals = [annual_collection_usd_tn(f, gdp_usd_tn, case) for f in fees]
    max_idx = max(range(len(vals)), key=lambda i: vals[i])
    max_collection = vals[max_idx]
    if max_collection + 1e-12 < target_usd_tn:
        f = fees[max_idx]
        return {
            "case": case.name, "required_fee_fraction": None, "best_fee_fraction": f,
            "retained_share": retained_share(f, case), "collection_usd_tn": max_collection,
            "shortfall_usd_tn": target_usd_tn - max_collection,
            "funding_fraction": max_collection / target_usd_tn if target_usd_tn else 1.0,
            "pass": False, "max_fee_fraction": case.max_fee_fraction,
            "turnover_multiple_of_gdp": case.turnover_multiple_of_gdp,
            "exempt_transaction_share": case.exempt_transaction_share,
            "fee_semi_elasticity": case.fee_semi_elasticity,
        }

    # First bracket where collection crosses target; bisection for low-fee root.
    hi_idx = next(i for i, v in enumerate(vals) if v >= target_usd_tn)
    lo = fees[max(0, hi_idx - 1)]; hi = fees[hi_idx]
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if annual_collection_usd_tn(mid, gdp_usd_tn, case) >= target_usd_tn:
            hi = mid
        else:
            lo = mid
    fee = hi
    coll = annual_collection_usd_tn(fee, gdp_usd_tn, case)
    return {
        "case": case.name, "required_fee_fraction": fee, "best_fee_fraction": fee,
        "retained_share": retained_share(fee, case), "collection_usd_tn": coll,
        "shortfall_usd_tn": max(0.0, target_usd_tn - coll),
        "funding_fraction": min(1.0, coll / target_usd_tn if target_usd_tn else 1.0),
        "pass": True, "max_fee_fraction": case.max_fee_fraction,
        "turnover_multiple_of_gdp": case.turnover_multiple_of_gdp,
        "exempt_transaction_share": case.exempt_transaction_share,
        "fee_semi_elasticity": case.fee_semi_elasticity,
    }


def settlement_collection_stress_table(target_usd_tn: float, gdp_usd_tn: float, cases: List[SettlementCase] = SETTLEMENT_COLLECTION_CASES) -> Dict:
    rows = []
    for c in cases:
        r = solve_required_fee(target_usd_tn, gdp_usd_tn, c)
        r.update(asdict(c))
        rows.append(r)
    return {
        "target_usd_tn": target_usd_tn, "gdp_usd_tn": gdp_usd_tn, "rows": rows,
        "failed_cases": [r["case"] for r in rows if not r["pass"]],
        "classification": SETTLEMENT_SOURCES["classification"],
    }


def settlement_collection_annual_ramp(finance_rows: List[Dict], case: SettlementCase) -> List[Dict]:
    out = []
    for r in finance_rows:
        solved = solve_required_fee(r["dynamic_cdr_spend_usd_tn"], r["gdp_screen_usd_tn"], case)
        out.append({"year": r["year"], "cdr_spend_usd_tn": r["dynamic_cdr_spend_usd_tn"], "gdp_usd_tn": r["gdp_screen_usd_tn"], **solved})
    return out


def settlement_maximum_collection(gdp_usd_tn: float, case: SettlementCase) -> Dict:
    """Return the fee and collection at the top of the case's Laffer-like curve."""
    if gdp_usd_tn <= 0:
        raise ValueError("GDP must be positive")
    # For f*exp(-e f), the unconstrained maximum occurs at 1/e.  The baseline
    # retained share and exempt/turnover terms are multiplicative constants.
    if case.fee_semi_elasticity > 0:
        fee=min(case.max_fee_fraction,1.0/case.fee_semi_elasticity)
    else:
        fee=case.max_fee_fraction
    coll=annual_collection_usd_tn(fee,gdp_usd_tn,case)
    return {
        "case":case.name,"fee_at_max_collection_fraction":fee,
        "max_collection_usd_tn":coll,"retained_share_at_max":retained_share(fee,case),
        "turnover_multiple_of_gdp":case.turnover_multiple_of_gdp,
        "exempt_transaction_share":case.exempt_transaction_share,
        "max_fee_fraction":case.max_fee_fraction,
    }


# ============================================================================================
# SECTION 9  Synthetic 8760-hour clean-power adequacy stress
#   (merged from grid_reliability.py)
# ============================================================================================

from dataclasses import dataclass, asdict
from typing import Dict, List
import math

HOURS = 8760

@dataclass(frozen=True)
class GridCase:
    name: str
    solar_energy_share: float
    wind_energy_share: float
    firm_clean_energy_share: float
    vre_overbuild: float = 1.0
    storage_energy_hours_avg_load: float = 24.0
    storage_power_multiple_avg_load: float = 1.0
    roundtrip_efficiency: float = 0.85
    firm_capacity_factor: float = 0.85
    warmup_years: int = 5

# These cases are deliberately a stress set, not recommendations. At least one
# underbuilt case is retained so the module can fail rather than being tuned to
# universal adequacy.
GRID_DEFAULT_CASES = [
    GridCase("Underbuilt VRE / 12h storage", 0.50, 0.40, 0.10, 1.05, 12.0, 1.0),
    GridCase("Balanced / 72h storage", 0.40, 0.35, 0.25, 1.18, 72.0, 1.25),
    GridCase("Firm-rich / 48h storage", 0.30, 0.25, 0.45, 1.12, 48.0, 1.20),
    GridCase("VRE-heavy / 7d storage", 0.50, 0.40, 0.10, 1.22, 168.0, 1.25),
]


def _grid_profiles():
    demand=[]; solar=[]; wind=[]
    for h in range(HOURS):
        day=h//24; hod=h%24
        # Representative macroregion: seasonal + evening demand peak.
        seasonal=1.0+0.10*math.cos(2*math.pi*(day-15)/365.0)
        diurnal=1.0+0.08*math.cos(2*math.pi*(hod-19)/24.0)
        weekend=0.96 if (day%7) in (5,6) else 1.0
        demand.append(seasonal*diurnal*weekend)

        daylight=math.sin(math.pi*(hod-6)/12.0) if 6 <= hod <= 18 else 0.0
        solar_season=max(0.55,0.82+0.18*math.sin(2*math.pi*(day-80)/365.0))
        solar.append(max(0.0,daylight)*solar_season)

        # Multi-timescale deterministic wind variability, including multi-day lulls.
        w=(0.42 + 0.08*math.sin(2*math.pi*day/9.0) + 0.07*math.sin(2*math.pi*day/31.0+1.2)
           +0.05*math.sin(2*math.pi*day/365.0+0.4) + 0.03*math.sin(2*math.pi*hod/24.0+2.0))
        if (day % 53) in (0,1,2):
            w *= 0.50
        wind.append(max(0.05,min(0.78,w)))
    dm=sum(demand)/HOURS
    demand=[x/dm for x in demand]
    return demand,solar,wind

DEMAND_SHAPE,SOLAR_CF,WIND_CF=_grid_profiles()


def _dispatch_one_year(demand, solar_gw, wind_gw, firm_gw, firm_budget_gwh,
                       storage_cap_gwh, storage_power_gw, eta, initial_soc_gwh,
                       collect: bool):
    """Dispatch one repeating synthetic weather year.

    VRE serves load first. Dispatchable firm clean generation then serves the
    residual deficit subject to both its nameplate limit and remaining annual
    energy budget. Storage covers the remaining deficit and absorbs VRE surplus.
    This order avoids the earlier accounting artifact in which storage was
    emptied while firm annual energy went unused.
    """
    soc=max(0.0,min(storage_cap_gwh,initial_soc_gwh))
    firm_remaining=max(0.0,firm_budget_gwh)
    metrics={
        "unserved_gwh":0.0,"unserved_hours":0,"max_shortfall_gw":0.0,
        "curtailment_gwh":0.0,"firm_generation_gwh":0.0,
        "storage_charge_input_gwh":0.0,"storage_discharge_to_load_gwh":0.0,
        "storage_conversion_loss_gwh":0.0,"min_soc_gwh":soc,"max_soc_gwh":soc,
    }
    for h in range(HOURS):
        load=demand[h]
        vre=solar_gw*SOLAR_CF[h]+wind_gw*WIND_CF[h]
        if vre >= load:
            surplus=vre-load
            charge_input=min(surplus, storage_power_gw,
                             (storage_cap_gwh-soc)/eta if eta>0 else 0.0)
            soc += charge_input*eta
            if collect:
                metrics["storage_charge_input_gwh"] += charge_input
                metrics["storage_conversion_loss_gwh"] += charge_input*(1.0-eta)
                metrics["curtailment_gwh"] += max(0.0,surplus-charge_input)
        else:
            deficit=load-vre
            # Firm first: it has both a power limit and an annual energy budget.
            firm=min(deficit,firm_gw,firm_remaining)
            deficit-=firm
            firm_remaining-=firm
            if collect:
                metrics["firm_generation_gwh"] += firm
            # Storage is the residual balancing resource.
            discharge=min(deficit,storage_power_gw,soc*eta)
            soc-=discharge/eta if eta>0 else 0.0
            deficit-=discharge
            if collect:
                metrics["storage_discharge_to_load_gwh"] += discharge
                metrics["storage_conversion_loss_gwh"] += (discharge/eta-discharge) if eta>0 else 0.0
                if deficit>1e-9:
                    metrics["unserved_gwh"] += deficit
                    metrics["unserved_hours"] += 1
                    metrics["max_shortfall_gw"] = max(metrics["max_shortfall_gw"],deficit)
        if collect:
            metrics["min_soc_gwh"] = min(metrics["min_soc_gwh"],soc)
            metrics["max_soc_gwh"] = max(metrics["max_soc_gwh"],soc)
    return soc, firm_remaining, metrics


def grid_simulate(total_demand_twh_yr: float, case: GridCase) -> Dict:
    if total_demand_twh_yr <= 0:
        raise ValueError("demand must be positive")
    share_sum=case.solar_energy_share+case.wind_energy_share+case.firm_clean_energy_share
    if abs(share_sum-1.0)>1e-8:
        raise ValueError("energy shares must sum to one")
    if not (0 < case.roundtrip_efficiency <= 1):
        raise ValueError("roundtrip efficiency must be in (0,1]")

    avg_gw=total_demand_twh_yr*1000.0/HOURS
    demand=[avg_gw*x for x in DEMAND_SHAPE]
    demand_gwh=sum(demand)

    solar_mean=sum(SOLAR_CF)/HOURS
    wind_mean=sum(WIND_CF)/HOURS
    solar_target_gwh=total_demand_twh_yr*1000*case.solar_energy_share*case.vre_overbuild
    wind_target_gwh=total_demand_twh_yr*1000*case.wind_energy_share*case.vre_overbuild
    solar_gw=solar_target_gwh/(HOURS*solar_mean)
    wind_gw=wind_target_gwh/(HOURS*wind_mean)

    # The firm share is an annual-energy allocation, while capacity factor
    # determines the nameplate needed to make that allocation dispatchable.
    firm_budget_gwh=total_demand_twh_yr*1000*case.firm_clean_energy_share
    firm_gw=firm_budget_gwh/(HOURS*case.firm_capacity_factor) if firm_budget_gwh>0 else 0.0

    storage_cap_gwh=case.storage_energy_hours_avg_load*avg_gw
    storage_power_gw=case.storage_power_multiple_avg_load*avg_gw
    eta=math.sqrt(case.roundtrip_efficiency)

    # Warm the storage state through repeated identical years so the reported
    # year does not receive an arbitrary one-off endowment of stored energy.
    soc=0.50*storage_cap_gwh
    warmup_end_soc=[]
    for _ in range(max(1,case.warmup_years)):
        soc,_,_=_dispatch_one_year(demand,solar_gw,wind_gw,firm_gw,firm_budget_gwh,
                                   storage_cap_gwh,storage_power_gw,eta,soc,False)
        warmup_end_soc.append(soc)
    start_soc=soc
    end_soc, firm_remaining, metrics=_dispatch_one_year(
        demand,solar_gw,wind_gw,firm_gw,firm_budget_gwh,
        storage_cap_gwh,storage_power_gw,eta,start_soc,True)

    unserved=metrics["unserved_gwh"]
    annual_vre_potential_gwh=solar_target_gwh+wind_target_gwh
    available_energy_ratio=(annual_vre_potential_gwh+firm_budget_gwh)/demand_gwh
    cyclic_soc_drift_gwh=end_soc-start_soc
    return {
        "case":case.name,"total_demand_twh_yr":total_demand_twh_yr,"average_load_gw":avg_gw,
        "solar_capacity_gw":solar_gw,"wind_capacity_gw":wind_gw,"firm_clean_capacity_gw":firm_gw,
        "firm_annual_energy_budget_twh":firm_budget_gwh/1000.0,
        "firm_unused_energy_budget_twh":firm_remaining/1000.0,
        "storage_energy_gwh":storage_cap_gwh,"storage_power_gw":storage_power_gw,
        "storage_start_soc_fraction":start_soc/storage_cap_gwh if storage_cap_gwh else 0.0,
        "storage_end_soc_fraction":end_soc/storage_cap_gwh if storage_cap_gwh else 0.0,
        "storage_cyclic_drift_gwh":cyclic_soc_drift_gwh,
        "unserved_energy_twh":unserved/1000.0,"unserved_energy_fraction":unserved/demand_gwh,
        "unserved_hours":metrics["unserved_hours"],"max_shortfall_gw":metrics["max_shortfall_gw"],
        "curtailment_twh":metrics["curtailment_gwh"]/1000.0,
        "firm_generation_twh":metrics["firm_generation_gwh"]/1000.0,
        "storage_charge_input_twh":metrics["storage_charge_input_gwh"]/1000.0,
        "storage_discharge_to_load_twh":metrics["storage_discharge_to_load_gwh"]/1000.0,
        "storage_conversion_loss_twh":metrics["storage_conversion_loss_gwh"]/1000.0,
        "storage_min_soc_fraction":metrics["min_soc_gwh"]/storage_cap_gwh if storage_cap_gwh else 0.0,
        "storage_max_soc_fraction":metrics["max_soc_gwh"]/storage_cap_gwh if storage_cap_gwh else 0.0,
        "potential_generation_to_demand_ratio":available_energy_ratio,
        "adequacy_pass":unserved/demand_gwh <= 0.0001,
        **asdict(case),
    }


def grid_reliability_stress_table(total_demand_twh_yr: float, cases: List[GridCase]=GRID_DEFAULT_CASES) -> Dict:
    rows=[grid_simulate(total_demand_twh_yr,c) for c in cases]
    return {
        "classification":"Representative-macroregion 8760-hour adequacy stress using synthetic transparent profiles, firm annual-energy budgets and cyclic storage warm-up; not a regional capacity-expansion or transmission model.",
        "rows":rows,
        "passed_cases":[r["case"] for r in rows if r["adequacy_pass"]],
        "failed_cases":[r["case"] for r in rows if not r["adequacy_pass"]],
    }


def solve_minimum_vre_overbuild(total_demand_twh_yr: float, case: GridCase,
                                lower: float = 1.0, upper: float = 3.0,
                                tolerance: float = 1e-4) -> Dict:
    """Solve the minimum VRE overbuild factor meeting the adequacy criterion.

    Storage hours, firm-energy share and all profile assumptions are held fixed.
    The result is a one-dimensional adequacy frontier, not a least-cost optimum.
    """
    lo=max(0.1,lower); hi=max(lo,upper)
    hi_case=GridCase(**{**asdict(case),"vre_overbuild":hi})
    hi_result=grid_simulate(total_demand_twh_yr,hi_case)
    if not hi_result["adequacy_pass"]:
        return {
            "case":case.name,"frontier_found":False,"minimum_vre_overbuild":None,
            "search_upper_bound":hi,"unserved_fraction_at_upper":hi_result["unserved_energy_fraction"],
            "storage_hours":case.storage_energy_hours_avg_load,
            "firm_clean_energy_share":case.firm_clean_energy_share,
        }
    for _ in range(60):
        mid=0.5*(lo+hi)
        test=GridCase(**{**asdict(case),"vre_overbuild":mid})
        rr=grid_simulate(total_demand_twh_yr,test)
        if rr["adequacy_pass"]:
            hi=mid
        else:
            lo=mid
        if hi-lo < tolerance:
            break
    final_case=GridCase(**{**asdict(case),"vre_overbuild":hi})
    rr=grid_simulate(total_demand_twh_yr,final_case)
    return {
        "case":case.name,"frontier_found":True,"minimum_vre_overbuild":hi,
        "storage_hours":case.storage_energy_hours_avg_load,
        "firm_clean_energy_share":case.firm_clean_energy_share,
        "solar_energy_share":case.solar_energy_share,"wind_energy_share":case.wind_energy_share,
        "required_solar_capacity_gw":rr["solar_capacity_gw"],
        "required_wind_capacity_gw":rr["wind_capacity_gw"],
        "firm_clean_capacity_gw":rr["firm_clean_capacity_gw"],
        "storage_energy_gwh":rr["storage_energy_gwh"],
        "curtailment_twh":rr["curtailment_twh"],
        "unserved_energy_fraction":rr["unserved_energy_fraction"],
        "potential_generation_to_demand_ratio":rr["potential_generation_to_demand_ratio"],
    }


# Replace the earlier grid_reliability_stress_table with an expanded return that includes a
# one-dimensional adequacy frontier for each mix.
def grid_reliability_stress_table(total_demand_twh_yr: float, cases: List[GridCase]=GRID_DEFAULT_CASES) -> Dict:
    rows=[grid_simulate(total_demand_twh_yr,c) for c in cases]
    frontier=[solve_minimum_vre_overbuild(total_demand_twh_yr,c) for c in cases]
    return {
        "classification":"Representative-macroregion 8760-hour adequacy stress using synthetic transparent profiles, firm annual-energy budgets and cyclic storage warm-up. Adequacy-frontier rows solve only the minimum VRE overbuild at fixed storage and firm share; they are not least-cost regional capacity plans.",
        "rows":rows,
        "adequacy_frontier_rows":frontier,
        "passed_cases":[r["case"] for r in rows if r["adequacy_pass"]],
        "failed_cases":[r["case"] for r in rows if not r["adequacy_pass"]],
    }


# ============================================================================================
# SECTION 10 Integration, scenarios, ensembles and output writers
#   (merged from planetary_restoration_model.py)
# ============================================================================================

from dataclasses import asdict, replace
from typing import Dict, List, Optional
import csv, json, math, os, random


SOURCE_URLS = dict(SOURCE_URLS)
SOURCE_URLS.update({
    "FAOSTAT_LAND_2023": "https://www.fao.org/statistics/highlights-archive/highlights-detail/land-statistics-2001-2023.-global--regional-and-country-trends/",
    "FAO_SOLAW_2025": "https://doi.org/10.4060/cd7488en",
    "DAC_LEARNING_2025": "https://www.sciencedirect.com/science/article/pii/S0040162525001404",
    "EW_REVIEW_2025": "https://www.nature.com/articles/s43017-025-00713-7",
    "FAO_AQUASTAT_IRRIGATION": "https://www.fao.org/aquastat/en/data-analysis/irrig-water-use/conclusions/index.html",
    "IPCC_AR6_WG2_WATER": "https://www.ipcc.ch/report/ar6/wg2/chapter/chapter-4/",
    "IPCC_AR6_WG3_AFOLU": "https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_Chapter07.pdf",
    "FOREST_BIOPHYSICS_2025": "https://www.nature.com/articles/s41467-025-59547-y",
    "BOREAL_ALBEDO_2026": "https://www.nature.com/articles/s41612-026-01365-0",
    "FSB_STABLECOIN_2023": "https://www.fsb.org/2023/07/high-level-recommendations-for-the-regulation-supervision-and-oversight-of-global-stablecoin-arrangements-final-report/",
    "FAIR_V2": "https://doi.org/10.5194/gmd-14-3007-2021",
    "FAIR_2_2_4": "https://pypi.org/project/fair/",
    "FAIR_CALIBRATION_2026": "https://zenodo.org/records/18828694",
    "MYHRE_1998": "https://doi.org/10.1029/98GL01908",
    "GEOFFROY_2013": "https://doi.org/10.1175/JCLI-D-12-00195.1",
    "IPCC_AR6_WG1_CH7": "https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-7/",
    "IGCC_2025": "https://essd.copernicus.org/articles/17/2641/2025/",
})
SOURCE_URLS.update(TRANSITION_SOURCES)


# Extend the immutable core Scenario with a sidecar land-case selector held by name.
# Existing Scenario instances remain valid; callers can use a dict or pass land_case
# to the high-level functions.

def _summarize_rows(rows: List[Dict]) -> Dict:
    elec = elec_low = elec_high = heat = 0.0
    for r in rows:
        amount = r["cdr_gtco2_yr"]
        et = amount * r["electricity_mwh_t"] * 1000.0
        elt = amount * r.get("electricity_low_mwh_t", r.get("electricity_mwh_t", 0.0)) * 1000.0
        eht = amount * r.get("electricity_high_mwh_t", r.get("electricity_mwh_t", 0.0)) * 1000.0
        ht = amount * r["heat_mwhth_t"] * 1000.0
        r["electricity_twh_yr"] = et
        r["electricity_low_twh_yr"] = elt
        r["electricity_high_twh_yr"] = eht
        r["heat_twhth_yr"] = ht
        elec += et; elec_low += elt; elec_high += eht; heat += ht
    return {
        "cdr_gtco2_yr": sum(r["cdr_gtco2_yr"] for r in rows),
        "rows": rows,
        "electricity_twh_yr": elec,
        "electricity_low_twh_yr": elec_low,
        "electricity_high_twh_yr": elec_high,
        "low_grade_heat_twhth_yr": heat,
    }

def unconstrained_portfolio(cdr_gtco2: float) -> Dict:
    """Build the design portfolio and preserve intensity inputs needed after constraints."""
    p = cdr_portfolio(cdr_gtco2)
    # Core rows expose TWh results but not low/high intensity. Recover intensities from design table.
    intensities = {x[0]: x for x in CDR_PORTFOLIO}
    rows=[]
    for r in p["rows"]:
        name=r["pathway"]; spec=intensities[name]
        q=dict(r)
        q["electricity_low_mwh_t"] = spec[3]
        q["electricity_high_mwh_t"] = spec[4]
        rows.append(q)
    return _summarize_rows(rows)

def constrained_portfolio(year: int, s: Scenario, planned_cdr_gt: float,
                          land_case: str = "central") -> Dict:
    if land_case not in LAND_CASES:
        raise KeyError(f"unknown land case: {land_case}")
    raw = unconstrained_portfolio(planned_cdr_gt)
    nexus = constrain_portfolio(year, raw["rows"], LAND_CASES[land_case])
    portfolio = _summarize_rows(nexus["adjusted_rows"])
    portfolio["planned_cdr_gtco2_yr"] = planned_cdr_gt
    portfolio["land_case"] = land_case
    portfolio["land_nexus"] = nexus
    return portfolio

def effective_cdr_path(year: int, s: Scenario, land_case: str = "central") -> Dict:
    planned = incremental_cdr_path(year, s)
    return constrained_portfolio(year, s, planned, land_case)


def gross_emissions_path(year: int, s: Scenario) -> float:
    """Return gross CO2 emissions from the selected transition architecture.

    The default is the endogenous reduced-form capital-turnover module.  The
    legacy prescribed linear path is retained only as an explicit comparator
    and for broad sensitivity tests.
    """
    if getattr(s, "emissions_mode", "prescribed") == "endogenous":
        return transition_emissions_for_year(year, getattr(s, "transition_case_key", "iea_nze_reference"))
    return emissions_path(year, s)


def emissions_transition_result(s: Scenario) -> Dict:
    if getattr(s, "emissions_mode", "prescribed") == "endogenous":
        return transition_run_case(getattr(s, "transition_case_key", "iea_nze_reference"), min(2100, s.end_year))
    rows=[{"year":y,"gross_emissions_gtco2":emissions_path(y,s)} for y in range(START_YEAR,min(2100,s.end_year)+1)]
    return {"case_key":"legacy_prescribed","case":"Legacy prescribed linear decline","rows":rows,"sector_rows":[],
            "residual_floor_year":s.residual_year,"cumulative_transition_capital_to_2050_usd_tn":None,
            "classification":"Legacy prescribed comparator; no capital-stock or investment solution.","validation":{},"sources":{}}

# --- Carbon with dynamic physical constraints --------------------------------------------
def carbon_cycle(s: Scenario, land_case: str = "central", maintain_after_target_years: int = 30) -> Dict:
    init = initialize_carbon_state(START_CO2_PPM, s.observed_natural_sink_gtc_yr)
    state = list(init["state_gtc"])
    rows=[]; peak_ppm=START_CO2_PPM; peak_year=START_YEAR; crossing_year=None
    cumulative_cdr=0.0; maintenance_years=0
    land_binding_years=[]
    maintenance_ppm=[]; maintenance_cdr=[]; maintenance_shortfall_years=[]
    for year in range(START_YEAR, s.end_year+1):
        emissions = gross_emissions_path(year, s)
        plan = effective_cdr_path(year, s, land_case)
        planned = plan["planned_cdr_gtco2_yr"]
        feasible = plan["cdr_gtco2_yr"]
        if plan["land_nexus"]["binding"]:
            land_binding_years.append(year)
        phase="drawdown"
        if crossing_year is None:
            cdr=feasible; net=emissions-cdr
        else:
            phase="target_maintenance"
            net_required = _required_net_flux_for_target(state, TARGET_CO2_PPM)
            required_cdr = max(0.0, emissions-net_required)
            # Maintenance cannot exceed the physically feasible portfolio in that year.
            cdr = min(required_cdr, feasible)
            if required_cdr > feasible + 1e-9:
                maintenance_shortfall_years.append(year)
            net = emissions-cdr
            maintenance_years += 1
            maintenance_cdr.append(cdr)
        state,natural_sink = _advance_reservoirs(state, net)
        co2=PREINDUSTRIAL_CO2_PPM+sum(state)/CO2_MASS_GTC_PER_PPM
        if crossing_year is None: cumulative_cdr += cdr
        else: maintenance_ppm.append(co2)
        if co2>peak_ppm: peak_ppm,peak_year=co2,year
        if crossing_year is None and co2<=TARGET_CO2_PPM: crossing_year=year
        rows.append({
            "year":year,"phase":phase,"gross_emissions_gtco2":emissions,
            "planned_incremental_cdr_gtco2":planned,"feasible_incremental_cdr_gtco2":feasible,
            "incremental_cdr_gtco2":cdr,"net_anthropogenic_gtco2":net,
            "natural_reservoir_flux_to_sinks_gtc":natural_sink,"co2_ppm":co2,
            "land_binding":plan["land_nexus"]["binding"],
            "food_land_deficit_mha":plan["land_nexus"]["food"]["food_land_deficit_mha"],
            "cdr_land_mha":plan["land_nexus"]["realized_cdr_land_mha"],
            "reservoir_permanent_gtc":state[0],"reservoir_slow_gtc":state[1],
            "reservoir_medium_gtc":state[2],"reservoir_fast_gtc":state[3],
        })
        if crossing_year is not None and maintenance_years>=maintain_after_target_years: break
    return {
        "scenario":asdict(s),"land_case":land_case,
        "model_class":"GCB-calibrated Joos four-reservoir IRF + dynamic land/blue-water-constrained CDR with biogeophysical diagnostics",
        "publication_boundary":"Reduced-complexity global screen; validate restoration timing against calibrated FaIR/OSCAR ensembles and regional physical constraints.",
        "initialization":init,"peak_co2_ppm":peak_ppm,"peak_year":peak_year,
        "crossing_year":crossing_year,"cumulative_incremental_cdr_to_target_gtco2":cumulative_cdr,
        # Reaching 280 ppm is not an endpoint. The atmospheric perturbation keeps decaying
        # out of the land and ocean reservoirs, so holding the target needs sustained
        # removal well above the residual-emissions rate.
        "steady_state_maintenance_cdr_gtco2_yr": (maintenance_cdr[-1] if maintenance_cdr else None),
        "maintenance_years_simulated": maintenance_years,
        "max_maintenance_co2_ppm": (max(maintenance_ppm) if maintenance_ppm else None),
        "target_held": (len(maintenance_shortfall_years)==0) if crossing_year is not None else None,
        "maintenance_shortfall_years": maintenance_shortfall_years,
        "land_binding_year_count":len(set(land_binding_years)),
        "first_land_binding_year":min(land_binding_years) if land_binding_years else None,
        "rows":rows,
    }

# --- FaIR-v2-form structural carbon cross-check ------------------------------------------
def unconstrained_net_flux_path(s: Scenario, land_case: str = "central") -> List[Dict]:
    """Emissions minus physically feasible CDR without a 280-ppm maintenance clamp."""
    rows=[]
    for year in range(START_YEAR, s.end_year+1):
        emissions=gross_emissions_path(year,s)
        p=effective_cdr_path(year,s,land_case)
        cdr=p["cdr_gtco2_yr"]
        rows.append({"year":year,"gross_emissions_gtco2":emissions,"feasible_incremental_cdr_gtco2":cdr,
                     "net_anthropogenic_gtco2":emissions-cdr})
    return rows


def fair_form_crosscheck(s: Scenario, land_case: str = "central") -> Dict:
    """Run the published FaIR-v2 gas-cycle form as a structural validation layer.

    This is deliberately labelled a structural cross-check.  It uses published
    FaIR-v2 equations/default/prior parameter forms but is not the official
    841-member fastmip/fair-calibrate posterior.
    """
    flux=unconstrained_net_flux_path(s,land_case)
    init=initialize_carbon_state(START_CO2_PPM,s.observed_natural_sink_gtc_yr)

    # The iIRF100 lifetime scaling depends on temperature. Freezing temperature at its
    # present-day value across a century-scale drawdown to pre-industrial CO2 is
    # internally inconsistent, so the warming trajectory from the coupled energy-balance
    # module is supplied instead. The frozen-temperature result is retained alongside it
    # so the size of that inconsistency is visible rather than assumed away.
    joos=carbon_cycle(s,land_case,maintain_after_target_years=0)
    temps={r["year"]:r["surface_warming_c"] for r in climate_run(joos["rows"])["rows"]}

    cases=[]
    for p in fair_form_parameter_cases():
        rr=fair_form_run(flux,init["state_gtc"],p,temperature_by_year=temps)
        cases.append({"name":p.name,"peak_co2_ppm":rr["peak_co2_ppm"],"peak_year":rr["peak_year"],
                      "crossing_year":rr["crossing_year"],"params":rr["params"],
                      "temperature_treatment":rr["temperature_treatment"]})
    frozen=fair_form_run(flux,init["state_gtc"],fair_form_parameter_cases()[0])
    ens=fair_form_ensemble(flux,init["state_gtc"])
    central=fair_form_run(flux,init["state_gtc"],fair_form_parameter_cases()[0],temperature_by_year=temps)
    return {
        "classification":"FaIR-v2-form state-dependent gas-cycle structural cross-check; official FaIR 2.2.4 calibrated/constrained ensemble remains a required external validation before a precise Earth-system restoration-date claim.",
        "cases":cases,"ensemble":ens,
        "endogenous_temperature_crossing_year":central["crossing_year"],
        "frozen_temperature_crossing_year":frozen["crossing_year"],
        "frozen_vs_endogenous_temperature_year_difference":(
            None if (central["crossing_year"] is None or frozen["crossing_year"] is None)
            else central["crossing_year"]-frozen["crossing_year"]),
        "ensemble_temperature_treatment":"frozen present-day value; the prior ensemble varies the frozen level across 1.2-2.0 C",
        "central_rows":central["rows"],
    }

# --- Learning curves and dynamic finance --------------------------------------------------
def dynamic_finance_ramp(s: Scenario, land_case: str = "central",
                         f: FinanceInputs = FinanceInputs(), end_year: int = 2050) -> List[Dict]:
    cumulative={k:a.initial_cumulative_gt for k,a in DEFAULT_LEARNING.items()}
    rows=[]
    horizon=max(s.cdr_maturity_year,2043)
    growth=(f.mature_gdp_usd_tn/f.gdp_2026_usd_tn)**(1/(horizon-START_YEAR))-1 if horizon>START_YEAR else 0.0
    for y in range(START_YEAR,end_year+1):
        p=effective_cdr_path(y,s,land_case)
        utilization={r["pathway"]: r.get("resource_utilization_fraction", 0.0) for r in p["rows"]}
        economics=pathway_economics(cumulative, utilization)
        spend_tn=0.0; no_learning_tn=0.0; no_scarcity_tn=0.0
        detail=[]
        for r in p["rows"]:
            name=r["pathway"]; amount=r["cdr_gtco2_yr"]; econ=economics[name]; cost=econ["marginal_cost_usd_t"]
            spend=amount*cost/1000.0
            spend_tn += spend
            no_scarcity_tn += amount*econ["cost_without_scarcity_usd_t"]/1000.0
            no_learning_tn += amount*f.cdr_cost_usd_t/1000.0
            detail.append({
                "pathway":name,"cdr_gtco2_yr":amount,"marginal_cost_usd_t":cost,
                "cost_without_scarcity_usd_t":econ["cost_without_scarcity_usd_t"],
                "learning_factor":econ["learning_factor"],"scarcity_multiplier":econ["scarcity_multiplier"],
                "resource_utilization_fraction":econ["resource_utilization_fraction"],
                "annual_spend_usd_tn":spend,"cumulative_before_gt":cumulative[name]
            })
            cumulative[name] += amount
        gdp=f.gdp_2026_usd_tn*((1+growth)**(min(y,horizon)-START_YEAR))
        if y>horizon: gdp=f.mature_gdp_usd_tn
        cap=gdp*f.settlement_envelope_fraction_gdp
        blended=(spend_tn*1000.0/p["cdr_gtco2_yr"]) if p["cdr_gtco2_yr"]>0 else 0.0
        rows.append({
            "year":y,"planned_cdr_gtco2":p["planned_cdr_gtco2_yr"],"feasible_cdr_gtco2":p["cdr_gtco2_yr"],
            "dynamic_blended_cost_usd_t":blended,"dynamic_cdr_spend_usd_tn":spend_tn,
            "learning_only_no_scarcity_spend_usd_tn":no_scarcity_tn,
            "flat_185_counterfactual_usd_tn":no_learning_tn,"gdp_screen_usd_tn":gdp,
            "settlement_cap_usd_tn":cap,"dynamic_spend_fraction_gdp":spend_tn/gdp if gdp else math.nan,
            "within_cap":spend_tn<=cap,"pathway_detail":detail,
        })
    return rows

def learning_summary(s: Scenario, land_case: str = "central") -> Dict:
    ramp=dynamic_finance_ramp(s,land_case,end_year=max(2050,s.cdr_maturity_year))
    by_year={r["year"]:r for r in ramp}
    maturity=by_year[s.cdr_maturity_year]
    y2050=by_year[2050]
    return {
        "classification":"Differentiated pathway economics: learnable process shares follow Wright-law sensitivities while land/feedstock/site shares receive a convex scarcity multiplier from physical resource utilization. Non-DAC parameters remain model assumptions.",
        "assumptions":{k:asdict(v) for k,v in DEFAULT_LEARNING.items()},
        "maturity_year":s.cdr_maturity_year,
        "maturity_blended_cost_usd_t":maturity["dynamic_blended_cost_usd_t"],
        "maturity_spend_usd_tn":maturity["dynamic_cdr_spend_usd_tn"],
        "maturity_learning_only_no_scarcity_spend_usd_tn":maturity["learning_only_no_scarcity_spend_usd_tn"],
        "maturity_flat_185_counterfactual_usd_tn":maturity["flat_185_counterfactual_usd_tn"],
        "cost_2050_usd_t":y2050["dynamic_blended_cost_usd_t"],
        "spend_2050_usd_tn":y2050["dynamic_cdr_spend_usd_tn"],
        "rows":ramp,
    }

def finance_summary(s: Scenario, land_case: str = "central", f: FinanceInputs = FinanceInputs()) -> Dict:
    learn=learning_summary(s,land_case)
    mat=next(r for r in learn["rows"] if r["year"]==s.cdr_maturity_year)
    spend=mat["dynamic_cdr_spend_usd_tn"]
    central_burden=spend/f.mature_gdp_usd_tn
    collection=[]
    for turnover_multiple in (2,5,10,20):
        for retained in (1.0,0.75,0.50,0.40):
            eligible=f.mature_gdp_usd_tn*turnover_multiple*retained
            collection.append({"eligible_settlement_turnover_multiple_of_gdp":turnover_multiple,"retained_fee_base_fraction":retained,
                               "required_average_fee_fraction":spend/eligible if eligible else math.inf})
    return {
        "maturity_dynamic_cdr_spend_usd_tn_yr":spend,
        "maturity_dynamic_blended_cost_usd_t":mat["dynamic_blended_cost_usd_t"],
        "maturity_flat_185_counterfactual_usd_tn_yr":mat["flat_185_counterfactual_usd_tn"],
        "central_burden_fraction_gdp":central_burden,
        "settlement_envelope_fraction_gdp":f.settlement_envelope_fraction_gdp,
        "central_envelope_capacity_usd_tn_yr":f.mature_gdp_usd_tn*f.settlement_envelope_fraction_gdp,
        "headroom_after_dynamic_cdr_usd_tn_yr":f.mature_gdp_usd_tn*f.settlement_envelope_fraction_gdp-spend,
        "carbon_credit_sales_required_usd_tn_yr":0.0,
        "collection_stress":collection,
        "status":"Dynamic CDR costs are solved conditional on learning assumptions. Settlement collection remains conditional on eligible transaction flow, retention and fee incidence.",
    }


# --- Settlement-funding feedback ---------------------------------------------------------
def _gdp_screen_for_year(year: int, s: Scenario, f: FinanceInputs = FinanceInputs()) -> float:
    horizon=max(s.cdr_maturity_year,2043)
    if year <= START_YEAR:
        return f.gdp_2026_usd_tn
    if year >= horizon:
        return f.mature_gdp_usd_tn
    growth=(f.mature_gdp_usd_tn/f.gdp_2026_usd_tn)**(1/(horizon-START_YEAR))-1
    return f.gdp_2026_usd_tn*((1+growth)**(year-START_YEAR))


def _scaled_portfolio_spend(p: Dict, scale: float, cumulative: Dict[str,float]) -> Dict:
    """Spend for a proportional funding scale at current cumulative deployment.

    Physical scarcity utilization scales with realized deployment. This is a
    neutral portfolio stress, not a cost-minimizing re-optimization across CDR
    pathways.
    """
    q=max(0.0,min(1.0,scale))
    utilization={r["pathway"]:r.get("resource_utilization_fraction",0.0)*q for r in p["rows"]}
    economics=pathway_economics(cumulative,utilization)
    spend=0.0; rows=[]
    for r in p["rows"]:
        name=r["pathway"]; amount=r["cdr_gtco2_yr"]*q; econ=economics[name]
        annual=amount*econ["marginal_cost_usd_t"]/1000.0
        spend+=annual
        rows.append({"pathway":name,"cdr_gtco2_yr":amount,"marginal_cost_usd_t":econ["marginal_cost_usd_t"],
                     "annual_spend_usd_tn":annual,"resource_utilization_fraction":utilization[name]})
    return {"scale":q,"cdr_gtco2_yr":sum(x["cdr_gtco2_yr"] for x in rows),"spend_usd_tn":spend,"rows":rows}


def funding_constrained_cdr_path(s: Scenario, settlement_case, land_case: str = "central",
                                 end_year: Optional[int] = None,
                                 f: FinanceInputs = FinanceInputs()) -> Dict:
    """Propagate settlement collection limits into the deployable CDR pathway.

    Each year the physical portfolio is solved first. Dynamic pathway costs are
    evaluated at actual cumulative deployment. Available public funding is the
    lesser of the settlement collection stress maximum and the 2.14%-of-GDP
    policy envelope. If insufficient, the portfolio is scaled proportionally.
    This is deliberately conservative and does not optimize pathway substitution.
    """
    end_year=end_year or s.end_year
    cumulative={k:a.initial_cumulative_gt for k,a in DEFAULT_LEARNING.items()}
    rows=[]
    for year in range(START_YEAR,end_year+1):
        p=effective_cdr_path(year,s,land_case)
        gdp=_gdp_screen_for_year(year,s,f)
        collection=settlement_maximum_collection(gdp,settlement_case)
        envelope=gdp*f.settlement_envelope_fraction_gdp
        available=min(collection["max_collection_usd_tn"],envelope)
        full=_scaled_portfolio_spend(p,1.0,cumulative)
        if full["spend_usd_tn"] <= available+1e-12:
            realized=full
        else:
            lo=0.0; hi=1.0
            for _ in range(70):
                mid=0.5*(lo+hi)
                trial=_scaled_portfolio_spend(p,mid,cumulative)
                if trial["spend_usd_tn"] <= available:
                    lo=mid
                else:
                    hi=mid
            realized=_scaled_portfolio_spend(p,lo,cumulative)
        for rr in realized["rows"]:
            cumulative[rr["pathway"]]+=rr["cdr_gtco2_yr"]
        rows.append({
            "year":year,"gdp_usd_tn":gdp,
            "planned_physical_cdr_gtco2_yr":p["cdr_gtco2_yr"],
            "funded_cdr_gtco2_yr":realized["cdr_gtco2_yr"],
            "funding_scale":realized["scale"],"required_full_spend_usd_tn":full["spend_usd_tn"],
            "realized_spend_usd_tn":realized["spend_usd_tn"],"available_funding_usd_tn":available,
            "settlement_max_collection_usd_tn":collection["max_collection_usd_tn"],
            "settlement_envelope_usd_tn":envelope,
            "funding_binding":realized["scale"] < 1.0-1e-8,
        })
    return {
        "case":settlement_case.name,
        "classification":"Settlement-funding feedback stress: physical CDR is proportionally scaled when maximum modeled collection or the public-envelope cap cannot fund dynamic pathway costs. This is not a general-equilibrium or least-cost portfolio optimization.",
        "rows":rows,
        "binding_year_count":sum(1 for x in rows if x["funding_binding"]),
        "first_binding_year":next((x["year"] for x in rows if x["funding_binding"]),None),
    }


def carbon_cycle_from_funded_path(s: Scenario, funded: Dict, maintain_after_target_years: int = 0) -> Dict:
    by_year={x["year"]:x for x in funded["rows"]}
    init=initialize_carbon_state(START_CO2_PPM,s.observed_natural_sink_gtc_yr)
    state=list(init["state_gtc"]); rows=[]; peak=START_CO2_PPM; peak_year=START_YEAR
    crossing=None; maintenance_years=0; cumulative=0.0
    for year in range(START_YEAR,s.end_year+1):
        emissions=gross_emissions_path(year,s)
        max_funded=by_year[year]["funded_cdr_gtco2_yr"]
        if crossing is None:
            cdr=max_funded; phase="drawdown"
        else:
            phase="target_maintenance"
            net_required=_required_net_flux_for_target(state,TARGET_CO2_PPM)
            required=max(0.0,emissions-net_required)
            cdr=min(required,max_funded)
            maintenance_years+=1
        net=emissions-cdr
        state,natural_sink=_advance_reservoirs(state,net)
        ppm=PREINDUSTRIAL_CO2_PPM+sum(state)/CO2_MASS_GTC_PER_PPM
        if crossing is None: cumulative+=cdr
        if ppm>peak: peak,peak_year=ppm,year
        if crossing is None and ppm<=TARGET_CO2_PPM: crossing=year
        rows.append({"year":year,"phase":phase,"gross_emissions_gtco2":emissions,
                     "max_funded_cdr_gtco2":max_funded,"incremental_cdr_gtco2":cdr,
                     "net_anthropogenic_gtco2":net,"co2_ppm":ppm,
                     "funding_scale":by_year[year]["funding_scale"],
                     "available_funding_usd_tn":by_year[year]["available_funding_usd_tn"],
                     "realized_spend_usd_tn":by_year[year]["realized_spend_usd_tn"]})
        if crossing is not None and maintenance_years>=maintain_after_target_years: break
    return {"case":funded["case"],"crossing_year":crossing,"peak_co2_ppm":peak,"peak_year":peak_year,
            "cumulative_incremental_cdr_to_target_gtco2":cumulative,"rows":rows}


def settlement_funding_feedback(s: Scenario, land_case: str = "central") -> Dict:
    cases=[]
    for c in SETTLEMENT_COLLECTION_CASES:
        fp=funding_constrained_cdr_path(s,c,land_case)
        cc=carbon_cycle_from_funded_path(s,fp,maintain_after_target_years=0)
        maturity=next(x for x in fp["rows"] if x["year"]==s.cdr_maturity_year)
        cases.append({"case":c.name,"crossing_year":cc["crossing_year"],"peak_co2_ppm":cc["peak_co2_ppm"],
                      "peak_year":cc["peak_year"],"binding_year_count":fp["binding_year_count"],
                      "first_binding_year":fp["first_binding_year"],
                      "maturity_funding_scale":maturity["funding_scale"],
                      "maturity_funded_cdr_gtco2_yr":maturity["funded_cdr_gtco2_yr"],
                      "maturity_available_funding_usd_tn":maturity["available_funding_usd_tn"]})
    return {
        "classification":"Dynamic collection-to-CDR feedback stress. Central physical results remain conditional on the selected collection case; adverse leakage can reduce funded CDR and delay or prevent atmospheric restoration within the model horizon.",
        "cases":cases,
    }

# --- Land stress matrix ------------------------------------------------------------------
def land_stress_matrix(s: Scenario) -> List[Dict]:
    rows=[]
    for case in LAND_CASES:
        for y in (s.cdr_maturity_year,2050,2085):
            p=effective_cdr_path(y,s,case)
            n=p["land_nexus"]
            rows.append({
                "case":case,"year":y,"planned_cdr_gtco2":p["planned_cdr_gtco2_yr"],"feasible_cdr_gtco2":p["cdr_gtco2_yr"],
                "food_cropland_mha":n["food"]["food_cropland_mha"],"food_pasture_mha":n["food"]["food_pasture_mha"],
                "food_irrigation_requirement_km3_yr":n["food"]["screened_food_irrigation_requirement_km3_yr"],
                "food_irrigation_withdrawal_km3_yr":n["food"]["screened_food_irrigation_withdrawal_km3_yr"],
                "remaining_agricultural_land_mha":n["food"]["remaining_agricultural_land_mha"],"cdr_land_mha":n["realized_cdr_land_mha"],
                "incremental_cdr_blue_water_km3_yr":n["realized_incremental_blue_water_km3_yr"],
                "incremental_blue_water_screen_km3_yr":n["incremental_blue_water_screen_km3_yr"],
                "water_utilization_fraction":n["incremental_blue_water_utilization_fraction"],
                "restoration_et_increment_diagnostic_km3_yr":n["restoration_et_increment_diagnostic_km3_yr"],
                "boreal_albedo_stress_global_forcing_w_m2":n["uncompensated_boreal_albedo_only_global_forcing_w_m2"],
                "land_scale":n["land_scale"],"water_scale":n["water_scale"],"binding":n["binding"],
            })
    return rows

# --- Coupled temperature response --------------------------------------------------------
def climate_response(s: Scenario, land_case: str = "central",
                     carbon: Optional[Dict] = None,
                     maintain_after_target_years: int = 60) -> Dict:
    """Warming trajectory implied by the CO2 pathway.

    The carbon modules produce a concentration trajectory; this converts it to
    radiative forcing and global-mean surface temperature so the package reports
    peak warming, overshoot duration and the warming still present when CO2
    reaches the restoration target. Non-CO2 forcing is an explicit scenario input.
    """
    c = carbon or carbon_cycle(s, land_case, maintain_after_target_years)
    cases = []
    central = None
    for p in climate_parameter_cases():
        run = climate_run(c["rows"], p)
        if central is None:
            central = run
        cases.append({k: v for k, v in run.items() if k != "rows"})
    return {
        "classification": central["classification"],
        "validation": climate_validation(),
        "central": {k: v for k, v in central.items() if k != "rows"},
        "sensitivity_cases": cases,
        "central_rows": central["rows"],
        "sources": CLIMATE_SOURCES,
        "boundary": ("Global-mean energy balance only. No regional pattern, precipitation, "
                     "sea level, ice sheet or permafrost response. Deep-ocean heat and the "
                     "associated sea-level commitment persist for centuries after surface "
                     "temperature falls, so CO2 restoration is not climate restoration."),
    }


# --- Scenario library --------------------------------------------------------------------
def scenario_library() -> List[Dict]:
    return [
        {"scenario":Scenario(name="IEA-NZE-calibrated restoration reference", emissions_mode="endogenous", transition_case_key="iea_nze_reference", cdr_mode="accelerated",mature_incremental_cdr_gtco2=15.2,cdr_maturity_year=2043),"land_case":"central"},
        {"scenario":Scenario(name="Accelerated capital-turnover design", emissions_mode="endogenous", transition_case_key="high_acceleration", cdr_mode="accelerated",mature_incremental_cdr_gtco2=15.2,cdr_maturity_year=2043),"land_case":"central"},
        {"scenario":Scenario(name="State of CDR 2026 highest-ambition median benchmark", emissions_mode="endogenous", transition_case_key="iea_nze_reference", cdr_mode="evidence_benchmark"),"land_case":"central"},
        {"scenario":Scenario(name="Low-efficiency land stress", emissions_mode="endogenous", transition_case_key="iea_nze_reference", cdr_mode="accelerated",mature_incremental_cdr_gtco2=15.2,cdr_maturity_year=2043),"land_case":"low_efficiency"},
        {"scenario":Scenario(name="CDR under-delivery 10 Gt/yr", emissions_mode="endogenous", transition_case_key="iea_nze_reference", cdr_mode="accelerated",mature_incremental_cdr_gtco2=10.0,cdr_maturity_year=2050),"land_case":"central"},
        {"scenario":Scenario(name="Current-investment constrained transition", emissions_mode="endogenous", transition_case_key="current_investment_constrained", cdr_mode="accelerated",mature_incremental_cdr_gtco2=15.2,cdr_maturity_year=2043),"land_case":"central"},
        {"scenario":Scenario(name="Natural capital-turnover transition", emissions_mode="endogenous", transition_case_key="natural_turnover", cdr_mode="accelerated",mature_incremental_cdr_gtco2=15.2,cdr_maturity_year=2043),"land_case":"central"},
        {"scenario":Scenario(name="Delayed transition finance", emissions_mode="endogenous", transition_case_key="delayed_finance", cdr_mode="accelerated",mature_incremental_cdr_gtco2=15.2,cdr_maturity_year=2043),"land_case":"central"},
        {"scenario":Scenario(name="Legacy prescribed-linear comparator", emissions_mode="prescribed", residual_year=2050,residual_emissions_gtco2=1.5,cdr_mode="accelerated",mature_incremental_cdr_gtco2=15.2,cdr_maturity_year=2043),"land_case":"central"},
    ]

def scenario_summary() -> List[Dict]:
    out=[]
    for item in scenario_library():
        s=item["scenario"]; lc=item["land_case"]
        c=carbon_cycle(s,lc,maintain_after_target_years=0)
        cl=climate_run(c["rows"])
        sizing_year=2100 if s.cdr_mode=="evidence_benchmark" else s.cdr_maturity_year
        p=effective_cdr_path(sizing_year,s,lc)
        e=integrated_energy(s,p)
        tr=emissions_transition_result(s)
        out.append({"scenario":s.name,"land_case":lc,"emissions_case":tr["case"],"emissions_residual_floor_year":tr.get("residual_floor_year"),
                    "planned_cdr_gtco2_yr":p["planned_cdr_gtco2_yr"],"feasible_cdr_gtco2_yr":p["cdr_gtco2_yr"],
                    "peak_co2_ppm":c["peak_co2_ppm"],"peak_year":c["peak_year"],"return_280_year":c["crossing_year"],
                    "cumulative_cdr_to_target_gtco2":c["cumulative_incremental_cdr_to_target_gtco2"],
                    "peak_warming_c":cl["peak_warming_c"],"years_above_1p5c":cl["years_above_1p5"],
                    "land_binding_year_count":c["land_binding_year_count"],"cdr_electricity_twh_yr":p["electricity_twh_yr"],
                    "total_electricity_core_twh_yr":e["core_transformed_electricity_twh_yr"]})
    return out

def _percentile(xs: List[float], p: float) -> float:
    if not xs:return math.nan
    ys=sorted(xs);pos=(len(ys)-1)*p;lo=int(math.floor(pos));hi=int(math.ceil(pos))
    if lo==hi:return ys[lo]
    f=pos-lo;return ys[lo]*(1-f)+ys[hi]*f

def _percentile_rank(xs: List[float], value: float) -> float:
    if not xs: return math.nan
    return sum(1 for x in xs if x <= value)/len(xs)


def bounded_sensitivity_ensemble(n:int=700,seed:int=20260901,
                                 deterministic_crossing_year: Optional[int] = None)->Dict:
    """Coupled sensitivity ensemble around the endogenous transition architecture.

    Transition cases are discrete screening states rather than empirical probabilities;
    CDR scale, maturity, sink initialization and land efficiency are sampled within
    bounded author-selected ranges.
    """
    rnd=random.Random(seed);years=[];peaks=[];noncross=0;land_bind=0
    transition_keys=["iea_nze_reference","high_acceleration","current_investment_constrained","natural_turnover","delayed_finance"]
    transition_weights=[0.35,0.15,0.20,0.15,0.15]
    for _ in range(n):
        key=rnd.choices(transition_keys,weights=transition_weights,k=1)[0]
        s=Scenario(name="bounded sensitivity draw",emissions_mode="endogenous",transition_case_key=key,
                   mature_incremental_cdr_gtco2=rnd.triangular(10.0,16.0,15.2),
                   cdr_maturity_year=int(round(rnd.triangular(2040,2055,2043))),
                   observed_natural_sink_gtc_yr=rnd.triangular(5.4,7.2,6.3),end_year=2400)
        lc=rnd.choices(["central","low_efficiency","high_efficiency"],weights=[0.6,0.2,0.2],k=1)[0]
        c=carbon_cycle(s,lc,maintain_after_target_years=0);peaks.append(c["peak_co2_ppm"])
        if c["land_binding_year_count"]>0:land_bind+=1
        if c["crossing_year"] is None:noncross+=1
        else:years.append(float(c["crossing_year"]))
    rank=(_percentile_rank(years,float(deterministic_crossing_year)) if deterministic_crossing_year is not None else None)
    censored=years+[float("inf")]*noncross
    def _cen(p):
        v=_percentile(censored,p);return None if math.isinf(v) else v
    return {"classification":"coupled bounded sensitivity ensemble using discrete endogenous transition cases plus author-selected triangular CDR/carbon-sink ranges and land-efficiency stresses; not an empirical probability forecast",
            "deterministic_central_crossing_year":deterministic_crossing_year,"deterministic_central_percentile_rank":rank,
            "rank_interpretation":"Fraction of returning draws reaching 280 ppm no later than the calibrated reference. Transition-case weights are scenario weights, not observed probabilities.",
            "fraction_not_restored_within_horizon":noncross/n if n else math.nan,"return_year_p50_all_draws":_cen(.5),"return_year_p95_all_draws":_cen(.95),
            "censoring_note":"p05/p50/p95 are conditional on return within the horizon; *_all_draws re-include non-returning draws as censored.",
            "samples":n,"crossing_samples":len(years),"noncrossing_samples":noncross,"land_binding_samples":land_bind,
            "transition_case_weights":dict(zip(transition_keys,transition_weights)),"return_year_samples":years,
            "return_year_p05":_percentile(years,.05),"return_year_p50":_percentile(years,.5),"return_year_p95":_percentile(years,.95),
            "peak_co2_p05":_percentile(peaks,.05),"peak_co2_p50":_percentile(peaks,.5),"peak_co2_p95":_percentile(peaks,.95)}

# --- Integrated output -------------------------------------------------------------------
def integrated_results(s: Scenario = Scenario(), land_case: str = "central") -> Dict:
    carbon=carbon_cycle(s,land_case)
    sizing_year=2100 if s.cdr_mode=="evidence_benchmark" else s.cdr_maturity_year
    portfolio=effective_cdr_path(sizing_year,s,land_case)
    learning=learning_summary(s,land_case)
    finance=finance_summary(s,land_case)
    energy=integrated_energy(s,portfolio)
    settlement=settlement_collection_stress_table(finance["maturity_dynamic_cdr_spend_usd_tn_yr"], FinanceInputs().mature_gdp_usd_tn)
    settlement_ramp=settlement_collection_annual_ramp(learning["rows"], SETTLEMENT_COLLECTION_CASES[0])
    grid=grid_reliability_stress_table(energy["full_desalination_backstop_transformed_electricity_twh_yr"])
    funding_feedback=settlement_funding_feedback(s,land_case)
    return {
        "scenario":asdict(s),"land_case":land_case,"emissions_transition":emissions_transition_result(s),"emissions_transition_cases":transition_case_summary(),"carbon":carbon,"fair_form_carbon_crosscheck":fair_form_crosscheck(s,land_case),
        "climate_response":climate_response(s,land_case,carbon=carbon),
        "scenario_summary":scenario_summary(),
        "bounded_sensitivity_ensemble":bounded_sensitivity_ensemble(
            deterministic_crossing_year=carbon["crossing_year"]),"cdr_portfolio":portfolio,
        "land_nexus":portfolio["land_nexus"],"land_stress_matrix":land_stress_matrix(s),
        "learning_curves":learning,"energy":energy,"grid_reliability_stress":grid,
        "minerals":minerals(portfolio),"biomass":biomass(portfolio),"water":water(),"seaweed":seaweed(),
        "nutrients":nutrients(),"plastics":plastics(),"finance":finance,
        "settlement_collection":{"maturity_stress":settlement,"central_annual_ramp":settlement_ramp,"funding_feedback":funding_feedback},
        "monetary_architecture":{"wealth_conversion":national_balance({"Country A":50,"Country B":30,"Country C":20}),"liquidity_stress":monetary_stress_table()},
        "banking_transition":banking_transition(),"external_social_ecological_screens":external_social_ecological_screens(),
        "sources":SOURCE_URLS,
        "model_boundary":"Dynamically constrained coupled global screening model with reduced-form endogenous sectoral capital-turnover emissions, state-dependent FaIR-form carbon cross-check, differentiated CDR learning/scarcity economics, managed blue-water screening, restoration ET/albedo diagnostics, settlement fee/leakage stress, representative 8760-hour power adequacy stress and illiquid-reserve redemption stress. Official calibrated FaIR/OSCAR validation, gridded land/water, real-weather regional grid optimization and full macro-monetary general equilibrium remain publication-grade validation layers.",
    }

def _flatten_learning_rows(rows: List[Dict]) -> List[Dict]:
    return [{k:v for k,v in r.items() if k!="pathway_detail"} for r in rows]


def _flatten_pathway_economics(rows: List[Dict]) -> List[Dict]:
    out=[]
    for row in rows:
        year=row["year"]
        for detail in row.get("pathway_detail",[]):
            q=dict(detail); q["year"]=year; out.append(q)
    return out

def write_outputs(outdir:str,s:Scenario=Scenario(),land_case:str="central")->Dict:
    os.makedirs(outdir,exist_ok=True);r=integrated_results(s,land_case)
    with open(os.path.join(outdir,"planetary_restoration_results.json"),"w",encoding="utf-8") as f:json.dump(r,f,indent=2)
    tables={
        "carbon_cycle.csv":r["carbon"]["rows"],"emissions_transition.csv":r["emissions_transition"]["rows"],"emissions_transition_sectors.csv":r["emissions_transition"].get("sector_rows",[]),"emissions_transition_cases.csv":r["emissions_transition_cases"],"scenario_summary.csv":r["scenario_summary"],"cdr_portfolio.csv":r["cdr_portfolio"]["rows"],
        "land_stress.csv":r["land_stress_matrix"],"learning_finance.csv":_flatten_learning_rows(r["learning_curves"]["rows"]),
        "cdr_pathway_economics.csv":_flatten_pathway_economics(r["learning_curves"]["rows"]),
        "monetary_liquidity_stress.csv":r["monetary_architecture"]["liquidity_stress"]["rows"],
        "fair_form_carbon_crosscheck.csv":r["fair_form_carbon_crosscheck"]["central_rows"],
        "grid_reliability_stress.csv":r["grid_reliability_stress"]["rows"],
        "climate_response.csv":r["climate_response"]["central_rows"],
        "climate_sensitivity_cases.csv":r["climate_response"]["sensitivity_cases"],
        "settlement_collection_stress.csv":r["settlement_collection"]["maturity_stress"]["rows"],
        "settlement_collection_ramp.csv":r["settlement_collection"]["central_annual_ramp"],
        "settlement_funding_feedback.csv":r["settlement_collection"]["funding_feedback"]["cases"],
        "grid_adequacy_frontier.csv":r["grid_reliability_stress"]["adequacy_frontier_rows"],
    }
    for fn,rows in tables.items():
        if not rows:continue
        with open(os.path.join(outdir,fn),"w",newline="",encoding="utf-8") as f:
            fields=[]
            for row in rows:
                for k in row:
                    if k not in fields: fields.append(k)
            w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
    return r


# ==============================================================================================
# SECTION 11 Programme capital: coupling the transition and the removal programme
# ==============================================================================================
# The emissions transition and the CDR programme are each costed, but until now they were
# never added together. That gap matters: the transition module's own investment envelope is
# roughly the same size as the entire CDR bill, and the settlement envelope the finance module
# tests against is a cap on the sum, not on either part alone.

@dataclass(frozen=True)
class ProgrammeCapitalInputs:
    settlement_envelope_fraction_gdp: float = 0.0214
    transition_public_share: float = 0.35
    transition_public_share_low: float = 0.15
    transition_public_share_high: float = 0.60


def programme_capital(s: Scenario, land_case: str = "central",
                      p: ProgrammeCapitalInputs = ProgrammeCapitalInputs()) -> Dict:
    """Combined annual capital requirement of decarbonization plus carbon removal.

    Clean-transition investment and CDR spending are drawn from the same real economy and,
    to whatever extent either is publicly funded, from the same fiscal or settlement-fee
    envelope. Reporting them separately understates the aggregate claim on output.

    Not all transition investment is public: most clean-energy capital is private and
    partly displaces fossil investment that would otherwise have occurred. The public
    share is therefore an explicit input with a stated range, and both the gross combined
    requirement and the publicly-funded subset are reported.
    """
    fin = FinanceInputs()
    trans = transition_run_case(getattr(s, "transition_case_key", "iea_nze_reference"))
    trans_by_year = {r["year"]: r for r in trans["rows"]}
    cdr_rows = dynamic_finance_ramp(s, land_case)

    rows: List[Dict] = []
    for r in cdr_rows:
        year = r["year"]
        t = trans_by_year.get(year)
        if t is None:
            continue
        gdp = r["gdp_screen_usd_tn"]
        transition_capex = t["transition_investment_usd_tn"]
        cdr_spend = r["dynamic_cdr_spend_usd_tn"]
        combined = transition_capex + cdr_spend
        envelope = gdp * p.settlement_envelope_fraction_gdp
        rows.append({
            "year": year, "gdp_screen_usd_tn": gdp,
            "transition_investment_usd_tn": transition_capex,
            "cdr_spend_usd_tn": cdr_spend,
            "combined_capital_usd_tn": combined,
            "combined_fraction_gdp": combined / gdp if gdp > 0 else math.nan,
            "public_transition_investment_usd_tn": transition_capex * p.transition_public_share,
            "public_combined_usd_tn": transition_capex * p.transition_public_share + cdr_spend,
            "public_combined_fraction_gdp": (
                (transition_capex * p.transition_public_share + cdr_spend) / gdp if gdp > 0 else math.nan),
            "settlement_envelope_usd_tn": envelope,
            "gross_within_settlement_envelope": combined <= envelope + 1e-12,
            "public_within_settlement_envelope": (
                transition_capex * p.transition_public_share + cdr_spend) <= envelope + 1e-12,
        })

    peak = max(rows, key=lambda x: x["combined_fraction_gdp"]) if rows else {}
    breaches = [x["year"] for x in rows if not x["gross_within_settlement_envelope"]]
    public_breaches = [x["year"] for x in rows if not x["public_within_settlement_envelope"]]
    mature = next((x for x in rows if x["year"] == s.cdr_maturity_year), rows[-1] if rows else {})

    def public_case(share: float) -> Dict:
        vals = [(x["transition_investment_usd_tn"] * share + x["cdr_spend_usd_tn"]) / x["gdp_screen_usd_tn"]
                for x in rows if x["gdp_screen_usd_tn"] > 0]
        return {"public_share": share, "peak_fraction_gdp": max(vals) if vals else math.nan,
                "exceeds_envelope": (max(vals) if vals else 0.0) > p.settlement_envelope_fraction_gdp}

    return {
        "classification": ("Screening aggregation of two separately modelled capital streams. It is not "
                           "a macroeconomic crowding-out, fiscal-incidence or investment-displacement "
                           "model, and it does not net out avoided fossil capital expenditure."),
        "inputs": asdict(p),
        "cumulative_transition_capital_to_2050_usd_tn": trans["cumulative_transition_capital_to_2050_usd_tn"],
        "mature_year": mature.get("year"),
        "mature_transition_investment_usd_tn": mature.get("transition_investment_usd_tn"),
        "mature_cdr_spend_usd_tn": mature.get("cdr_spend_usd_tn"),
        "mature_combined_usd_tn": mature.get("combined_capital_usd_tn"),
        "mature_combined_fraction_gdp": mature.get("combined_fraction_gdp"),
        "peak_combined_year": peak.get("year"),
        "peak_combined_usd_tn": peak.get("combined_capital_usd_tn"),
        "peak_combined_fraction_gdp": peak.get("combined_fraction_gdp"),
        "gross_envelope_breach_years": breaches,
        "public_envelope_breach_years": public_breaches,
        "public_share_sensitivity": [public_case(x) for x in
                                     (p.transition_public_share_low, p.transition_public_share,
                                      p.transition_public_share_high)],
        "finding": ("The CDR bill alone stays inside the settlement envelope. The transition investment "
                    "the emissions module itself requires is of comparable size, and the gross combined "
                    "requirement does not. Any claim that the settlement mechanism can fund the programme "
                    "must state which of the two streams it is funding."),
        "rows": rows,
    }


# ==============================================================================================
# SECTION 12 Transition calibration transparency
# ==============================================================================================
# The reference emissions trajectory is produced by fitting two parameters: investment
# effectiveness, calibrated to the IEA 2035 energy-related CO2 anchor, and a post-2035
# acceleration multiplier, calibrated so that total CO2 reaches the residual floor in 2050.
# The second fit is doing a great deal of work and was previously invisible. Reporting the
# same capital-turnover physics without it converts a hidden assumption into a stated result.

def transition_calibration_audit(s: Scenario, land_case: str = "central") -> Dict:
    cal = transition_reference_calibration()
    case = TRANSITION_CASES[getattr(s, "transition_case_key", "iea_nze_reference")]

    fitted = transition_run_case(case.key)
    unfitted = _transition_raw_run(case, cal["investment_effectiveness"], 1.0, TRANSITION_END_YEAR)

    def restoration_under(path_rows: List[Dict]) -> Dict:
        table = {r["year"]: r["gross_emissions_gtco2"] for r in path_rows}
        original = globals()["gross_emissions_path"]
        globals()["gross_emissions_path"] = (
            lambda year, sc, _t=table: _t.get(year, sc.residual_emissions_gtco2))
        try:
            c = carbon_cycle(s, land_case, maintain_after_target_years=0)
            cl = climate_run(c["rows"])
            return {"crossing_year": c["crossing_year"], "peak_co2_ppm": c["peak_co2_ppm"],
                    "peak_warming_c": cl["peak_warming_c"],
                    "years_above_1p5": cl["years_above_1p5"],
                    "cumulative_emissions_to_2100_gtco2": sum(
                        x["gross_emissions_gtco2"] for x in c["rows"] if x["year"] <= 2100)}
        finally:
            globals()["gross_emissions_path"] = original

    f = restoration_under(fitted["rows"])
    u = restoration_under(unfitted["rows"])

    return {
        "classification": "Disclosure of what the reference emissions calibration assumes.",
        "investment_effectiveness_fitted_to": "IEA WEO 2025 NZE 2035 energy-related CO2 anchor",
        "investment_effectiveness": cal["investment_effectiveness"],
        "post_2035_acceleration_fitted_to": "total CO2 reaching the 1.5 GtCO2/yr residual floor in 2050",
        "post_2035_acceleration_multiplier": cal["reference_post_2035_acceleration"],
        "residual_floor_year_with_fitted_acceleration": fitted["residual_floor_year"],
        "residual_floor_year_without_fitted_acceleration": unfitted["residual_floor_year"],
        "restoration_with_fitted_acceleration": f,
        "restoration_without_fitted_acceleration": u,
        "finding": (
            "Net zero by 2050 is not a result of the capital-turnover physics. At the calibrated "
            "technology effectiveness and the reference investment envelope, the same model reaches "
            "the residual floor in {} rather than {}; the 2050 date requires a {:.1f}x step change in "
            "conversion rate after 2035, fitted rather than derived. The restoration date is far less "
            "sensitive to this than the net-zero date is ({} versus {}), because sustained CDR rather "
            "than the last increment of abatement governs the drawdown."
        ).format(unfitted["residual_floor_year"], fitted["residual_floor_year"],
                 cal["reference_post_2035_acceleration"], u["crossing_year"], f["crossing_year"]),
    }


def transition_case_restoration_matrix(s: Scenario, land_case: str = "central") -> List[Dict]:
    """Restoration outcome under every transition case, not just the reference."""
    out: List[Dict] = []
    original = globals()["gross_emissions_path"]
    try:
        for key, case in TRANSITION_CASES.items():
            run = transition_run_case(key)
            table = {r["year"]: r["gross_emissions_gtco2"] for r in run["rows"]}
            globals()["gross_emissions_path"] = (
                lambda year, sc, _t=table: _t.get(year, sc.residual_emissions_gtco2))
            c = carbon_cycle(s, land_case, maintain_after_target_years=0)
            cl = climate_run(c["rows"])
            out.append({
                "case_key": key, "case": case.name,
                "residual_floor_year": run["residual_floor_year"],
                "gross_emissions_2030_gtco2": next(
                    x["gross_emissions_gtco2"] for x in run["rows"] if x["year"] == 2030),
                "cumulative_transition_capital_to_2050_usd_tn":
                    run["cumulative_transition_capital_to_2050_usd_tn"],
                "peak_co2_ppm": c["peak_co2_ppm"], "peak_year": c["peak_year"],
                "return_280_year": c["crossing_year"],
                "peak_warming_c": cl["peak_warming_c"],
                "years_above_1p5c": cl["years_above_1p5"],
            })
    finally:
        globals()["gross_emissions_path"] = original
    return out


# Attach the two new sections to the integrated result set.
_base_integrated_results = integrated_results


def integrated_results(s: Scenario = Scenario(), land_case: str = "central") -> Dict:  # noqa: F811
    r = _base_integrated_results(s, land_case)
    r["programme_capital"] = programme_capital(s, land_case)
    r["transition_calibration_audit"] = transition_calibration_audit(s, land_case)
    r["transition_case_restoration_matrix"] = transition_case_restoration_matrix(s, land_case)
    return r


def run_new_section_tests() -> None:
    """Assertions for the programme-capital and calibration-audit sections."""
    s = Scenario()

    # P1. Programme capital must be the sum of its parts, every year.
    pc = programme_capital(s)
    assert pc["rows"], "no programme-capital rows"
    for row in pc["rows"]:
        assert abs(row["combined_capital_usd_tn"]
                   - (row["transition_investment_usd_tn"] + row["cdr_spend_usd_tn"])) < 1e-9
        assert abs(row["combined_fraction_gdp"]
                   - row["combined_capital_usd_tn"]/row["gdp_screen_usd_tn"]) < 1e-12
        assert row["public_combined_usd_tn"] <= row["combined_capital_usd_tn"] + 1e-12

    # P2. The coupling must actually bind somewhere, or it is not telling us anything.
    # CDR alone fits inside the settlement envelope; the gross combined requirement does not.
    mature = next(x for x in pc["rows"] if x["year"] == s.cdr_maturity_year)
    assert mature["cdr_spend_usd_tn"] < mature["settlement_envelope_usd_tn"]
    assert mature["combined_capital_usd_tn"] > mature["settlement_envelope_usd_tn"]
    assert pc["gross_envelope_breach_years"], "combined requirement never tested against the envelope"

    # P3. Public share must be monotonic in the burden it produces.
    fr = [c["peak_fraction_gdp"] for c in pc["public_share_sensitivity"]]
    assert fr == sorted(fr), "public-share sensitivity is not monotonic"

    # P4. The reference emissions trajectory is fitted, and the audit must say by how much.
    ta = transition_calibration_audit(s)
    assert ta["post_2035_acceleration_multiplier"] > 1.0
    assert (ta["residual_floor_year_without_fitted_acceleration"]
            > ta["residual_floor_year_with_fitted_acceleration"]), (
        "the fitted acceleration must be shown to be doing work")
    assert (ta["restoration_without_fitted_acceleration"]["crossing_year"]
            >= ta["restoration_with_fitted_acceleration"]["crossing_year"])

    # P5. Every transition case must produce a distinct, ordered outcome. A slower
    # transition must never restore earlier than a faster one.
    matrix = transition_case_restoration_matrix(s)
    assert len(matrix) == len(TRANSITION_CASES)
    ordered = sorted(matrix, key=lambda x: x["residual_floor_year"])
    years = [x["return_280_year"] for x in ordered]
    assert years == sorted(years), f"restoration order inconsistent with transition speed: {years}"
    peaks = [x["peak_co2_ppm"] for x in ordered]
    assert peaks[0] == min(peaks), "fastest transition should give the lowest peak CO2"


# ==============================================================================================
# SECTION 13 Figure generation
# ==============================================================================================
def build_all_figures(results: Optional[Dict] = None) -> str:
    """Regenerate every figure from the model. Requires matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import os
    import matplotlib.pyplot as plt

    HERE=os.path.dirname(os.path.abspath(__file__))
    OUT=os.path.join(HERE,"figures")
    os.makedirs(OUT,exist_ok=True)
    r = results or integrated_results()

    # 1 carbon scenarios
    plt.figure(figsize=(9,5.4))
    for item in scenario_library():
        c=carbon_cycle(item["scenario"],item["land_case"],maintain_after_target_years=0)
        xs=[x["year"] for x in c["rows"]]; ys=[x["co2_ppm"] for x in c["rows"]]
        plt.plot(xs,ys,label=item["scenario"].name)
    plt.axhline(280,linestyle="--",linewidth=1)
    plt.xlabel("Year");plt.ylabel("Atmospheric CO$_2$ (ppm)");plt.title("Atmospheric CO$_2$ under dynamically constrained scenarios")
    plt.legend(fontsize=8);plt.tight_layout();plt.savefig(os.path.join(OUT,"carbon_scenarios.png"),dpi=180);plt.close()

    # 2 land nexus CDR effect
    rows=r["land_stress_matrix"]
    plt.figure(figsize=(8.5,5.2))
    labels=[];planned=[];feasible=[]
    for x in rows:
        if x["year"]==2043:
            labels.append(x["case"]);planned.append(x["planned_cdr_gtco2"]);feasible.append(x["feasible_cdr_gtco2"])
    pos=list(range(len(labels)))
    plt.bar([i-0.18 for i in pos],planned,width=0.36,label="Planned")
    plt.bar([i+0.18 for i in pos],feasible,width=0.36,label="Land/blue-water feasible")
    plt.xticks(pos,labels);plt.ylabel("Incremental CDR (GtCO$_2$/yr)");plt.title("Land-water nexus effect on the 2043 CDR portfolio")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"land_nexus.png"),dpi=180);plt.close()

    # 3 blue-water utilization by land case
    plt.figure(figsize=(8.5,5.2))
    labels=[];water=[];screen=[]
    for x in rows:
        if x["year"]==2043:
            labels.append(x["case"])
            water.append(x["incremental_cdr_blue_water_km3_yr"])
            screen.append(x["incremental_blue_water_screen_km3_yr"])
    pos=list(range(len(labels)))
    plt.bar([i-0.18 for i in pos],water,width=0.36,label="Managed CDR blue-water use")
    plt.bar([i+0.18 for i in pos],screen,width=0.36,label="Stress-screen anchor")
    plt.xticks(pos,labels);plt.ylabel("km$^3$/yr");plt.title("Incremental managed blue-water stress screen")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"land_blue_water_stress.png"),dpi=180);plt.close()

    # 4 albedo-only stress diagnostic
    plt.figure(figsize=(8.5,5.2))
    labels=[];forcing=[]
    for x in rows:
        if x["year"]==2043:
            labels.append(x["case"]);forcing.append(x["boreal_albedo_stress_global_forcing_w_m2"])
    plt.bar(range(len(labels)),forcing)
    plt.xticks(range(len(labels)),labels)
    plt.ylabel("Global-mean W/m$^2$")
    plt.title("Uncompensated boreal albedo-only stress diagnostic")
    plt.tight_layout();plt.savefig(os.path.join(OUT,"land_albedo_stress.png"),dpi=180);plt.close()

    # 5 differentiated learning + scarcity cost
    learn=r["learning_curves"]["rows"]
    plt.figure(figsize=(8.5,5.2))
    plt.plot([x["year"] for x in learn],[x["dynamic_blended_cost_usd_t"] for x in learn],label="Learning + scarcity")
    plt.axhline(185,linestyle="--",linewidth=1,label="$185/t flat counterfactual")
    plt.xlabel("Year");plt.ylabel("Blended CDR cost (USD/tCO$_2$)");plt.title("Differentiated CDR learning and scarcity sensitivity")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"cdr_learning_scarcity_curve.png"),dpi=180);plt.close()

    # 6 finance
    plt.figure(figsize=(8.5,5.2))
    plt.plot([x["year"] for x in learn],[x["dynamic_cdr_spend_usd_tn"] for x in learn],label="Learning + scarcity CDR spend")
    plt.plot([x["year"] for x in learn],[x["learning_only_no_scarcity_spend_usd_tn"] for x in learn],label="Learning-only counterfactual")
    plt.plot([x["year"] for x in learn],[x["settlement_cap_usd_tn"] for x in learn],label="2.14% GDP envelope")
    plt.xlabel("Year");plt.ylabel("USD trillion per year");plt.title("Dynamic CDR spend versus settlement envelope")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"finance_dynamic.png"),dpi=180);plt.close()

    # 7 monetary redemption price resilience
    money=r["monetary_architecture"]["liquidity_stress"]["rows"]
    plt.figure(figsize=(9,5.4))
    plt.bar(range(len(money)),[x["effective_price_fraction_of_reference"] for x in money])
    plt.axhline(0.98,linestyle="--",linewidth=1,label="98% reference-price threshold")
    plt.xticks(range(len(money)),[x["case"] for x in money],rotation=20,ha="right")
    plt.ylabel("Effective redemption price / timber reference");plt.title("Timber-reference redemption stress")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"monetary_redemption_price.png"),dpi=180);plt.close()

    # 8 post-redemption net reserve ratio
    plt.figure(figsize=(9,5.4))
    plt.bar(range(len(money)),[x["post_redemption_net_reserve_ratio"] for x in money])
    plt.axhline(1.0,linestyle="--",linewidth=1,label="1.0x net reserve threshold")
    plt.xticks(range(len(money)),[x["case"] for x in money],rotation=20,ha="right")
    plt.ylabel("Post-redemption net reserve ratio");plt.title("Reserve liquidity mismatch stress")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"monetary_liquidity_stress.png"),dpi=180);plt.close()

    # 9 energy balance
    energy=r["energy"]
    names=["Pre-CDR system","CDR electricity","Marine cleanup","Water core","Desalination backstop"]
    vals=[energy["pre_cdr_transformed_electricity_twh_yr"],energy["cdr_direct_electricity_twh_yr"],energy["marine_cleanup_electricity_twh_yr"],energy["core_water_electricity_twh_yr"],energy["desalination_backstop_twh_yr"]]
    plt.figure(figsize=(8.5,5.2));plt.bar(names,vals);plt.xticks(rotation=20,ha="right");plt.ylabel("TWh/yr");plt.title("Annual transformed-electricity components")
    plt.tight_layout();plt.savefig(os.path.join(OUT,"energy_balance.png"),dpi=180);plt.close()

    # --- warming trajectory and overshoot ---------------------------------------------------
    cl=r["climate_response"]
    rows=[q for q in cl["central_rows"] if q["year"]<=2200]
    xs=[q["year"] for q in rows]
    fig,ax=plt.subplots(3,1,figsize=(9,9.5),sharex=True,gridspec_kw={"height_ratios":[1,1,0.85]})
    ax[0].plot(xs,[q["co2_ppm"] for q in rows],color="k")
    ax[0].axhline(280,linestyle="--",linewidth=1,color="0.4")
    ax[0].set_ylabel("CO$_2$ (ppm)");ax[0].set_title("Design case: concentration, warming and energy imbalance")
    ax[1].plot(xs,[q["surface_warming_c"] for q in rows],color="crimson",label="Surface")
    ax[1].plot(xs,[q["deep_ocean_warming_c"] for q in rows],color="navy",label="Deep ocean")
    ax[1].axhline(1.5,linestyle="--",linewidth=1,color="0.5")
    ax[1].axhline(2.0,linestyle=":",linewidth=1,color="0.5")
    ax[1].fill_between(xs,1.5,[max(1.5,q["surface_warming_c"]) for q in rows],color="crimson",alpha=0.15)
    c0=cl["central"]
    ax[1].annotate(f"peak {c0['peak_warming_c']:.2f} C ({c0['peak_warming_year']})\n"
                   f"{c0['years_above_1p5']} yr above 1.5 C",
                   (c0["peak_warming_year"],c0["peak_warming_c"]),xytext=(15,10),
                   textcoords="offset points",fontsize=8)
    ax[1].set_ylabel(r"Warming vs 1850-1900 ($^\circ$C)");ax[1].legend(fontsize=8)
    ax[2].plot(xs,[q["earth_energy_imbalance_w_m2"] for q in rows],color="darkgreen")
    ax[2].axhline(0,linewidth=0.8,color="0.4")
    ax[2].set_ylabel("Energy imbalance (W m$^{-2}$)");ax[2].set_xlabel("Year")
    plt.tight_layout();plt.savefig(os.path.join(OUT,"climate_response.png"),dpi=180);plt.close()

    # --- climate sensitivity spread ---------------------------------------------------------
    plt.figure(figsize=(8.6,5.2))
    for case in cl["sensitivity_cases"]:
        p=ClimateParams(**case["params"])
        rr=climate_run(r["carbon"]["rows"],p)
        q=[z for z in rr["rows"] if z["year"]<=2200]
        plt.plot([z["year"] for z in q],[z["surface_warming_c"] for z in q],
                 label=f"{p.name} (peak {rr['peak_warming_c']:.2f} C)")
    plt.axhline(1.5,linestyle="--",linewidth=1,color="0.5")
    plt.axhline(2.0,linestyle=":",linewidth=1,color="0.5")
    plt.xlabel("Year");plt.ylabel(r"Warming vs 1850-1900 ($^\circ$C)")
    plt.title("Warming across the AR6 climate-sensitivity range")
    plt.legend(fontsize=8);plt.tight_layout()
    plt.savefig(os.path.join(OUT,"climate_sensitivity.png"),dpi=180);plt.close()

    # --- ensemble return-year distribution --------------------------------------------------
    ens=r["bounded_sensitivity_ensemble"]
    years=ens.get("return_year_samples",[])
    plt.figure(figsize=(9,5.2))
    plt.hist(years,bins=40,color="0.72",edgecolor="0.4")
    det=r["carbon"]["crossing_year"]
    plt.axvline(det,color="crimson",linewidth=1.6,label=f"Calibrated reference ({det})")
    plt.axvline(ens["return_year_p50"],color="navy",linestyle="--",linewidth=1.4,label=f"Coupled sensitivity median ({ens['return_year_p50']:.0f})")
    plt.xlabel("Year of first return to 280 ppm");plt.ylabel("Returning draws")
    plt.title(f"Coupled bounded sensitivity ({ens['fraction_not_restored_within_horizon']*100:.1f}% do not return)")
    plt.legend(fontsize=8);plt.tight_layout()
    plt.savefig(os.path.join(OUT,"ensemble_return_year.png"),dpi=180);plt.close()

    print("FIGURES BUILT")

    # 10 FaIR-form structural carbon cross-check
    fair=r["fair_form_carbon_crosscheck"]
    main=r["carbon"]["rows"]
    fair_rows=fair["central_rows"]
    plt.figure(figsize=(9,5.4))
    plt.plot([x["year"] for x in main],[x["co2_ppm"] for x in main],label="Joos reservoir-memory central")
    plt.plot([x["year"] for x in fair_rows],[x["co2_ppm"] for x in fair_rows],label="FaIR-v2-form structural cross-check")
    plt.axhline(280,linestyle="--",linewidth=1)
    plt.xlabel("Year");plt.ylabel("Atmospheric CO$_2$ (ppm)")
    plt.title("Reduced-complexity carbon-cycle structural cross-check")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"carbon_model_crosscheck.png"),dpi=180);plt.close()

    # 11 settlement collection -> funded CDR feedback
    fb=r["settlement_collection"]["funding_feedback"]["cases"]
    plt.figure(figsize=(9,5.4))
    plt.bar(range(len(fb)),[x["maturity_funded_cdr_gtco2_yr"] for x in fb])
    plt.axhline(r["cdr_portfolio"]["cdr_gtco2_yr"],linestyle="--",linewidth=1,label="Physically feasible maturity CDR")
    plt.xticks(range(len(fb)),[x["case"] for x in fb],rotation=20,ha="right")
    plt.ylabel("Funded CDR at maturity (GtCO$_2$/yr)")
    plt.title("Settlement leakage feeds back into physical CDR deployment")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"settlement_funding_feedback.png"),dpi=180);plt.close()

    # 12 8760-hour adequacy frontier
    grid=r["grid_reliability_stress"]
    front=grid["adequacy_frontier_rows"]
    plt.figure(figsize=(9,5.4))
    plt.bar(range(len(front)),[x["minimum_vre_overbuild"] for x in front])
    plt.axhline(1.0,linestyle="--",linewidth=1,label="No VRE overbuild")
    plt.xticks(range(len(front)),[x["case"] for x in front],rotation=20,ha="right")
    plt.ylabel("Minimum VRE energy overbuild factor")
    plt.title("Synthetic 8760-hour adequacy frontier at fixed storage and firm share")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"grid_adequacy_frontier.png"),dpi=180);plt.close()

    # 13 baseline hourly adequacy failures
    base=grid["rows"]
    plt.figure(figsize=(9,5.4))
    plt.bar(range(len(base)),[100*x["unserved_energy_fraction"] for x in base])
    plt.axhline(0.01,linestyle="--",linewidth=1,label="0.01% adequacy threshold")
    plt.xticks(range(len(base)),[x["case"] for x in base],rotation=20,ha="right")
    plt.ylabel("Unserved annual energy (%)")
    plt.title("Annual energy balance does not guarantee hourly adequacy")
    plt.legend();plt.tight_layout();plt.savefig(os.path.join(OUT,"grid_reliability_stress.png"),dpi=180);plt.close()


    # 14 endogenous emissions transition
    trans=r["emissions_transition"]
    plt.figure(figsize=(9,5.4))
    plt.plot([x["year"] for x in trans["rows"]],[x["gross_emissions_gtco2"] for x in trans["rows"]],label="Total CO2")
    plt.plot([x["year"] for x in trans["rows"]],[x["energy_related_co2_gtco2"] for x in trans["rows"]],label="Energy-related CO2")
    plt.axhline(18.0,linestyle="--",linewidth=1,label="IEA NZE 2035 energy-related anchor")
    plt.axhline(1.5,linestyle=":",linewidth=1,label="Residual floor")
    plt.xlim(2026,2070);plt.xlabel("Year");plt.ylabel("Gross CO$_2$ (Gt/yr)")
    plt.title("Endogenous reduced-form capital-turnover emissions transition")
    plt.legend(fontsize=8);plt.tight_layout();plt.savefig(os.path.join(OUT,"emissions_transition.png"),dpi=180);plt.close()

    # 15 emissions transition case comparison
    plt.figure(figsize=(9,5.4))
    for key in ["iea_nze_reference","high_acceleration","current_investment_constrained","natural_turnover","delayed_finance"]:
        tr=transition_run_case(key)
        q=[x for x in tr["rows"] if x["year"]<=2070]
        plt.plot([x["year"] for x in q],[x["gross_emissions_gtco2"] for x in q],label=tr["case"])
    plt.xlabel("Year");plt.ylabel("Gross CO$_2$ (Gt/yr)")
    plt.title("Capital-turnover and finance cases generate different emissions paths")
    plt.legend(fontsize=7);plt.tight_layout();plt.savefig(os.path.join(OUT,"emissions_transition_cases.png"),dpi=180);plt.close()
    return OUT



# ==============================================================================================
# SECTION 14 Test suite
# ==============================================================================================
import math


def close(a,b,tol=1e-8):
    return abs(a-b) <= tol*max(1.0,abs(a),abs(b))


def run_tests():
    s=Scenario()
    r=integrated_results(s,"central")

    # Carbon initialization reproduces starting concentration and sink calibration.
    init=r["carbon"]["initialization"]
    ppm=PREINDUSTRIAL_CO2_PPM+sum(init["state_gtc"])/CO2_MASS_GTC_PER_PPM
    assert close(ppm, START_CO2_PPM, 1e-10)
    assert close(init["implied_sink_gtc_yr"], s.observed_natural_sink_gtc_yr, 1e-8)

    # Cross-module propagation: lower planned CDR lowers physical demand and finance.
    low=Scenario(mature_incremental_cdr_gtco2=10.0,cdr_maturity_year=2050)
    rlow=integrated_results(low,"central")
    assert rlow["cdr_portfolio"]["cdr_gtco2_yr"] < r["cdr_portfolio"]["cdr_gtco2_yr"]
    assert rlow["energy"]["cdr_direct_electricity_twh_yr"] < r["energy"]["cdr_direct_electricity_twh_yr"]
    assert rlow["minerals"]["total_central_gt_yr"] < r["minerals"]["total_central_gt_yr"]
    assert rlow["finance"]["maturity_dynamic_cdr_spend_usd_tn_yr"] < r["finance"]["maturity_dynamic_cdr_spend_usd_tn_yr"]

    # Land/water nexus: central feasible; low-efficiency binds and reduces CDR.
    pc=effective_cdr_path(s.cdr_maturity_year,s,"central")
    pl=effective_cdr_path(s.cdr_maturity_year,s,"low_efficiency")
    assert pc["land_nexus"]["binding"] is False
    assert pl["land_nexus"]["binding"] is True
    assert pl["cdr_gtco2_yr"] < pc["cdr_gtco2_yr"]
    assert pl["land_nexus"]["realized_cdr_land_mha"] <= pl["land_nexus"]["food"]["remaining_agricultural_land_mha"] + 1e-8
    assert pc["land_nexus"]["realized_incremental_blue_water_km3_yr"] <= pc["land_nexus"]["incremental_blue_water_screen_km3_yr"] + 1e-8
    assert pl["land_nexus"]["realized_incremental_blue_water_km3_yr"] <= pl["land_nexus"]["incremental_blue_water_screen_km3_yr"] + 1e-8

    # Food land is protected first.
    f2085=food_land(2085,LAND_CASES["low_efficiency"])
    assert f2085["food_land_deficit_mha"] > 0
    assert close(f2085["remaining_agricultural_land_mha"],0.0)

    # Hydrology/albedo diagnostics are explicit and not silently converted to CO2 credits.
    ln=pc["land_nexus"]
    assert ln["restoration_et_increment_diagnostic_km3_yr"] > 0
    assert ln["uncompensated_boreal_albedo_only_global_forcing_w_m2"] > 0
    bio=next(x for x in pc["rows"] if x["pathway"]=="Biological restoration")
    assert bio["credited_new_boreal_afforestation_fraction"] == 0.0

    # Differentiated economics: learning reduces learnable components, scarcity raises
    # marginal cost for land/site-limited pathways as utilization rises.
    for a in DEFAULT_LEARNING.values():
        c0=wright_cost(a.initial_cumulative_gt,a)
        c1=wright_cost(a.initial_cumulative_gt*2,a)
        assert c1 <= c0 + 1e-12 or a.learnable_cost_share == 0
        assert c1 >= a.floor_cost_usd_t - 1e-12
    bio_a=DEFAULT_LEARNING["Biological restoration"]
    bio_low=pathway_economic_detail(20.0,0.10,bio_a)["marginal_cost_usd_t"]
    bio_high=pathway_economic_detail(20.0,0.90,bio_a)["marginal_cost_usd_t"]
    assert bio_high > bio_low
    dac_a=DEFAULT_LEARNING["DACCS"]
    dac_low=pathway_economic_detail(20.0,0.10,dac_a)["marginal_cost_usd_t"]
    dac_high=pathway_economic_detail(20.0,0.90,dac_a)["marginal_cost_usd_t"]
    assert close(dac_low,dac_high)
    assert r["learning_curves"]["maturity_spend_usd_tn"] >= r["learning_curves"]["maturity_learning_only_no_scarcity_spend_usd_tn"]

    # Dynamic finance remains within the selected envelope in the central screen.
    assert r["finance"]["maturity_dynamic_cdr_spend_usd_tn_yr"] <= r["finance"]["central_envelope_capacity_usd_tn_yr"]

    # Desalination contingency is explicit in full-backstop energy balance.
    e=r["energy"]
    assert close(e["full_desalination_backstop_transformed_electricity_twh_yr"]-e["core_transformed_electricity_twh_yr"],e["desalination_backstop_twh_yr"])

    # Seaweed nutrient mass balance is explicit.
    sw=r["seaweed"]
    assert sw["n_required_for_full_potential_mt_yr"] >= sw["credited_eutrophic_n_mt_yr"]
    assert sw["p_required_for_full_potential_mt_yr"] >= sw["credited_eutrophic_p_mt_yr"]

    # Plastic qualified feedstock is derived from stock flows rather than inserted.
    p=r["plastics"]
    expected=(p["legacy_removed_mt"]+p["intercepted_new_with_prevention_mt"])*PlasticInputs().structural_qualification_yield
    assert close(p["qualified_marine_polymer_with_prevention_mt"],expected)

    # Timber-reference unit: reference moves with timber; severe reserve-liquidity
    # mismatch produces a peg/redemption break instead of assuming timber is cash.
    base=simulate_case(MONETARY_DEFAULT_CASES[0])
    timber_up=simulate_case(MONETARY_DEFAULT_CASES[1])
    severe=simulate_case(next(c for c in MONETARY_DEFAULT_CASES if c.name=="Severe combined"))
    assert close(base["reference_usd_per_unit"],1.0)
    assert close(timber_up["reference_usd_per_unit"],1.3)
    assert base["liquidity_test_pass"] is True
    assert severe["liquidity_test_pass"] is False
    assert severe["effective_price_fraction_of_reference"] < 0.98

    # Wealth conversion remains share-neutral only as an accounting identity.
    assert r["monetary_architecture"]["wealth_conversion"]["max_share_error"] < 1e-12

    # FaIR-v2-form cross-check is state dependent and is explicitly not the official calibrated posterior.
    fair=r["fair_form_carbon_crosscheck"]
    assert "official FaIR" in fair["classification"]
    assert fair["cases"][0]["crossing_year"] is not None
    assert abs(fair["cases"][0]["crossing_year"]-r["carbon"]["crossing_year"]) < 25
    alphas=[x["alpha_lifetime"] for x in fair["central_rows"][:50]]
    assert max(alphas)-min(alphas) > 1e-6

    # Settlement collection mechanics: central collection funds the maturity target, severe migration does not.
    collection=r["settlement_collection"]["maturity_stress"]
    central=next(x for x in collection["rows"] if x["case"]=="Central collection")
    migration=next(x for x in collection["rows"] if x["case"]=="Severe migration stress")
    assert central["pass"] is True
    assert central["required_fee_fraction"] < 0.01
    assert migration["pass"] is False

    # Financial leakage feeds back into physical CDR rather than remaining a disconnected finance table.
    feedback=r["settlement_collection"]["funding_feedback"]["cases"]
    ff_central=next(x for x in feedback if x["case"]=="Central collection")
    ff_severe=next(x for x in feedback if x["case"]=="Severe migration stress")
    assert close(ff_central["maturity_funded_cdr_gtco2_yr"],r["cdr_portfolio"]["cdr_gtco2_yr"])
    assert ff_severe["maturity_funded_cdr_gtco2_yr"] < ff_central["maturity_funded_cdr_gtco2_yr"]
    assert ff_severe["crossing_year"] is None or ff_severe["crossing_year"] > ff_central["crossing_year"]

    # 8760-hour power stress can fail annual-TWh designs, while a one-dimensional overbuild frontier can recover adequacy.
    grid=r["grid_reliability_stress"]
    assert len(grid["failed_cases"]) >= 1
    assert all(x["frontier_found"] for x in grid["adequacy_frontier_rows"])
    assert all(x["minimum_vre_overbuild"] >= 1.0 for x in grid["adequacy_frontier_rows"])
    under=next(x for x in grid["rows"] if x["case"]=="Underbuilt VRE / 12h storage")
    assert under["adequacy_pass"] is False

    # Sensitivity ensemble is not mislabeled as a probability forecast.
    assert "not an empirical probability forecast" in r["bounded_sensitivity_ensemble"]["classification"]

    # ---- Conservation and identity tests -------------------------------------
    # These test the physics, not merely that the code runs.

    # C1. Carbon reservoir mass balance, every year. The change in atmospheric excess
    # must equal the airborne part of the anthropogenic pulse minus the flux returned
    # to sinks. A fixed-airborne-fraction model cannot pass this.
    resp = JOOS_A[0] + sum(
        JOOS_A[i]*math.exp(-0.5/JOOS_TAU_YR[i]) for i in (1,2,3))
    prev = r["carbon"]["initialization"]["total_excess_gtc"]
    for row in r["carbon"]["rows"]:
        cur = (row["co2_ppm"]-PREINDUSTRIAL_CO2_PPM)*CO2_MASS_GTC_PER_PPM
        pred = (prev - row["natural_reservoir_flux_to_sinks_gtc"]
                + row["net_anthropogenic_gtco2"]/CO2_GTC_TO_GTCO2*resp)
        assert close(pred, cur, 1e-9), (row["year"], pred, cur)
        prev = cur

    # C2. Reaching the target is not the end of the obligation.
    maint = r["carbon"]["steady_state_maintenance_cdr_gtco2_yr"]
    assert maint is not None and maint > s.residual_emissions_gtco2
    assert r["carbon"]["target_held"] is True
    assert r["carbon"]["max_maintenance_co2_ppm"] <= TARGET_CO2_PPM + 1e-9

    # C3. Electricity identity and separation of process heat from electricity.
    assert close(e["core_transformed_electricity_twh_yr"],
                 e["pre_cdr_transformed_electricity_twh_yr"]
                 + e["cdr_direct_electricity_twh_yr"]
                 + e["marine_cleanup_electricity_twh_yr"]
                 + e["core_water_electricity_twh_yr"])
    assert e["cdr_low_grade_heat_twhth_yr"] > 0

    # C4. Water mass balance.
    w=r["water"]; wi=WaterInputs()
    assert w["wastewater_reused_km3_yr"] <= w["wastewater_collected_km3_yr"] + 1e-9
    assert w["wastewater_collected_km3_yr"] <= w["municipal_water_km3_yr"] + 1e-9
    assert close(w["wastewater_treatment_twh_yr"], w["wastewater_collected_km3_yr"]*wi.treatment_kwh_m3)

    # C5. Plastic mass conservation.
    pi=PlasticInputs()
    assert p["qualified_marine_polymer_with_prevention_mt"] <= (
        p["legacy_removed_mt"]+p["intercepted_new_with_prevention_mt"]) + 1e-9
    assert p["legacy_removed_mt"] <= pi.legacy_surface_macroplastic_mt + 1e-9
    gross_total = sum(row["gross_new_input_mt"] for row in p["annual_prevention_rows"])
    assert close(p["intercepted_new_with_prevention_mt"]+p["residual_new_with_prevention_mt"], gross_total)
    assert p["marine_share_of_demand_with_prevention"] <= 1.0 + 1e-9

    # C6. Seaweed nutrient closure.
    assert sw["nutrient_supported_biomass_without_other_sources_gt_yr"] < sw["area_yield_potential_gt_dry_yr"]
    assert close(sw["supplemental_or_natural_n_needed_for_full_potential_mt_yr"],
                 sw["n_required_for_full_potential_mt_yr"]-sw["credited_eutrophic_n_mt_yr"])

    # C7. Phosphorus full factorial ordering, adverse pairing reported.
    nut=r["nutrients"]
    assert nut["full_factorial_min_coverage"] <= nut["central_coverage"] <= nut["full_factorial_max_coverage"]
    assert nut["full_factorial_min_coverage"] < 1.0

    # C8. Land conservation in every land case and year, including the enhanced-weathering
    # cropland co-use that never enters the residual-land test.
    for case in LAND_CASES:
        for yr in (2043, 2050, 2085):
            n=effective_cdr_path(yr, s, case)["land_nexus"]
            assert n["realized_cdr_land_mha"] <= n["food"]["remaining_agricultural_land_mha"]+1e-6, (case,yr)
            assert n["realized_incremental_blue_water_km3_yr"] <= n["incremental_blue_water_screen_km3_yr"]+1e-6
            assert n["ew_spreading_area_mha"] <= n["ew_adoptable_cropland_mha"]+1e-6

    # C9. Scenario propagation: a slower transition must delay restoration, raise peak
    # concentration, raise cumulative removal and raise peak warming.
    fast=carbon_cycle(Scenario(emissions_mode="prescribed",residual_year=2050,residual_emissions_gtco2=1.5),"central",0)
    slow=carbon_cycle(Scenario(emissions_mode="prescribed",residual_year=2070,residual_emissions_gtco2=5.0),"central",0)
    assert slow["crossing_year"] > fast["crossing_year"]
    assert slow["peak_co2_ppm"] > fast["peak_co2_ppm"]
    assert (slow["cumulative_incremental_cdr_to_target_gtco2"]
            > fast["cumulative_incremental_cdr_to_target_gtco2"])
    assert climate_run(slow["rows"])["peak_warming_c"] > climate_run(fast["rows"])["peak_warming_c"]

    # C10. Endogenous emissions transition is generated from stock turnover and investment,
    # not a hard-coded linear path. The reference reproduces the IEA 2035 energy-related
    # anchor while alternative capital cases diverge.
    tr=r["emissions_transition"]
    assert tr["case_key"] == "iea_nze_reference"
    assert abs(tr["validation"]["energy_related_co2_2035_gt"]-18.0) < 0.05
    assert abs(tr["validation"]["total_co2_2026_gt"]-42.2) < 1e-9
    assert any(x["early_retirement_fraction"] > 0 for x in tr["sector_rows"] if x["year"] > 2030)
    cases={x["case_key"]:x for x in r["emissions_transition_cases"]}
    assert cases["high_acceleration"]["residual_floor_year"] < cases["current_investment_constrained"]["residual_floor_year"]
    assert cases["natural_turnover"]["residual_floor_year"] is None or cases["natural_turnover"]["residual_floor_year"] > 2060

    # C11. The ensemble must be able to represent a delayed transition and to fail.
    ens = r["bounded_sensitivity_ensemble"]
    assert ens["return_year_p95"] > fast["crossing_year"] + 100
    assert ens["noncrossing_samples"] > 0, "ensemble never explores failure to restore"
    assert ens["deterministic_central_percentile_rank"] is not None

    # ---- Climate module ------------------------------------------------------
    # T1. The energy-balance model is spun up from 1850 and must reproduce assessed
    # warming and sensitivity without being tuned to them.
    v = climate_validation()
    assert abs(v["warming_2024_c"] - v["warming_2024_reference_c"]) < 0.15, v["warming_2024_c"]
    assert abs(v["warming_2010_2019_c"] - v["warming_2010_2019_reference_c"]) < 0.20
    lo, hi = v["energy_imbalance_reference_range_w_m2"]
    assert lo <= v["energy_imbalance_2024_w_m2"] <= hi, v["energy_imbalance_2024_w_m2"]
    assert 2.5 <= v["equilibrium_climate_sensitivity_c"] <= 4.0
    assert 1.4 <= v["transient_climate_response_c"] <= 2.2

    # T2. Energy balance: the two-layer identity must hold each year.
    cl = r["climate_response"]
    prm = cl["central"]["params"]
    for row in cl["central_rows"]:
        implied = (row["total_forcing_w_m2"] - prm["climate_feedback"]*row["surface_warming_c"])
        assert close(implied, row["earth_energy_imbalance_w_m2"], 1e-9), row["year"]

    # T3. Higher sensitivity must give more warming; sensitivity cases must bracket.
    peaks = [c["peak_warming_c"] for c in cl["sensitivity_cases"]]
    ecs   = [c["equilibrium_climate_sensitivity_c"] for c in cl["sensitivity_cases"]]
    assert peaks[ecs.index(max(ecs))] == max(peaks)
    assert peaks[ecs.index(min(ecs))] == min(peaks)

    # T4. CO2 restoration is not climate restoration: warming and deep-ocean heat must
    # both still be positive when CO2 reaches the target.
    assert cl["central"]["warming_at_co2_target_c"] > 0.0
    assert cl["central"]["final_deep_ocean_warming_c"] > 0.0
    assert cl["central"]["warming_at_co2_target_c"] < cl["central"]["peak_warming_c"]

    # T5. Forcing must be monotonic in concentration and vanish at pre-industrial.
    assert close(co2_forcing(CLIMATE_PREINDUSTRIAL_PPM), 0.0)
    assert co2_forcing(560.0) > co2_forcing(280.0)
    assert close(co2_forcing(2*CLIMATE_PREINDUSTRIAL_PPM), F_2XCO2_W_M2, 1e-6)

    # T6. The FaIR-form cross-check must use the endogenous warming trajectory rather
    # than a temperature frozen for a century, and must report the difference.
    fair = r["fair_form_carbon_crosscheck"]
    assert "endogenous" in fair["cases"][0]["temperature_treatment"]
    assert fair["frozen_vs_endogenous_temperature_year_difference"] is not None

    print("ALL TESTS PASSED")



# ==============================================================================================
# SECTION 15 Workbook and authoritative headline-results generation
# ==============================================================================================
# The workbook and data/HEADLINE_RESULTS.md are derived artifacts, rebuilt from
# integrated_results() on every run. Nothing in them is hand-entered, so a document that
# disagrees with HEADLINE_RESULTS.md is stale by definition.
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter, column_index_from_string

import os
from typing import Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


WB_HERE = os.path.dirname(os.path.abspath(__file__))
WB_OUT = os.path.join(WB_HERE, "Planetary_Restoration_Integrated_Model.xlsx")

WB_TITLE = Font(name="Calibri", size=13, bold=True)
WB_HEAD = Font(name="Calibri", size=10, bold=True)
WB_BODY = Font(name="Calibri", size=10)
WB_NOTE = Font(name="Calibri", size=9, italic=True)
WB_HFILL = PatternFill("solid", fgColor="D9E2F3")
WB_WRAP = Alignment(wrap_text=True, vertical="top")


def _wb_fmt(value: float) -> str:
    """Pick a display format appropriate to the magnitude, so the workbook never
    shows raw floating-point precision next to rounded values."""
    a = abs(value)
    if a == 0:
        return "0"
    if a >= 1000:
        return "#,##0"
    if a >= 100:
        return "0.0"
    if a >= 1:
        return "0.000"
    if a >= 0.001:
        return "0.0000"
    return "0.00E+00"


def _wb_put(ws, row: int, col: int, value, *, font=WB_BODY, fill=None, number_format=None):
    c = ws.cell(row, col, value)
    c.font = font
    c.alignment = WB_WRAP
    if fill is not None:
        c.fill = fill
    if isinstance(value, float):
        c.number_format = number_format or _wb_fmt(value)
    return c


def _wb_table(ws, start_row: int, rows: List[Dict], fields: Optional[List[str]] = None,
           widths: Optional[Dict[str, int]] = None) -> int:
    if not rows:
        return start_row
    if fields is None:
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
    for j, f in enumerate(fields, start=1):
        _wb_put(ws, start_row, j, f, font=WB_HEAD, fill=WB_HFILL)
    r = start_row + 1
    for row in rows:
        for j, f in enumerate(fields, start=1):
            v = row.get(f)
            if isinstance(v, bool):
                v = "TRUE" if v else "FALSE"
            elif isinstance(v, (list, dict)):
                v = str(v)
            _wb_put(ws, r, j, v)
        r += 1
    for j, f in enumerate(fields, start=1):
        w = (widths or {}).get(f, min(34, max(11, len(str(f)) + 2)))
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = ws.cell(start_row + 1, 1)
    return r


def _wb_kv(ws, start_row: int, pairs: List) -> int:
    _wb_put(ws, start_row, 1, "Metric", font=WB_HEAD, fill=WB_HFILL)
    _wb_put(ws, start_row, 2, "Value", font=WB_HEAD, fill=WB_HFILL)
    _wb_put(ws, start_row, 3, "Basis", font=WB_HEAD, fill=WB_HFILL)
    r = start_row + 1
    for item in pairs:
        label, value = item[0], item[1]
        basis = item[2] if len(item) > 2 else ""
        _wb_put(ws, r, 1, label)
        _wb_put(ws, r, 2, value)
        _wb_put(ws, r, 3, basis, font=WB_NOTE)
        r += 1
    ws.column_dimensions["A"].width = 52
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 62
    return r


def build_workbook(results: Optional[Dict] = None) -> str:
    r = results or integrated_results()
    carbon = r["carbon"]
    ens = r["bounded_sensitivity_ensemble"]
    nexus = r["land_nexus"]
    learn = r["learning_curves"]
    fin = r["finance"]
    energy = r["energy"]
    minerals = r["minerals"]
    biomass = r["biomass"]
    water = r["water"]
    seaweed = r["seaweed"]
    nutrients = r["nutrients"]
    plastics = r["plastics"]
    money = r["monetary_architecture"]["liquidity_stress"]
    clim = r["climate_response"]
    fair = r["fair_form_carbon_crosscheck"]
    grid = r["grid_reliability_stress"]
    coll = r["settlement_collection"]
    pcap = r["programme_capital"]; taud = r["transition_calibration_audit"]
    tmat = r["transition_case_restoration_matrix"]

    wb = openpyxl.Workbook()

    # ---------------------------------------------------------------- Dashboard
    ws = wb.active
    ws.title = "Dashboard"
    _wb_put(ws, 1, 1, "Planetary Restoration — dynamically constrained coupled model", font=WB_TITLE)
    _wb_put(ws, 2, 1, "Generated by build_workbook.py from planetary_restoration_model.integrated_results(). "
                   "Do not edit by hand; rerun the model instead.", font=WB_NOTE)

    pairs = [
        ("Starting CO2 (ppm)", START_CO2_PPM, "NOAA global monthly mean, May 2026"),
        ("Peak CO2 (ppm)", carbon["peak_co2_ppm"], f"Design case, peak year {carbon['peak_year']}"),
        ("Peak year", carbon["peak_year"], ""),
        ("First 280 ppm crossing year — design case", carbon["crossing_year"],
         "Deterministic run with all inputs at their central values"),
        ("Ensemble p05 / p50 / p95 return year",
         f"{ens['return_year_p05']:.0f} / {ens['return_year_p50']:.0f} / {ens['return_year_p95']:.0f}",
         "Conditional on returning within the simulated horizon"),
        ("Ensemble median including censored draws", ens["return_year_p50_all_draws"],
         "Non-returning draws re-included as censored values"),
        ("Draws not restored within horizon", ens["fraction_not_restored_within_horizon"],
         "Upper percentile therefore lies beyond the simulated horizon"),
        ("Design-case percentile rank within its own ensemble", ens["deterministic_central_percentile_rank"],
         "Fraction of draws restoring no later than the design case. A low value means the "
         "headline year sits in the optimistic tail of the model's own sensitivity range."),
        ("--- programme capital ---", "", ""),
        ("Transition investment at maturity (USD tn/yr)", pcap["mature_transition_investment_usd_tn"],
         "From the endogenous capital-turnover emissions module"),
        ("CDR spend at maturity (USD tn/yr)", pcap["mature_cdr_spend_usd_tn"], ""),
        ("Combined programme capital at maturity (USD tn/yr)", pcap["mature_combined_usd_tn"], ""),
        ("Combined as share of GDP screen", pcap["mature_combined_fraction_gdp"],
         "Against a 2.14% settlement envelope. The two capital streams were previously never added."),
        ("Peak combined share of GDP", pcap["peak_combined_fraction_gdp"],
         f"Peak year {pcap['peak_combined_year']}"),
        ("Years gross combined requirement exceeds the envelope", len(pcap["gross_envelope_breach_years"]), ""),
        ("Years the public share exceeds the envelope", len(pcap["public_envelope_breach_years"]),
         f"At an assumed {pcap['inputs']['transition_public_share']*100:.0f}% public share of transition capital"),
        ("--- transition calibration ---", "", ""),
        ("Post-2035 acceleration multiplier (fitted)", taud["post_2035_acceleration_multiplier"],
         "Fitted so total CO2 reaches the residual floor in 2050"),
        ("Residual-floor year with the fitted acceleration", taud["residual_floor_year_with_fitted_acceleration"], ""),
        ("Residual-floor year without it", taud["residual_floor_year_without_fitted_acceleration"],
         "Same capital-turnover physics and investment envelope, no fitted step change"),
        ("280 ppm without the fitted acceleration",
         taud["restoration_without_fitted_acceleration"]["crossing_year"],
         "The restoration date is far less sensitive to this than the net-zero date is"),
        ("--- warming ---", "", ""),
        ("Present-day warming, model spin-up (C)", clim["central"]["start_warming_c"],
         "Spun up from 1850; validated against assessed warming, not tuned to it"),
        ("Peak warming (C)", clim["central"]["peak_warming_c"],
         f"Design case, peak year {clim['central']['peak_warming_year']}"),
        ("Years above 1.5 C", clim["central"]["years_above_1p5"], ""),
        ("Years above 2.0 C", clim["central"]["years_above_2p0"], ""),
        ("Year falling back below 1.5 C", clim["central"]["year_falling_below_1p5"] or "n/a", ""),
        ("Warming remaining when CO2 reaches 280 ppm (C)", clim["central"]["warming_at_co2_target_c"],
         "Deep-ocean heat and residual non-CO2 forcing persist. CO2 restoration is not "
         "climate restoration."),
        ("Deep-ocean warming at end of run (C)", clim["central"]["final_deep_ocean_warming_c"],
         "Centuries-long thermosteric sea-level commitment; not reversed on this timescale"),
        ("Equilibrium climate sensitivity (C)", clim["central"]["equilibrium_climate_sensitivity_c"], ""),
        ("Transient climate response (C)", clim["central"]["transient_climate_response_c"], ""),
        ("--- structural cross-checks ---", "", ""),
        ("FaIR-form 280 ppm crossing, endogenous temperature", fair["endogenous_temperature_crossing_year"],
         "Independent state-dependent gas cycle against the Joos impulse response"),
        ("FaIR-form vs Joos crossing difference (years)",
         (fair["endogenous_temperature_crossing_year"] - carbon["crossing_year"])
         if fair["endogenous_temperature_crossing_year"] and carbon["crossing_year"] else "n/a",
         "Small difference means carbon-cycle structure is not what drives the date"),
        ("8760-hour adequacy failures", ", ".join(grid["failed_cases"]) or "none",
         "Annual TWh balances hide these"),
        ("Settlement collection failures", ", ".join(coll["maturity_stress"]["failed_cases"]) or "none", ""),
        ("--- carbon and deployment ---", "", ""),
        ("Steady-state maintenance CDR at 280 ppm (GtCO2/yr)",
         carbon["steady_state_maintenance_cdr_gtco2_yr"],
         "Removal needed to hold the target after crossing, against "
         f"{r['scenario']['residual_emissions_gtco2']} GtCO2/yr residual emissions. The excess is "
         "reservoir rebound: restoration is a permanent obligation, not an endpoint."),
        ("Target held through maintenance window", "YES" if carbon["target_held"] else "NO", ""),
        ("Mature feasible CDR (GtCO2/yr)", r["cdr_portfolio"]["cdr_gtco2_yr"], "After land and blue-water constraints"),
        ("Cumulative CDR to target (GtCO2)", carbon["cumulative_incremental_cdr_to_target_gtco2"], ""),
        ("CDR land demand (Mha)", nexus["realized_cdr_land_mha"], ""),
        ("Remaining agricultural land at maturity (Mha)", nexus["food"]["remaining_agricultural_land_mha"], ""),
        ("Enhanced-weathering spreading area (Mha)", nexus["ew_spreading_area_mha"],
         "Basalt application on existing cropland"),
        ("Enhanced weathering as share of food cropland", nexus["ew_share_of_food_cropland_fraction"],
         "Co-use, not land conversion; not captured by the residual-land test"),
        ("Enhanced weathering, adoptable-area utilization", nexus["ew_adoptable_area_utilization_fraction"],
         "Near-binding: a modest reduction in adoptable share makes this the limiting constraint"),
        ("Managed CDR blue-water use (km3/yr)", nexus["realized_incremental_blue_water_km3_yr"], ""),
        ("Managed CDR blue-water stress anchor (km3/yr)", nexus["incremental_blue_water_screen_km3_yr"],
         "Literature-informed stress anchor, not a freshwater allocation"),
        ("Restoration ET-change diagnostic (km3/yr)", nexus["restoration_et_increment_diagnostic_km3_yr"],
         "Diagnostic only; not a blue-water withdrawal"),
        ("Boreal albedo-only stress diagnostic (global W/m2)",
         nexus["uncompensated_boreal_albedo_only_global_forcing_w_m2"],
         "Uncompensated albedo-only; not the net biophysical forcing"),
        ("Learning + scarcity blended CDR cost (USD/t)", learn["maturity_blended_cost_usd_t"], ""),
        ("Learning + scarcity CDR spend (USD tn/yr)", learn["maturity_spend_usd_tn"], ""),
        ("Learning-only, no scarcity (USD tn/yr)", learn["maturity_learning_only_no_scarcity_spend_usd_tn"], ""),
        ("Flat $185/t counterfactual (USD tn/yr)", learn["maturity_flat_185_counterfactual_usd_tn"],
         "The flat screen is optimistic in this model, not conservative"),
        ("Dynamic CDR burden of mature GDP", fin["central_burden_fraction_gdp"], ""),
        ("Settlement envelope (share of GDP)", fin["settlement_envelope_fraction_gdp"],
         "Policy cap, not a demonstrated collection mechanism"),
        ("Headroom after CDR (USD tn/yr)", fin["headroom_after_dynamic_cdr_usd_tn_yr"], ""),
        ("CDR direct electricity (TWh/yr)", energy["cdr_direct_electricity_twh_yr"], ""),
        ("CDR low-grade process heat (TWhth/yr)", energy["cdr_low_grade_heat_twhth_yr"],
         "Reported separately from electricity; low-carbon heat supply is unsolved"),
        ("Core transformed electricity (TWh/yr)", energy["core_transformed_electricity_twh_yr"],
         "Excludes the desalination contingency"),
        ("Desalination backstop (TWh/yr)", energy["desalination_backstop_twh_yr"],
         "Excluded from the core total unless dispatched"),
        ("Full-backstop transformed electricity (TWh/yr)",
         energy["full_desalination_backstop_transformed_electricity_twh_yr"], ""),
        ("Central mineral/feedstock throughput (Gt/yr)", minerals["total_central_gt_yr"], ""),
        ("Central dry land-biomass requirement (Gt/yr)", biomass["land_biomass_total_gt_yr"], ""),
        ("Marine polymer share of storm-structure demand",
         plastics["marine_share_of_demand_with_prevention"], "With source prevention"),
        ("Phosphorus coverage, worst pairing", nutrients["full_factorial_min_coverage"],
         "Full factorial, not paired low-with-low"),
        ("Failed monetary stress cases", ", ".join(money["failed_cases"]) or "none", ""),
        ("Carbon-credit sales required (USD tn/yr)", fin["carbon_credit_sales_required_usd_tn_yr"], ""),
    ]
    _wb_kv(ws, 4, pairs)

    # ---------------------------------------------------------------- sheets
    sheets = [
        ("Scenario_Summary", r["scenario_summary"], None),
        ("Carbon_Cycle", carbon["rows"], None),
        ("CDR_Portfolio", r["cdr_portfolio"]["rows"], None),
        ("Biogeophysical_Nexus", r["land_stress_matrix"], None),
        ("Learning_Scarcity_Finance", _flatten_learning_rows(learn["rows"]), None),
        ("Pathway_Economics", _flatten_pathway_economics(learn["rows"]), None),
        ("Monetary_Liquidity", money["rows"], None),
        ("Collection_Stress", fin["collection_stress"], None),
        ("Banking_Opportunity", r["banking_transition"]["scenarios"], None),
        ("External_Screens", r["external_social_ecological_screens"], None),
        ("Climate_Response", clim["central_rows"], None),
        ("Climate_Sensitivity", clim["sensitivity_cases"], None),
        ("Climate_Validation", [{"check": k, "value": v} for k, v in clim["validation"].items()], None),
        ("FaIR_Crosscheck", fair["central_rows"], None),
        ("FaIR_Cases", [{k: v for k, v in c.items() if k != "params"} for c in fair["cases"]], None),
        ("Grid_Reliability", grid["rows"], None),
        ("Grid_Adequacy_Frontier", grid["adequacy_frontier_rows"], None),
        ("Settlement_Collection", coll["maturity_stress"]["rows"], None),
        ("Settlement_Feedback", coll["funding_feedback"]["cases"], None),
        ("Programme_Capital", pcap["rows"], None),
        ("Transition_Cases", tmat, None),
    ]
    for name, rows, fields in sheets:
        s = wb.create_sheet(name)
        _wb_table(s, 1, rows, fields)

    # Energy / materials
    s = wb.create_sheet("Energy_Materials")
    _wb_put(s, 1, 1, "Energy and material throughput", font=WB_TITLE)
    rows = [(k, v, "") for k, v in energy.items() if isinstance(v, (int, float))]
    rows += [("--- minerals ---", "", "")]
    rows += [(k, v, minerals.get("constraint", "")) if k == "total_central_gt_yr" else (k, v, "")
             for k, v in minerals.items() if isinstance(v, (int, float))]
    rows += [("--- biomass ---", "", "")]
    rows += [(k, v, "") for k, v in biomass.items() if isinstance(v, (int, float))]
    n = _wb_kv(s, 2, rows)
    _wb_put(s, n + 1, 1, minerals["constraint"], font=WB_NOTE)
    _wb_put(s, n + 2, 1, biomass["constraint"], font=WB_NOTE)
    _wb_put(s, n + 3, 1, energy["reliability_status"], font=WB_NOTE)

    # Water / nutrients / plastics
    s = wb.create_sheet("Water_Nutrients_Plastics")
    _wb_put(s, 1, 1, "Water, nutrient and plastic mass balances", font=WB_TITLE)
    rows = [(f"water: {k}", v, "") for k, v in water.items() if isinstance(v, (int, float))]
    rows += [(f"seaweed: {k}", v, "") for k, v in seaweed.items() if isinstance(v, (int, float))]
    rows += [(f"phosphorus: {k}", v, "") for k, v in nutrients.items() if isinstance(v, (int, float))]
    rows += [(f"plastics: {k}", v, "") for k, v in plastics.items() if isinstance(v, (int, float))]
    n = _wb_kv(s, 2, rows)
    _wb_put(s, n + 1, 1, seaweed["constraint"], font=WB_NOTE)

    # Sources
    s = wb.create_sheet("Sources")
    _wb_table(s, 1, [{"key": k, "url": v} for k, v in sorted(r["sources"].items())],
           ["key", "url"], {"key": 26, "url": 110})

    # Limitations
    s = wb.create_sheet("Limitations")
    _wb_put(s, 1, 1, "Publication boundaries", font=WB_TITLE)
    lim = [
        {"Area": "Carbon", "Model treatment": carbon["model_class"], "Status": "SCREEN",
         "Publication boundary": carbon["publication_boundary"]},
        {"Area": "Temperature", "Model treatment": "Two-layer energy balance spun up from 1850",
         "Status": "EMULATOR",
         "Publication boundary": clim["boundary"]},
        {"Area": "Emissions transition", "Model treatment": "Prescribed linear decline to a residual level",
         "Status": "SCENARIO",
         "Publication boundary": "Not derived from an energy-system or policy model. The design case assumes "
                                 "the fastest transition in the sampled range; the ensemble median is materially later."},
        {"Area": "Land/water", "Model treatment": "Food-first land plus managed blue-water screen", "Status": "SCREEN",
         "Publication boundary": "Requires gridded basin and land-suitability optimization."},
        {"Area": "Biogeophysics", "Model treatment": "ET and boreal albedo stress diagnostics", "Status": "DIAGNOSTIC",
         "Publication boundary": "Not converted to CO2-equivalent credit or penalty."},
        {"Area": "CDR economics", "Model treatment": "Pathway learning plus physical scarcity", "Status": "SENSITIVITY",
         "Publication boundary": "Non-DAC parameters are scenario assumptions, not estimated supply curves."},
        {"Area": "Settlement finance", "Model treatment": "Spend against a policy envelope plus collection stress",
         "Status": "SCREEN",
         "Publication boundary": "The envelope is a cap. No model of transaction volume, incidence, elasticity or "
                                 "collection demonstrates that the revenue can actually be raised."},
        {"Area": "Monetary", "Model treatment": "Liquid/illiquid reserve redemption stress", "Status": "STRESS TEST",
         "Publication boundary": "Does not prove purchasing-power stability, convertibility or legal adoption."},
        {"Area": "Power", "Model treatment": "Annual TWh accounting", "Status": "SCREEN",
         "Publication boundary": "No regional 8760-hour reliability solve; no capacity requirement is inferred."},
        {"Area": "Social/ecological headlines", "Model treatment": "External screens, isolated and labelled",
         "Status": "EXTERNAL", "Publication boundary": "Not produced by any submodel in this package."},
    ]
    _wb_table(s, 2, lim, ["Area", "Model treatment", "Status", "Publication boundary"],
           {"Area": 24, "Model treatment": 46, "Status": 14, "Publication boundary": 78})

    wb.save(WB_OUT)
    return WB_OUT


def build_headline_markdown(results: Optional[Dict] = None) -> str:
    """Regenerate data/HEADLINE_RESULTS.md from the model.

    Every headline number quoted anywhere in this project should be copied from
    this file. It is rewritten on every run, so a document that disagrees with it
    is stale by definition. This is the mechanism that stops the spreadsheet, the
    figures and the manuscript from drifting apart again.
    """
    r = results or integrated_results()
    c = r["carbon"]; ens = r["bounded_sensitivity_ensemble"]; n = r["land_nexus"]
    lc = r["learning_curves"]; fin = r["finance"]; e = r["energy"]
    mi = r["minerals"]; bi = r["biomass"]; pl = r["plastics"]; nu = r["nutrients"]
    sw = r["seaweed"]; mo = r["monetary_architecture"]["liquidity_stress"]
    clim = r["climate_response"]; fair = r["fair_form_carbon_crosscheck"]
    grid = r["grid_reliability_stress"]; coll = r["settlement_collection"]
    pcap = r["programme_capital"]; taud = r["transition_calibration_audit"]
    tmat = r["transition_case_restoration_matrix"]
    s = r["scenario"]

    L = []
    A = L.append
    A("# Headline results — generated file, do not edit")
    A("")
    A("Regenerated by `build_workbook.py` from `planetary_restoration_model.integrated_results()`.")
    A("Any number quoted in the README, the manuscript, a figure caption or an outreach")
    A("document must match this file. If it does not, the document is stale.")
    A("")
    A(f"Design scenario: **{s['name']}**, land case **{r['land_case']}**.")
    A("")
    A("## Atmosphere")
    A("")
    A(f"- Starting CO2: **{START_CO2_PPM} ppm** (NOAA global monthly mean, May 2026).")
    A(f"- Peak CO2: **{c['peak_co2_ppm']:.2f} ppm in {c['peak_year']}**.")
    A(f"- Design-case first return to 280 ppm: **{c['crossing_year']}**.")
    A(f"- Cumulative incremental CDR to target: **{c['cumulative_incremental_cdr_to_target_gtco2']:,.0f} GtCO2**.")
    A(f"- Sensitivity ensemble, conditional on returning within the horizon: "
      f"p05 **{ens['return_year_p05']:.0f}**, p50 **{ens['return_year_p50']:.0f}**, p95 **{ens['return_year_p95']:.0f}**.")
    A(f"- Median including censored draws: **{ens['return_year_p50_all_draws']:.0f}**. "
      f"**{ens['fraction_not_restored_within_horizon']*100:.1f}%** of draws do not return to 280 ppm within the "
      f"simulated horizon, so the 95th percentile over all draws lies beyond it.")
    A(f"- The design case sits at the **{ens['deterministic_central_percentile_rank']*100:.1f}th percentile** of its own "
      f"ensemble: only that share of draws restore as early or earlier. The design case is a best-corner "
      f"combination of central inputs, not a central outcome. The ensemble median is the defensible headline.")
    A(f"- Holding 280 ppm requires **{c['steady_state_maintenance_cdr_gtco2_yr']:.2f} GtCO2/yr** of continuing removal "
      f"against **{s['residual_emissions_gtco2']} GtCO2/yr** of residual emissions. The difference is reservoir "
      f"rebound. Restoration is a permanent obligation, not an endpoint.")
    A(f"- Target held through the maintenance window: **{'yes' if c['target_held'] else 'no'}**.")
    A("")
    A("## Scenarios")
    A("")
    A("| Scenario | Land case | Peak CO2 (ppm) | 280 ppm | Cumulative CDR (GtCO2) | Peak warming (C) | Yr >1.5 C |")
    A("|---|---|---|---|---|---|---|")
    for row in r["scenario_summary"]:
        A(f"| {row['scenario']} | {row['land_case']} | {row['peak_co2_ppm']:.1f} | "
          f"{row['return_280_year']} | {row.get('cumulative_cdr_to_target_gtco2', float('nan')):,.0f} | "
          f"{row.get('peak_warming_c', float('nan')):.2f} | {row.get('years_above_1p5c', 0)} |")
    A("")
    A("## Programme capital")
    A("")
    A(f"- At maturity the emissions transition needs **US${pcap['mature_transition_investment_usd_tn']:.2f} tn/yr** of "
      f"clean-capital investment and the removal programme **US${pcap['mature_cdr_spend_usd_tn']:.2f} tn/yr**: a combined "
      f"**US${pcap['mature_combined_usd_tn']:.2f} tn/yr**, or **{pcap['mature_combined_fraction_gdp']*100:.2f}%** of the "
      f"mature-GDP screen. Cumulative transition capital to 2050 is "
      f"**US${pcap['cumulative_transition_capital_to_2050_usd_tn']:.0f} tn**.")
    A(f"- The removal bill alone sits inside the 2.14% settlement envelope. **The gross combined requirement does "
      f"not**, exceeding it in {len(pcap['gross_envelope_breach_years'])} modelled years and peaking at "
      f"**{pcap['peak_combined_fraction_gdp']*100:.2f}%** of GDP in {pcap['peak_combined_year']}. At the assumed "
      f"{pcap['inputs']['transition_public_share']*100:.0f}% public share of transition capital the publicly funded "
      f"subset stays inside the envelope; above roughly a 55% public share it does not.")
    A("- Most clean-energy investment is private and partly displaces fossil capital that would have been spent "
      "anyway, so the gross figure is not a fiscal requirement. The point is narrower and still binding: any claim "
      "that the settlement mechanism funds the programme must say which of the two capital streams it funds.")
    A("")
    A("## What the reference emissions trajectory assumes")
    A("")
    A(f"- {taud['finding']}")
    A("")
    A("| Transition case | Residual floor | 280 ppm | Peak CO2 | Peak warming | Yr >1.5 C | Capital to 2050 |")
    A("|---|---|---|---|---|---|---|")
    for row in tmat:
        A(f"| {row['case']} | {row['residual_floor_year']} | {row['return_280_year']} | "
          f"{row['peak_co2_ppm']:.1f} ppm | {row['peak_warming_c']:.2f} C | {row['years_above_1p5c']} | "
          f"US${row['cumulative_transition_capital_to_2050_usd_tn']:.0f} tn |")
    A("")
    A("## Warming")
    A("")
    A(f"- Present-day warming from the 1850 spin-up: **{clim['central']['start_warming_c']:.2f} C**. "
      f"The module is validated against assessed warming rather than tuned to it: it produces "
      f"**{clim['validation']['warming_2024_c']:.2f} C** for 2024 against an assessed "
      f"**{clim['validation']['warming_2024_reference_c']:.2f} C**, with ECS "
      f"**{clim['validation']['equilibrium_climate_sensitivity_c']:.2f} C** and TCR "
      f"**{clim['validation']['transient_climate_response_c']:.2f} C**.")
    A(f"- Peak warming: **{clim['central']['peak_warming_c']:.2f} C in {clim['central']['peak_warming_year']}**.")
    A(f"- **{clim['central']['years_above_1p5']} years above 1.5 C** and "
      f"**{clim['central']['years_above_2p0']} above 2.0 C**"
      + (f", falling back below 1.5 C in **{clim['central']['year_falling_below_1p5']}**."
         if clim['central']['year_falling_below_1p5'] else "."))
    A(f"- Warming still present when CO2 reaches 280 ppm: **{clim['central']['warming_at_co2_target_c']:.2f} C**, "
      f"with the deep ocean at **{clim['central']['final_deep_ocean_warming_c']:.2f} C**. "
      f"Returning CO2 to pre-industrial does not return the climate system to a pre-industrial "
      f"state, and the sea-level commitment does not reverse on this timescale.")
    A("- Across the AR6 sensitivity range: " + "; ".join(
        f"{c['params']['name']} peak **{c['peak_warming_c']:.2f} C**, "
        f"{c['years_above_2p0']} yr above 2.0 C" for c in clim["sensitivity_cases"]) + ".")
    A("")
    A("## Structural cross-checks")
    A("")
    A(f"- An independent FaIR-v2-form state-dependent gas cycle returns 280 ppm in "
      f"**{fair['endogenous_temperature_crossing_year']}** against **{c['crossing_year']}** from the Joos "
      f"impulse response, a **{abs((fair['endogenous_temperature_crossing_year'] or 0)-(c['crossing_year'] or 0))}-year** "
      f"difference. Its own prior ensemble spans "
      f"**{fair['ensemble']['crossing_year_p05']:.0f}-{fair['ensemble']['crossing_year_p95']:.0f}** while peak CO2 "
      f"spans **{fair['ensemble']['peak_co2_ppm_p05']:.0f}-{fair['ensemble']['peak_co2_ppm_p95']:.0f} ppm**. "
      f"Carbon-cycle parameter uncertainty therefore moves the concentration level a great deal and the "
      f"restoration date very little: **the date is governed by the emissions and deployment trajectory, "
      f"not by carbon-cycle structure**.")
    A(f"- 8760-hour adequacy failures: **{', '.join(grid['failed_cases']) or 'none'}**. Annual TWh balances "
      f"cannot see these.")
    A(f"- Settlement collection failures: **{', '.join(coll['maturity_stress']['failed_cases']) or 'none'}**.")
    A("")
    A("## Land, water and biogeophysics")
    A("")
    A(f"- Mature land/blue-water-feasible CDR: **{r['cdr_portfolio']['cdr_gtco2_yr']:.2f} GtCO2/yr**.")
    A(f"- CDR land demand: **{n['realized_cdr_land_mha']:.1f} Mha** against **"
      f"{n['food']['remaining_agricultural_land_mha']:.1f} Mha** of residual agricultural land.")
    A(f"- Enhanced-weathering spreading area: **{n['ew_spreading_area_mha']:.1f} Mha**, "
      f"**{n['ew_share_of_food_cropland_fraction']*100:.1f}%** of modeled food cropland and "
      f"**{n['ew_adoptable_area_utilization_fraction']*100:.1f}%** of the adoptable envelope. This is co-use "
      f"of existing cropland, so it does not appear in the residual-land test, and it is the closest "
      f"non-binding constraint in the central case.")
    A(f"- Managed incremental CDR blue water: **{n['realized_incremental_blue_water_km3_yr']:.1f} km3/yr** against a "
      f"**{n['incremental_blue_water_screen_km3_yr']:.0f} km3/yr** literature-informed stress anchor.")
    A(f"- Screened food irrigation withdrawal: **{n['food']['screened_food_irrigation_withdrawal_km3_yr']:,.0f} km3/yr** "
      f"(global aggregate, not a basin feasibility result).")
    A(f"- Restoration ET-change diagnostic: **{n['restoration_et_increment_diagnostic_km3_yr']:.0f} km3/yr**. "
      f"Diagnostic only; not treated as a withdrawal.")
    A(f"- Uncompensated boreal albedo-only stress diagnostic: **{n['uncompensated_boreal_albedo_only_global_forcing_w_m2']:.4f} W/m2** "
      f"global mean. Not the net biophysical forcing; not converted to CO2-equivalent.")
    A("")
    A("## Energy and materials")
    A("")
    A(f"- CDR direct electricity: **{e['cdr_direct_electricity_twh_yr']:,.1f} TWh/yr**.")
    A(f"- CDR low-grade process heat: **{e['cdr_low_grade_heat_twhth_yr']:,.0f} TWhth/yr**, reported separately. "
      f"Low-carbon supply of heat at this scale is unsolved.")
    A(f"- Core transformed electricity: **{e['core_transformed_electricity_twh_yr']:,.1f} TWh/yr** "
      f"(desalination contingency not dispatched).")
    A(f"- Full desalination-backstop case: **{e['full_desalination_backstop_transformed_electricity_twh_yr']:,.1f} TWh/yr**.")
    A(f"- Mineral/feedstock throughput: **{mi['total_central_gt_yr']:.2f} Gt/yr** central, "
      f"**{mi['total_low_gt_yr']:.2f}–{mi['total_high_gt_yr']:.2f} Gt/yr** screening range.")
    A(f"- Dry land biomass: **{bi['land_biomass_total_gt_yr']:.2f} Gt/yr**, about "
      f"**{bi['land_biomass_energy_equivalent_ej_yr']:.0f} EJ/yr** equivalent.")
    A("")
    A("## Mass balances")
    A("")
    A(f"- Seaweed: area-yield potential **{sw['area_yield_potential_gt_dry_yr']:.3f} Gt dry/yr** would require "
      f"**{sw['n_required_for_full_potential_mt_yr']:.1f} Mt N/yr**, but credited eutrophic capture is only "
      f"**{sw['credited_eutrophic_n_mt_yr']:.2f} Mt N/yr**, which supports "
      f"**{sw['nutrient_supported_biomass_without_other_sources_gt_yr']:.3f} Gt dry/yr**. The remainder requires a "
      f"separately demonstrated natural or managed nutrient flux.")
    A(f"- Phosphorus coverage across the full factorial: **{nu['full_factorial_min_coverage']:.3f}** to "
      f"**{nu['full_factorial_max_coverage']:.3f}**, central **{nu['central_coverage']:.3f}**. The adverse pairing "
      f"leaves **{nu['worst_case_primary_p_requirement_mt_yr']:.2f} Mt P/yr** still requiring mined rock, so "
      f"zero-mining is a conditional result, not a range-wide one.")
    A(f"- Plastics: **{pl['legacy_removed_mt']:.2f} Mt** legacy removed plus **{pl['intercepted_new_with_prevention_mt']:.2f} Mt** "
      f"intercepted gives **{pl['qualified_marine_polymer_with_prevention_mt']:.2f} Mt** qualified polymer against "
      f"**{pl['storm_structure_polymer_demand_mt']:.2f} Mt** of structural demand, a "
      f"**{pl['marine_share_of_demand_with_prevention']*100:.1f}%** marine share. Net floating-stock reduction is "
      f"**{pl['net_buoyant_stock_reduction_with_prevention_fraction']*100:.1f}%**.")
    A("")
    A("## Economics and finance")
    A("")
    A(f"- Blended CDR cost at maturity: **${lc['maturity_blended_cost_usd_t']:.1f}/tCO2**.")
    A(f"- CDR spend at maturity: **${lc['maturity_spend_usd_tn']:.3f} tn/yr** with learning and scarcity, "
      f"**${lc['maturity_learning_only_no_scarcity_spend_usd_tn']:.3f} tn/yr** without scarcity, "
      f"**${lc['maturity_flat_185_counterfactual_usd_tn']:.3f} tn/yr** under the flat $185/t screen. "
      f"The flat screen is therefore optimistic in this model, not conservative.")
    A(f"- Burden: **{fin['central_burden_fraction_gdp']*100:.2f}%** of the mature-GDP screen against a "
      f"**{fin['settlement_envelope_fraction_gdp']*100:.2f}%** settlement envelope; headroom "
      f"**${fin['headroom_after_dynamic_cdr_usd_tn_yr']:.2f} tn/yr**. The envelope is a policy cap. No model here "
      f"demonstrates that a settlement network can actually collect it; see the Collection_Stress sheet.")
    A(f"- Carbon-credit sales required: **${fin['carbon_credit_sales_required_usd_tn_yr']:.0f}**.")
    A(f"- Timber-reference reserve stress failures: **{', '.join(mo['failed_cases']) or 'none'}**. "
      f"The monetary architecture is not presented as demonstrated.")
    A("")

    path = os.path.join(WB_HERE, "data", "HEADLINE_RESULTS.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return path


# ==============================================================================================
# SECTION 16 Command line
# ==============================================================================================
def print_summary(r: Dict) -> None:
    c = r["carbon"]; ens = r["bounded_sensitivity_ensemble"]
    n = r["land_nexus"]; l = r["learning_curves"]; cl = r["climate_response"]["central"]
    pc = r["programme_capital"]; ta = r["transition_calibration_audit"]
    print(f"Peak CO2: {c['peak_co2_ppm']:.2f} ppm in {c['peak_year']}")
    print("280 ppm crossing (design case):", c["crossing_year"])
    print(f"Ensemble p05/p50/p95: {ens['return_year_p05']:.0f} {ens['return_year_p50']:.0f} {ens['return_year_p95']:.0f}"
          f"  (design case at p{ens['deterministic_central_percentile_rank']*100:.0f} of its own ensemble)")
    print(f"Peak warming: {cl['peak_warming_c']:.2f} C in {cl['peak_warming_year']}; "
          f"{cl['years_above_1p5']} yr above 1.5 C; warming at 280 ppm {cl['warming_at_co2_target_c']:.2f} C")
    print(f"Maintenance CDR to hold 280 ppm: {c['steady_state_maintenance_cdr_gtco2_yr']:.2f} GtCO2/yr")
    print(f"Mature feasible CDR: {r['cdr_portfolio']['cdr_gtco2_yr']:.3f} GtCO2/yr; "
          f"land {n['realized_cdr_land_mha']:.1f} Mha, binding={n['binding']}")
    print(f"Maturity blended CDR cost ${l['maturity_blended_cost_usd_t']:.1f}/t, spend ${l['maturity_spend_usd_tn']:.3f} tn/yr")
    print(f"Transition residual floor: {ta['residual_floor_year_with_fitted_acceleration']} with the fitted "
          f"{ta['post_2035_acceleration_multiplier']:.1f}x post-2035 acceleration, "
          f"{ta['residual_floor_year_without_fitted_acceleration']} without it")
    print(f"Programme capital at maturity: transition ${pc['mature_transition_investment_usd_tn']:.2f} tn + "
          f"CDR ${pc['mature_cdr_spend_usd_tn']:.2f} tn = ${pc['mature_combined_usd_tn']:.2f} tn "
          f"({pc['mature_combined_fraction_gdp']*100:.2f}% of GDP screen vs a 2.14% envelope)")
    print("FaIR-form cross-check 280 ppm:", r["fair_form_carbon_crosscheck"]["cases"][0]["crossing_year"])
    print("8760 adequacy failures:", r["grid_reliability_stress"]["failed_cases"])
    print("Settlement collection failures:", r["settlement_collection"]["maturity_stress"]["failed_cases"])
    print("Monetary reserve failures:", r["monetary_architecture"]["liquidity_stress"]["failed_cases"])


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(
        description="Planetary Restoration Model (single-file build). "
                    "With no arguments: run the model, the tests, the workbook and the figures.")
    ap.add_argument("--model", action="store_true", help="run the model and write data/")
    ap.add_argument("--tests", action="store_true", help="run the test suite only")
    ap.add_argument("--workbook", action="store_true", help="regenerate the workbook and headline file")
    ap.add_argument("--figures", action="store_true", help="regenerate figures (needs matplotlib)")
    a = ap.parse_args(argv)
    steps = [a.model, a.tests, a.workbook, a.figures]
    run_all = not any(steps)

    here = os.path.dirname(os.path.abspath(__file__))
    results = None
    if run_all or a.model:
        results = write_outputs(os.path.join(here, "data"))
        print_summary(results)
    if run_all or a.tests:
        run_tests()
        run_new_section_tests()
        print("PROGRAMME-CAPITAL AND CALIBRATION-AUDIT TESTS PASSED")
    if run_all or a.workbook:
        print("WORKBOOK BUILT:", build_workbook(results))
        print("HEADLINES BUILT:", build_headline_markdown(results))
    if run_all or a.figures:
        try:
            print("FIGURES BUILT:", build_all_figures(results))
        except ImportError:
            print("FIGURES SKIPPED: matplotlib not installed")
    return 0




# ==============================================================================================
# VERSION 51 ADVANCED COUPLED EXTENSION — merged single-file distribution
# ==============================================================================================
import sys as _self_sys
prm = _self_sys.modules[__name__]
_core_write_outputs = write_outputs
_core_run_tests = run_tests
_core_run_new_section_tests = run_new_section_tests
_core_build_all_figures = build_all_figures
_core_integrated_results = integrated_results

"""Advanced coupled extension for the Planetary Restoration Model.

This module deliberately does *not* claim to be a replacement for ICON, E3SM,
CESM, UKESM or another kilometre-scale/full-complexity Earth-system model. It
turns the existing Planetary Restoration Model into a more self-consistent
reduced-complexity screening model by adding state variables that its own
interventions can modify:

* per-pathway stored-carbon stocks, saturation and reversals;
* CH4 and N2O concentration states and fossil-linked aerosol forcing;
* a surface-ocean carbonate/alkalinity state and pH diagnostic that responds to OAE;
* a permafrost-carbon feedback;
* land-carbon saturation and climate-sensitive disturbance through the biological
  restoration stock;
* avoided climate-damage screens against a no-action comparator;
* critical-mineral demand screens; and
* workforce / person-year feasibility screens.

It also provides a state-variable registry and adapter metadata for ICON. Full
ICON source code is intentionally kept as an external dependency. The public
ICON release must retain its upstream LICENSES/ and AUTHORS.TXT files.

All numerical assumptions introduced here are explicit in dataclasses below and
are meant to be replaced by calibrated distributions in a publication model.
"""

import argparse
import csv
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ADVANCED_MODEL_VERSION = "52.0"
ADVANCED_RELEASE_LABEL = "Planetary Restoration Model Version 52 — reconciled coupled screen"


# ======================================================================================
# 1. Explicit assumptions for newly coupled state variables
# ======================================================================================

CH4_PI_PPB = 722.0
CH4_2026_PPB = 1937.59  # NOAA global mean, Apr 2026 snapshot used for initialization
N2O_PI_PPB = 270.0
N2O_2026_PPB = 339.78   # NOAA global mean, Apr 2026 snapshot used for initialization


@dataclass(frozen=True)
class PathwayStorage:
    pathway: str
    annual_reversal_fraction: float
    stock_capacity_gtco2: Optional[float] = None
    climate_sensitive: bool = False
    notes: str = ""


# These are screening assumptions, not claimed observations. The purpose is to stop
# treating every tonne of CDR as perfectly permanent by construction. A user can replace
# any rate with a project-specific MRV/durability distribution.
PATHWAY_STORAGE: Dict[str, PathwayStorage] = {
    "DACCS": PathwayStorage(
        "DACCS", 1.0e-5, None, False,
        "Geological-storage screening rate; replace with reservoir-specific leakage/MRV data."),
    "Enhanced silicate weathering": PathwayStorage(
        "Enhanced silicate weathering", 5.0e-5, None, False,
        "Very durable dissolved/mineral carbon; non-zero rate retained as a conservative screen."),
    "Ocean alkalinity / carbonate weathering": PathwayStorage(
        "Ocean alkalinity / carbonate weathering", 5.0e-5, None, False,
        "Represents loss of retained CDR effectiveness/re-equilibration, not literal tank leakage."),
    "Biochar": PathwayStorage(
        "Biochar", 1.0e-3, 350.0, True,
        "Heterogeneous durability; finite stock screen avoids indefinite linear accumulation."),
    "BiCRS / BECCS / durable biomass storage": PathwayStorage(
        "BiCRS / BECCS / durable biomass storage", 1.0e-4, None, False,
        "Assumes durable geological/engineered storage after biomass conversion."),
    "Biological restoration": PathwayStorage(
        "Biological restoration", 5.0e-3, 250.0, True,
        "Finite ecosystem carbon stock with fire/drought/disturbance reversal risk."),
    "Direct/passive mineral carbonation": PathwayStorage(
        "Direct/passive mineral carbonation", 1.0e-6, None, False,
        "Mineralized carbon treated as effectively permanent at screening timescales."),
}


@dataclass(frozen=True)
class GasCycleAssumptions:
    ch4_lifetime_yr: float = 11.8
    n2o_lifetime_yr: float = 109.0
    # 2026 source attribution indices sum to one. They are *source shares for this
    # reduced model*, not an emissions inventory.
    ch4_livestock_share: float = 0.45
    ch4_fossil_share: float = 0.25
    ch4_other_share: float = 0.30
    n2o_cropland_share: float = 0.70
    n2o_livestock_share: float = 0.10
    n2o_fossil_share: float = 0.05
    n2o_other_share: float = 0.15
    aerosol_2026_w_m2: float = -0.95
    aerosol_fossil_exponent: float = 0.70
    other_ch4_floor_2100: float = 0.70
    other_n2o_floor_2100: float = 0.80
    residual_nonco2_2026_w_m2: float = 0.70
    residual_nonco2_2120_w_m2: float = 0.30


@dataclass(frozen=True)
class OceanCarbonateAssumptions:
    surface_mixed_layer_depth_m: float = 100.0
    ocean_area_m2: float = 3.61e14
    seawater_density_kg_m3: float = 1025.0
    baseline_total_alkalinity_umol_kg: float = 2300.0
    oae_alkalinity_equiv_per_mol_co2: float = 1.20
    oae_surface_retention_yr: float = 20.0
    # The compact equilibrium solver omits full salinity/temperature/speciation
    # detail. Scale its pH anomaly to the assessed ~8.17 -> ~8.05 historical change.
    preindustrial_surface_ph: float = 8.17
    equilibrium_anomaly_scale: float = 0.80


@dataclass(frozen=True)
class PermafrostAssumptions:
    carbon_feedback_pgc_per_c: float = 18.0
    methane_feedback_pgc_equiv_per_c: float = 2.8
    activation_warming_c: float = 1.20
    include_methane_as_co2e_in_carbon_cycle: bool = False


@dataclass(frozen=True)
class DamageAssumptions:
    reference_warming_c: float = 1.20
    central_damage_at_3c_fraction_gdp: float = 0.05
    low_damage_at_3c_fraction_gdp: float = 0.02
    high_damage_at_3c_fraction_gdp: float = 0.15
    real_discount_rate: float = 0.02


@dataclass(frozen=True)
class MineralAssumptions:
    variable_renewables_fraction: float = 0.65
    vre_capacity_factor: float = 0.30
    firm_clean_fraction: float = 0.35
    firm_capacity_factor: float = 0.75
    grid_copper_t_per_mw_avg_load: float = 2.0
    vre_copper_t_per_mw: float = 4.0
    firm_copper_t_per_mw: float = 2.0
    battery_storage_share_of_avg_load: float = 0.20
    battery_storage_hours: float = 8.0
    lithium_kg_per_kwh: float = 0.15
    nickel_battery_share: float = 0.30
    nickel_kg_per_kwh_for_nickel_chemistries: float = 0.40
    vre_steel_t_per_mw: float = 60.0
    firm_steel_t_per_mw: float = 100.0
    grid_steel_t_per_mw_avg_load: float = 10.0


@dataclass(frozen=True)
class WorkforceAssumptions:
    rock_mined_t_per_worker_yr: float = 25_000.0
    rock_spread_ha_per_worker_yr: float = 1_500.0
    biomass_handled_t_per_worker_yr: float = 10_000.0
    engineered_cdr_tco2_per_worker_yr: float = 20_000.0
    ecosystem_restoration_ha_per_worker_yr: float = 200.0
    power_build_mw_per_worker_yr: float = 5.0
    operations_mw_per_worker: float = 100.0


@dataclass(frozen=True)
class SocialDividendAssumptions:
    """Post-restoration policy allocation screen.

    Avoided climate damages are social/economic benefits, not a government cash account.
    Allocable cash is therefore based on potential settlement-policy headroom after the
    280-ppm crossing, less continuing programme cost.
    """
    settlement_envelope_fraction_gdp: float = 0.0214
    housing_fraction: float = 0.25
    job_creation_fraction: float = 0.20
    health_fraction: float = 0.15
    food_security_fraction: float = 0.10
    education_fraction: float = 0.10
    clean_water_sanitation_fraction: float = 0.08
    disaster_resilience_fraction: float = 0.05
    ecosystems_biodiversity_fraction: float = 0.05
    direct_cash_emergency_fraction: float = 0.02

    def allocation_total(self) -> float:
        return (self.housing_fraction + self.job_creation_fraction + self.health_fraction
                + self.food_security_fraction + self.education_fraction
                + self.clean_water_sanitation_fraction + self.disaster_resilience_fraction
                + self.ecosystems_biodiversity_fraction + self.direct_cash_emergency_fraction)


@dataclass(frozen=True)
class AdvancedAssumptions:
    gas: GasCycleAssumptions = GasCycleAssumptions()
    ocean: OceanCarbonateAssumptions = OceanCarbonateAssumptions()
    permafrost: PermafrostAssumptions = PermafrostAssumptions()
    damage: DamageAssumptions = DamageAssumptions()
    minerals: MineralAssumptions = MineralAssumptions()
    workforce: WorkforceAssumptions = WorkforceAssumptions()
    social_dividend: SocialDividendAssumptions = SocialDividendAssumptions()
    coupling_iterations: int = 4
    maintenance_after_target_years: int = 30


# ======================================================================================
# 2. Helpers
# ======================================================================================

def _interp(year: int, anchors: Mapping[int, float]) -> float:
    ys = sorted(anchors)
    if year <= ys[0]:
        return float(anchors[ys[0]])
    if year >= ys[-1]:
        return float(anchors[ys[-1]])
    for a, b in zip(ys, ys[1:]):
        if a <= year <= b:
            f = (year - a) / (b - a)
            return float(anchors[a] + f * (anchors[b] - anchors[a]))
    raise RuntimeError("interpolation failure")


def _temperature_by_year(rows: Sequence[Mapping]) -> Dict[int, float]:
    return {int(r["year"]): float(r["surface_warming_c"]) for r in rows}


def _pathway_plan(year: int, s: prm.Scenario, land_case: str) -> Dict[str, float]:
    p = prm.effective_cdr_path(year, s, land_case)
    return {r["pathway"]: float(r["cdr_gtco2_yr"]) for r in p["rows"]}


def _climate_reversal_multiplier(pathway: str, warming_c: float) -> float:
    cfg = PATHWAY_STORAGE[pathway]
    if not cfg.climate_sensitive:
        return 1.0
    # Smooth, transparent disturbance screen. At 2 C this raises reversal hazards 50%.
    return 1.0 + 0.5 * max(0.0, warming_c - 1.0)


# ======================================================================================
# 3. Durable CDR stocks, saturation, leakage and permafrost feedback
# ======================================================================================

def permafrost_source_from_temperature(
    temp_rows: Sequence[Mapping],
    assumptions: PermafrostAssumptions = PermafrostAssumptions(),
) -> Dict[int, float]:
    """Translate incremental warming above a present-climate activation point into a
    monotonic additional permafrost-carbon source.

    The central sensitivity is the IPCC-assessed 18 PgC per degree C by 2100. We use
    the *increase in attained warming above the activation temperature*, so historical
    permafrost emissions already implicit in the 2026 concentration are not added again.
    """
    source: Dict[int, float] = {}
    if not temp_rows:
        return source
    first_t = float(temp_rows[0]["surface_warming_c"])
    baseline_excess = max(0.0, first_t - assumptions.activation_warming_c)
    max_excess = baseline_excess
    previous_cumulative = (baseline_excess * assumptions.carbon_feedback_pgc_per_c
                           * prm.CO2_GTC_TO_GTCO2)
    if assumptions.include_methane_as_co2e_in_carbon_cycle:
        previous_cumulative += (baseline_excess * assumptions.methane_feedback_pgc_equiv_per_c
                                * prm.CO2_GTC_TO_GTCO2)
    for r in temp_rows:
        year = int(r["year"])
        t = float(r["surface_warming_c"])
        max_excess = max(max_excess, max(0.0, t - assumptions.activation_warming_c))
        cumulative_gtco2 = (max_excess * assumptions.carbon_feedback_pgc_per_c
                             * prm.CO2_GTC_TO_GTCO2)
        if assumptions.include_methane_as_co2e_in_carbon_cycle:
            cumulative_gtco2 += (max_excess * assumptions.methane_feedback_pgc_equiv_per_c
                                  * prm.CO2_GTC_TO_GTCO2)
        annual = max(0.0, cumulative_gtco2 - previous_cumulative)
        source[year] = annual
        previous_cumulative = cumulative_gtco2
    return source


def durable_carbon_cycle(
    s: prm.Scenario,
    land_case: str = "central",
    temperature_driver: Optional[Mapping[int, float]] = None,
    permafrost_source_gtco2: Optional[Mapping[int, float]] = None,
    maintain_after_target_years: int = 30,
) -> Dict:
    """Joos IRF carbon cycle with explicit stored-carbon stocks and reversals."""
    init = prm.initialize_carbon_state(prm.START_CO2_PPM, s.observed_natural_sink_gtc_yr)
    atmospheric_state = list(init["state_gtc"])
    stocks = {p: 0.0 for p in PATHWAY_STORAGE}
    rows: List[Dict] = []
    pathway_rows: List[Dict] = []
    peak_ppm, peak_year = prm.START_CO2_PPM, prm.START_YEAR
    crossing_year: Optional[int] = None
    maintenance_years = 0
    cumulative_cdr_to_target = 0.0
    cumulative_reversal_to_target = 0.0
    cumulative_permafrost_to_target = 0.0
    shortfalls: List[int] = []

    temperature_driver = temperature_driver or {}
    permafrost_source_gtco2 = permafrost_source_gtco2 or {}

    for year in range(prm.START_YEAR, s.end_year + 1):
        warming = float(temperature_driver.get(year, temperature_driver.get(year - 1, 1.37)))
        emissions = float(prm.gross_emissions_path(year, s))
        permafrost = float(permafrost_source_gtco2.get(year, 0.0))
        plan = prm.effective_cdr_path(year, s, land_case)
        feasible_map = {r["pathway"]: float(r["cdr_gtco2_yr"]) for r in plan["rows"]}
        feasible_total = sum(feasible_map.values())

        # Existing stock can reverse before the year's new storage is added.
        reversals: Dict[str, float] = {}
        stock_after_reversal: Dict[str, float] = {}
        for pathway, stock in stocks.items():
            cfg = PATHWAY_STORAGE[pathway]
            rate = cfg.annual_reversal_fraction * _climate_reversal_multiplier(pathway, warming)
            reversal = min(stock, max(0.0, stock * rate))
            reversals[pathway] = reversal
            stock_after_reversal[pathway] = stock - reversal
        reversal_total = sum(reversals.values())

        phase = "drawdown" if crossing_year is None else "target_maintenance"
        if crossing_year is None:
            requested_total = feasible_total
        else:
            net_required = prm._required_net_flux_for_target(atmospheric_state, prm.TARGET_CO2_PPM)
            requested_total = max(0.0, emissions + permafrost + reversal_total - net_required)

        scale = min(1.0, requested_total / feasible_total) if feasible_total > 0 else 0.0
        proposed = {p: feasible_map.get(p, 0.0) * scale for p in PATHWAY_STORAGE}

        # Apply pathway stock capacities. This is the crucial difference between a
        # one-off durability discount and a dynamic stock with saturation.
        actual: Dict[str, float] = {}
        saturation_shortfall = 0.0
        for pathway, amount in proposed.items():
            cfg = PATHWAY_STORAGE[pathway]
            if cfg.stock_capacity_gtco2 is None:
                accepted = amount
            else:
                remaining = max(0.0, cfg.stock_capacity_gtco2 - stock_after_reversal[pathway])
                accepted = min(amount, remaining)
            actual[pathway] = accepted
            saturation_shortfall += max(0.0, amount - accepted)
            stocks[pathway] = stock_after_reversal[pathway] + accepted

        actual_cdr = sum(actual.values())
        if crossing_year is not None:
            maintenance_years += 1
            if actual_cdr + 1e-9 < requested_total:
                shortfalls.append(year)

        # Reversal and permafrost emissions are explicit additions to the atmospheric flux.
        net_anthropogenic = emissions + permafrost + reversal_total - actual_cdr
        atmospheric_state, natural_sink = prm._advance_reservoirs(atmospheric_state, net_anthropogenic)
        co2 = prm.PREINDUSTRIAL_CO2_PPM + sum(atmospheric_state) / prm.CO2_MASS_GTC_PER_PPM

        if crossing_year is None:
            cumulative_cdr_to_target += actual_cdr
            cumulative_reversal_to_target += reversal_total
            cumulative_permafrost_to_target += permafrost
        if co2 > peak_ppm:
            peak_ppm, peak_year = co2, year
        if crossing_year is None and co2 <= prm.TARGET_CO2_PPM:
            crossing_year = year

        rows.append({
            "year": year,
            "phase": phase,
            "gross_emissions_gtco2": emissions,
            "permafrost_source_gtco2": permafrost,
            "stored_carbon_reversal_gtco2": reversal_total,
            "planned_incremental_cdr_gtco2": float(plan["planned_cdr_gtco2_yr"]),
            "feasible_incremental_cdr_gtco2": feasible_total,
            "requested_incremental_cdr_gtco2": requested_total,
            "actual_incremental_cdr_gtco2": actual_cdr,
            "saturation_shortfall_gtco2": saturation_shortfall,
            "net_anthropogenic_gtco2": net_anthropogenic,
            "natural_reservoir_flux_to_sinks_gtc": natural_sink,
            "co2_ppm": co2,
            "total_stored_carbon_stock_gtco2": sum(stocks.values()),
            "biological_restoration_stock_gtco2": stocks["Biological restoration"],
            "biochar_stock_gtco2": stocks["Biochar"],
            "land_binding": bool(plan["land_nexus"]["binding"]),
            "surface_warming_driver_c": warming,
        })
        for pathway in PATHWAY_STORAGE:
            pathway_rows.append({
                "year": year,
                "pathway": pathway,
                "new_storage_gtco2": actual[pathway],
                "reversal_gtco2": reversals[pathway],
                "stock_gtco2": stocks[pathway],
                "annual_reversal_fraction": PATHWAY_STORAGE[pathway].annual_reversal_fraction,
                "climate_reversal_multiplier": _climate_reversal_multiplier(pathway, warming),
                "stock_capacity_gtco2": PATHWAY_STORAGE[pathway].stock_capacity_gtco2,
            })

        if crossing_year is not None and maintenance_years >= maintain_after_target_years:
            break

    return {
        "model_class": "Joos four-reservoir carbon cycle + pathway storage stocks + reversals + saturation + permafrost source",
        "scenario": asdict(s),
        "land_case": land_case,
        "initialization": init,
        "peak_co2_ppm": peak_ppm,
        "peak_year": peak_year,
        "crossing_year": crossing_year,
        "cumulative_incremental_cdr_to_target_gtco2": cumulative_cdr_to_target,
        "cumulative_reversal_to_target_gtco2": cumulative_reversal_to_target,
        "cumulative_permafrost_to_target_gtco2": cumulative_permafrost_to_target,
        "stock_at_end_gtco2": sum(stocks.values()),
        "pathway_stock_at_end_gtco2": dict(stocks),
        "maintenance_shortfall_years": shortfalls,
        "target_held": (not shortfalls) if crossing_year is not None else None,
        "rows": rows,
        "pathway_rows": pathway_rows,
    }


def homogeneous_leakage_sensitivity(
    core_rows: Sequence[Mapping], rates: Sequence[float] = (0.0001, 0.0005, 0.001, 0.002)
) -> List[Dict]:
    """Pure stock arithmetic sensitivity matching the user's requested leakage framing.

    It applies one homogeneous leakage rate to the actual annual CDR series. This is
    deliberately separate from the pathway-specific physical run above.
    """
    out = []
    for rate in rates:
        stock = 0.0
        released = 0.0
        for r in core_rows:
            leakage = stock * rate
            stock -= leakage
            released += leakage
            stock += float(r.get("actual_incremental_cdr_gtco2", r.get("incremental_cdr_gtco2", 0.0)))
        ppm = released / (prm.CO2_GTC_TO_GTCO2 * prm.CO2_MASS_GTC_PER_PPM)
        # Maintenance years at the mature 4.37-ish core maintenance scale is not a
        # physical law; report a direct-equivalent years screen using the final CDR rate.
        final_rate = max(1e-9, float(core_rows[-1].get("actual_incremental_cdr_gtco2", 0.0)))
        out.append({
            "annual_leakage_fraction": rate,
            "annual_leakage_percent": 100.0 * rate,
            "cumulative_released_gtco2": released,
            "ppm_equivalent": ppm,
            "equivalent_maintenance_years_at_final_cdr": released / final_rate,
        })
    return out


# ======================================================================================
# 4. Dynamic CH4, N2O, aerosols and climate response
# ======================================================================================

def _other_source_index(year: int, floor_2100: float) -> float:
    return _interp(year, {2026: 1.0, 2100: floor_2100, 2200: floor_2100})


def dynamic_nonco2_states(
    years: Iterable[int],
    s: prm.Scenario,
    land_case: str = "central",
    assumptions: GasCycleAssumptions = GasCycleAssumptions(),
    emissions_override: Optional[Mapping[int, float]] = None,
) -> List[Dict]:
    if land_case not in prm.LAND_CASES:
        raise KeyError(land_case)
    land_cfg = prm.LAND_CASES[land_case]
    baseline_land = prm.food_land(prm.START_YEAR, land_cfg)
    ch4 = CH4_2026_PPB
    n2o = N2O_2026_PPB
    ch4_source0 = (CH4_2026_PPB - CH4_PI_PPB) / assumptions.ch4_lifetime_yr
    n2o_source0 = (N2O_2026_PPB - N2O_PI_PPB) / assumptions.n2o_lifetime_yr
    rows: List[Dict] = []

    for year in years:
        emissions = (float(emissions_override[year]) if emissions_override and year in emissions_override
                     else float(prm.gross_emissions_path(year, s)))
        fossil_idx = max(0.0, emissions / max(1e-9, s.emissions_anchor_gtco2))
        food = prm.food_land(year, land_cfg)
        livestock_idx = food["livestock_land_intensity_factor"]
        cropland_idx = food["food_cropland_mha"] / baseline_land["food_cropland_mha"]
        other_ch4 = _other_source_index(year, assumptions.other_ch4_floor_2100)
        other_n2o = _other_source_index(year, assumptions.other_n2o_floor_2100)

        ch4_source_idx = (assumptions.ch4_livestock_share * livestock_idx
                          + assumptions.ch4_fossil_share * fossil_idx
                          + assumptions.ch4_other_share * other_ch4)
        n2o_source_idx = (assumptions.n2o_cropland_share * cropland_idx
                          + assumptions.n2o_livestock_share * livestock_idx
                          + assumptions.n2o_fossil_share * fossil_idx
                          + assumptions.n2o_other_share * other_n2o)

        # One-box concentration states, annual Euler update.
        ch4 += ch4_source0 * ch4_source_idx - (ch4 - CH4_PI_PPB) / assumptions.ch4_lifetime_yr
        n2o += n2o_source0 * n2o_source_idx - (n2o - N2O_PI_PPB) / assumptions.n2o_lifetime_yr
        ch4 = max(CH4_PI_PPB, ch4)
        n2o = max(N2O_PI_PPB, n2o)

        f_ch4 = 0.036 * (math.sqrt(ch4) - math.sqrt(CH4_PI_PPB))
        f_n2o = 0.12 * (math.sqrt(n2o) - math.sqrt(N2O_PI_PPB))
        f_aerosol = assumptions.aerosol_2026_w_m2 * (fossil_idx ** assumptions.aerosol_fossil_exponent)
        f_residual = _interp(year, {2026: assumptions.residual_nonco2_2026_w_m2,
                                    2120: assumptions.residual_nonco2_2120_w_m2,
                                    2200: assumptions.residual_nonco2_2120_w_m2})
        total = f_ch4 + f_n2o + f_aerosol + f_residual
        rows.append({
            "year": year,
            "ch4_ppb": ch4,
            "n2o_ppb": n2o,
            "fossil_combustion_index": fossil_idx,
            "livestock_source_index": livestock_idx,
            "cropland_source_index": cropland_idx,
            "ch4_source_index": ch4_source_idx,
            "n2o_source_index": n2o_source_idx,
            "ch4_forcing_w_m2": f_ch4,
            "n2o_forcing_w_m2": f_n2o,
            "aerosol_forcing_w_m2": f_aerosol,
            "residual_nonco2_forcing_w_m2": f_residual,
            "nonco2_forcing_w_m2": total,
        })
    return rows


def climate_with_dynamic_nonco2(
    co2_rows: Sequence[Mapping],
    gas_rows: Sequence[Mapping],
    p: prm.ClimateParams = prm.ClimateParams(),
) -> Dict:
    gas = {int(r["year"]): r for r in gas_rows}
    init = prm.climate_spinup(p, end_year=prm.START_YEAR - 1)
    t, td = init["surface_warming_c"], init["deep_ocean_warming_c"]
    rows = []
    peak_t, peak_year = t, prm.START_YEAR
    years_above_15 = 0
    years_above_20 = 0
    warming_at_target = None
    for rec in co2_rows:
        year = int(rec["year"])
        ppm = float(rec["co2_ppm"])
        f_co2 = prm.co2_forcing(ppm)
        f_other = float(gas[year]["nonco2_forcing_w_m2"])
        t, td, imbalance, heat_uptake = prm._climate_step(t, td, f_co2 + f_other, p)
        if t > peak_t:
            peak_t, peak_year = t, year
        years_above_15 += int(t > 1.5)
        years_above_20 += int(t > 2.0)
        if warming_at_target is None and ppm <= prm.TARGET_CO2_PPM:
            warming_at_target = t
        rows.append({
            "year": year,
            "co2_ppm": ppm,
            "co2_forcing_w_m2": f_co2,
            "nonco2_forcing_w_m2": f_other,
            "total_forcing_w_m2": f_co2 + f_other,
            "surface_warming_c": t,
            "deep_ocean_warming_c": td,
            "earth_energy_imbalance_w_m2": imbalance,
            "ocean_heat_uptake_w_m2": heat_uptake,
            "ch4_ppb": gas[year]["ch4_ppb"],
            "n2o_ppb": gas[year]["n2o_ppb"],
            "aerosol_forcing_w_m2": gas[year]["aerosol_forcing_w_m2"],
        })
    return {
        "peak_warming_c": peak_t,
        "peak_year": peak_year,
        "years_above_1p5": years_above_15,
        "years_above_2p0": years_above_20,
        "warming_at_co2_target_c": warming_at_target,
        "rows": rows,
    }


# ======================================================================================
# 5. Surface-ocean carbonate system + OAE alkalinity state
# ======================================================================================

def _raw_surface_ph(pco2_ppm: float, total_alkalinity_umol_kg: float) -> float:
    """Compact fixed-T/S carbonate equilibrium solve.

    Includes carbonate, borate and water alkalinity. It is deliberately smaller than
    CO2SYS/PyCO2SYS and is calibrated below only for a global surface-ocean screening
    diagnostic.
    """
    K0 = 0.034       # mol kg-1 atm-1, global-screen value
    K1 = 10.0 ** -6.0
    K2 = 10.0 ** -9.1
    KB = 10.0 ** -8.6
    KW = 1.0e-14
    total_boron = 416.0e-6
    ta = total_alkalinity_umol_kg * 1.0e-6
    co2aq = K0 * pco2_ppm * 1.0e-6

    def alkalinity(ph: float) -> float:
        h = 10.0 ** (-ph)
        hco3 = K1 * co2aq / h
        co3 = K1 * K2 * co2aq / (h * h)
        borate = total_boron * KB / (KB + h)
        oh = KW / h
        return hco3 + 2.0 * co3 + borate + oh - h

    lo, hi = 6.5, 9.3
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if alkalinity(mid) > ta:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def calibrated_surface_ph(
    pco2_ppm: float,
    total_alkalinity_umol_kg: float,
    assumptions: OceanCarbonateAssumptions = OceanCarbonateAssumptions(),
) -> float:
    raw_pi = _raw_surface_ph(280.0, assumptions.baseline_total_alkalinity_umol_kg)
    raw = _raw_surface_ph(pco2_ppm, total_alkalinity_umol_kg)
    return assumptions.preindustrial_surface_ph + assumptions.equilibrium_anomaly_scale * (raw - raw_pi)


def ocean_surface_state(
    carbon_rows: Sequence[Mapping],
    pathway_rows: Sequence[Mapping],
    assumptions: OceanCarbonateAssumptions = OceanCarbonateAssumptions(),
) -> List[Dict]:
    by_year_oae: Dict[int, float] = {}
    for r in pathway_rows:
        if r["pathway"] == "Ocean alkalinity / carbonate weathering":
            by_year_oae[int(r["year"])] = float(r["new_storage_gtco2"])

    mixed_mass = (assumptions.ocean_area_m2 * assumptions.surface_mixed_layer_depth_m
                  * assumptions.seawater_density_kg_m3)
    excess_alk_umol_kg = 0.0
    rows = []
    for r in carbon_rows:
        year = int(r["year"])
        # Export/re-equilibration of the added surface alkalinity inventory.
        excess_alk_umol_kg *= math.exp(-1.0 / assumptions.oae_surface_retention_yr)
        oae_gt = by_year_oae.get(year, 0.0)
        mol_co2 = oae_gt * 1.0e15 / 44.0095
        delta_mol_alk_per_kg = (mol_co2 * assumptions.oae_alkalinity_equiv_per_mol_co2) / mixed_mass
        excess_alk_umol_kg += delta_mol_alk_per_kg * 1.0e6
        ta = assumptions.baseline_total_alkalinity_umol_kg + excess_alk_umol_kg
        ph = calibrated_surface_ph(float(r["co2_ppm"]), ta, assumptions)
        ph_no_oae = calibrated_surface_ph(float(r["co2_ppm"]),
                                          assumptions.baseline_total_alkalinity_umol_kg,
                                          assumptions)
        rows.append({
            "year": year,
            "atmospheric_pco2_ppm": float(r["co2_ppm"]),
            "oae_cdr_gtco2_yr": oae_gt,
            "total_alkalinity_umol_kg": ta,
            "oae_alkalinity_anomaly_umol_kg": excess_alk_umol_kg,
            "surface_ocean_ph": ph,
            "surface_ocean_ph_without_oae": ph_no_oae,
            "oae_ph_increment": ph - ph_no_oae,
        })
    return rows


# ======================================================================================
# 6. No-action comparator and avoided climate damages
# ======================================================================================

def no_action_emissions(year: int) -> float:
    return _interp(year, {2026: 42.2, 2050: 45.0, 2100: 40.0, 2150: 30.0, 2200: 20.0,
                          2300: 10.0, 2400: 5.0})


def carbon_cycle_from_emissions(emissions_by_year: Mapping[int, float], end_year: int,
                                permafrost_by_year: Mapping[int, float] | None = None) -> List[Dict]:
    """Emissions-driven reduced carbon cycle.

    permafrost_by_year adds a temperature-driven permafrost source on the same terms as
    the restoration run. Without it the comparator charges the COOLER world a permafrost
    penalty and the HOTTER world none, which is backwards: the feedback is monotonic in
    attained warming, so the no-action world must carry the larger source, not zero.
    """
    init = prm.initialize_carbon_state()
    state = list(init["state_gtc"])
    rows = []
    for year in range(prm.START_YEAR, end_year + 1):
        emissions = float(emissions_by_year[year])
        permafrost = float((permafrost_by_year or {}).get(year, 0.0))
        emissions = emissions + permafrost
        state, sink = prm._advance_reservoirs(state, emissions)
        ppm = prm.PREINDUSTRIAL_CO2_PPM + sum(state) / prm.CO2_MASS_GTC_PER_PPM
        rows.append({"year": year, "gross_emissions_gtco2": emissions,
                     "permafrost_source_gtco2": permafrost,
                     "co2_ppm": ppm, "natural_reservoir_flux_to_sinks_gtc": sink})
    return rows


def damage_fraction(warming_c: float, damage_at_3c: float,
                    reference_warming_c: float = 1.20) -> float:
    if warming_c <= reference_warming_c:
        return 0.0
    denom = 3.0 ** 2 - reference_warming_c ** 2
    a = damage_at_3c / denom
    return max(0.0, a * (warming_c ** 2 - reference_warming_c ** 2))


def avoided_damage_screen(
    restoration_climate_rows: Sequence[Mapping],
    no_action_climate_rows: Sequence[Mapping],
    s: prm.Scenario,
    assumptions: DamageAssumptions = DamageAssumptions(),
) -> Dict:
    restoration = {int(r["year"]): r for r in restoration_climate_rows}
    noaction = {int(r["year"]): r for r in no_action_climate_rows}
    common = sorted(set(restoration) & set(noaction))
    cases = {
        "low_2pct_at_3c": assumptions.low_damage_at_3c_fraction_gdp,
        "central_5pct_at_3c": assumptions.central_damage_at_3c_fraction_gdp,
        "high_15pct_at_3c": assumptions.high_damage_at_3c_fraction_gdp,
    }
    rows = []
    cumul = {k: 0.0 for k in cases}
    for year in common:
        gdp = prm._gdp_screen_for_year(year, s)
        row = {"year": year, "gdp_screen_usd_tn": gdp,
               "restoration_warming_c": float(restoration[year]["surface_warming_c"]),
               "no_action_warming_c": float(noaction[year]["surface_warming_c"])}
        for key, at3 in cases.items():
            dr = damage_fraction(row["restoration_warming_c"], at3, assumptions.reference_warming_c)
            dn = damage_fraction(row["no_action_warming_c"], at3, assumptions.reference_warming_c)
            avoided = max(0.0, (dn - dr) * gdp)
            cumul[key] += avoided
            row[f"restoration_damage_fraction_{key}"] = dr
            row[f"no_action_damage_fraction_{key}"] = dn
            row[f"avoided_damage_usd_tn_{key}"] = avoided
            row[f"cumulative_avoided_damage_usd_tn_{key}"] = cumul[key]
        rows.append(row)
    return {
        "classification": "Illustrative reduced-form damage screen, not a welfare or IAM result.",
        "damage_function": "quadratic in warming above 1.2 C, normalized to low/central/high loss at 3 C",
        "cumulative_avoided_damage_usd_tn": cumul,
        "rows": rows,
    }


def economic_balance_screen(
    damage_result: Dict,
    carbon_rows: Sequence[Mapping],
    s: prm.Scenario,
    land_case: str,
    assumptions: DamageAssumptions = DamageAssumptions(),
) -> Dict:
    """Put avoided damages and the model's incremental restoration costs on one ledger.

    Transition investment is taken from the endogenous transition module, which in
    The audited transition accounting charges only capital actually allocated to remaining abatable dirty stock;
    ordinary replacement capital after full conversion is not charged asymmetrically to
    restoration. CDR cost is scaled to the *actual* advanced CDR rate after saturation and
    reversal. The screen still excludes distributional effects and non-climate co-benefits.
    """
    end_year = int(carbon_rows[-1]["year"])
    trans = prm.transition_run_case(getattr(s, "transition_case_key", "iea_nze_reference"), end_year)
    trans_by_year = {int(r["year"]): r for r in trans["rows"]}
    fin = prm.dynamic_finance_ramp(s, land_case, end_year=end_year)
    fin_by_year = {int(r["year"]): r for r in fin}
    carbon = {int(r["year"]): r for r in carbon_rows}
    damage = {int(r["year"]): r for r in damage_result["rows"]}
    rows=[]
    cumul_cost=0.0; pv_cost=0.0
    cumul_net={k:0.0 for k in ("low_2pct_at_3c","central_5pct_at_3c","high_15pct_at_3c")}
    pv_net={k:0.0 for k in cumul_net}
    for year in sorted(carbon):
        f=fin_by_year[year]
        feasible=max(1e-12,float(f["feasible_cdr_gtco2"]))
        actual=float(carbon[year]["actual_incremental_cdr_gtco2"])
        cdr_cost=float(f["dynamic_cdr_spend_usd_tn"]) * actual/feasible if feasible>0 else 0.0
        transition_cost=float(trans_by_year.get(year,{}).get("transition_investment_usd_tn",0.0) or 0.0)
        gross_cost=transition_cost+cdr_cost
        discount=1.0/((1.0+assumptions.real_discount_rate)**(year-prm.START_YEAR))
        cumul_cost += gross_cost; pv_cost += gross_cost*discount
        row={"year":year,"transition_investment_usd_tn":transition_cost,
             "advanced_cdr_cost_usd_tn":cdr_cost,"gross_programme_cost_usd_tn":gross_cost,
             "cumulative_gross_programme_cost_usd_tn":cumul_cost,"pv_gross_programme_cost_usd_tn":pv_cost}
        d=damage.get(year,{})
        for key in cumul_net:
            benefit=float(d.get(f"avoided_damage_usd_tn_{key}",0.0))
            net=benefit-gross_cost
            cumul_net[key]+=net; pv_net[key]+=net*discount
            row[f"avoided_damage_usd_tn_{key}"]=benefit
            row[f"net_benefit_usd_tn_{key}"]=net
            row[f"cumulative_net_benefit_usd_tn_{key}"]=cumul_net[key]
            row[f"pv_cumulative_net_benefit_usd_tn_{key}"]=pv_net[key]
        rows.append(row)
    def snapshot(year):
        candidates=[r for r in rows if r["year"]<=year]
        return candidates[-1] if candidates else None
    sustained_break_even_year = None
    for i, rr in enumerate(rows):
        if rr["cumulative_net_benefit_usd_tn_central_5pct_at_3c"] >= 0.0 and all(
            xx["cumulative_net_benefit_usd_tn_central_5pct_at_3c"] >= 0.0 for xx in rows[i:]
        ):
            sustained_break_even_year = rr["year"]
            break
    target_year = next((int(rr["year"]) for rr in carbon_rows
                        if float(rr["co2_ppm"]) <= prm.TARGET_CO2_PPM), int(carbon_rows[-1]["year"]))
    return {
        "classification": ("Incremental transition-conversion capital plus gross CDR cost versus "
                           "avoided-climate-damage screen. Ordinary post-conversion replacement "
                           "capital is excluded symmetrically; non-climate co-benefits and "
                           "distributional welfare remain excluded."),
        "discount_rate_real": assumptions.real_discount_rate,
        "sustained_cumulative_break_even_year_central": sustained_break_even_year,
        "through_2100": snapshot(2100),
        "at_280": snapshot(target_year),
        "full_horizon": rows[-1] if rows else None,
        "rows": rows,
    }


# ======================================================================================
# 7. Post-restoration social-dividend policy screen
# ======================================================================================

def post_restoration_social_dividend_screen(
    economics: Dict, carbon_rows: Sequence[Mapping], s: prm.Scenario, land_case: str,
    assumptions: SocialDividendAssumptions = SocialDividendAssumptions(),
) -> Dict:
    """Allocate potential post-280 settlement headroom to public-good programmes.

    Avoided damages are not treated as spendable cash. The allocable amount is the
    lesser of the central settlement-network collection capacity and the policy cap,
    minus continuing programme cost. Keeping the levy after restoration is an explicit
    policy choice; society could instead reduce it and return the headroom to households.
    """
    if abs(assumptions.allocation_total() - 1.0) > 1e-9:
        raise ValueError("social-dividend allocation fractions must sum to 1.0")
    crossing = next((int(r["year"]) for r in carbon_rows
                     if float(r["co2_ppm"]) <= prm.TARGET_CO2_PPM), None)
    econ = {int(r["year"]): r for r in economics["rows"]}
    case = prm.SETTLEMENT_COLLECTION_CASES[0]
    allocations = {
        "housing_and_homelessness": assumptions.housing_fraction,
        "job_creation_local_enterprise_and_vocational_training": assumptions.job_creation_fraction,
        "public_health_and_preventive_care": assumptions.health_fraction,
        "food_security_and_child_nutrition": assumptions.food_security_fraction,
        "education_and_scholarships": assumptions.education_fraction,
        "clean_water_and_sanitation": assumptions.clean_water_sanitation_fraction,
        "disaster_resilience_and_adaptation": assumptions.disaster_resilience_fraction,
        "ecosystems_and_biodiversity": assumptions.ecosystems_biodiversity_fraction,
        "direct_cash_and_emergency_relief": assumptions.direct_cash_emergency_fraction,
    }
    rows=[]; cumulative={k:0.0 for k in allocations}; cumulative_total=0.0
    for year in sorted(econ):
        e=econ[year]
        gdp=prm._gdp_screen_for_year(year,s)
        policy_cap=gdp*assumptions.settlement_envelope_fraction_gdp
        network_cap=prm.settlement_maximum_collection(gdp,case)["max_collection_usd_tn"]
        available=min(policy_cap,network_cap)
        programme_cost=float(e.get("gross_programme_cost_usd_tn",0.0) or 0.0)
        active=crossing is not None and year>=crossing
        allocable=max(0.0,available-programme_cost) if active else 0.0
        row={"year":year,"post_280_active":active,"gdp_screen_usd_tn":gdp,
             "settlement_policy_cap_usd_tn":policy_cap,
             "settlement_network_capacity_usd_tn":network_cap,
             "available_collection_envelope_usd_tn":available,
             "continuing_programme_cost_usd_tn":programme_cost,
             "annual_allocable_social_dividend_usd_tn":allocable,
             "annual_central_social_net_benefit_usd_tn":float(e.get("net_benefit_usd_tn_central_5pct_at_3c",0.0) or 0.0)}
        for k,f in allocations.items():
            amt=allocable*f; cumulative[k]+=amt
            row[k+"_usd_tn"]=amt; row["cumulative_"+k+"_usd_tn"]=cumulative[k]
        cumulative_total+=allocable
        row["cumulative_allocable_social_dividend_usd_tn"]=cumulative_total
        rows.append(row)
    post=[r for r in rows if r["post_280_active"]]
    return {
        "classification": ("Policy allocation screen for potential settlement-envelope headroom after the "
                           "280-ppm crossing; avoided damages are not treated as cash and continued levy "
                           "collection is an explicit policy choice."),
        "crossing_year":crossing,"allocation_fractions":allocations,
        "all_post_crossing_years_positive_headroom":bool(post) and all(r["annual_allocable_social_dividend_usd_tn"]>0 for r in post),
        "first_year_allocable_usd_tn":post[0]["annual_allocable_social_dividend_usd_tn"] if post else None,
        "final_year_allocable_usd_tn":post[-1]["annual_allocable_social_dividend_usd_tn"] if post else None,
        "cumulative_allocable_usd_tn":cumulative_total,"rows":rows}


# ======================================================================================
# 8. Critical minerals and workforce feasibility screens
# ======================================================================================

def mature_electricity_screen(s: prm.Scenario, land_case: str) -> Dict:
    """Pre-CDR transformed demand plus CDR-direct demand at maturity.

    SCOPE: this is deliberately NARROWER than the core model's
    `core_transformed_electricity_twh_yr`, which additionally includes core water
    treatment/reuse and marine-cleanup electricity. The two therefore differ by
    ~199 TWh/yr and must not be quoted interchangeably. This screen exists to drive
    the critical-minerals build-out, which is sized on generation and storage for the
    energy system proper.
    """
    p = prm.effective_cdr_path(s.cdr_maturity_year, s, land_case)
    base = prm.BaseSystemInputs().pre_cdr_transformed_electricity_twh_yr
    return {
        "pre_cdr_twh_yr": base,
        "cdr_twh_yr": p["electricity_twh_yr"],
        "total_twh_yr": base + p["electricity_twh_yr"],
        "cdr_gtco2_yr": p["cdr_gtco2_yr"],
        "portfolio": p,
    }


def critical_minerals_screen(total_electricity_twh_yr: float,
                             a: MineralAssumptions = MineralAssumptions()) -> Dict:
    avg_load_tw = total_electricity_twh_yr / 8760.0
    avg_load_mw = avg_load_tw * 1.0e6
    vre_mw = avg_load_mw * a.variable_renewables_fraction / a.vre_capacity_factor
    firm_mw = avg_load_mw * a.firm_clean_fraction / a.firm_capacity_factor
    storage_kwh = avg_load_mw * a.battery_storage_share_of_avg_load * a.battery_storage_hours * 1000.0
    copper_mt = (vre_mw * a.vre_copper_t_per_mw
                 + firm_mw * a.firm_copper_t_per_mw
                 + avg_load_mw * a.grid_copper_t_per_mw_avg_load) / 1.0e6
    lithium_mt = storage_kwh * a.lithium_kg_per_kwh / 1.0e9
    nickel_mt = (storage_kwh * a.nickel_battery_share
                 * a.nickel_kg_per_kwh_for_nickel_chemistries) / 1.0e9
    steel_gt = (vre_mw * a.vre_steel_t_per_mw
                + firm_mw * a.firm_steel_t_per_mw
                + avg_load_mw * a.grid_steel_t_per_mw_avg_load) / 1.0e9
    return {
        "classification": "Engineering material-demand screen; not a mine-by-mine supply model.",
        "total_electricity_twh_yr": total_electricity_twh_yr,
        "average_load_tw": avg_load_tw,
        "variable_renewable_nameplate_tw": vre_mw / 1e6,
        "firm_clean_nameplate_tw": firm_mw / 1e6,
        "battery_storage_twh": storage_kwh / 1e9,
        "copper_mt_buildout": copper_mt,
        "lithium_mt_buildout": lithium_mt,
        "nickel_mt_buildout": nickel_mt,
        "steel_gt_buildout": steel_gt,
        "supply_context": {
            "copper": "IEA 2026 outlook projects a material 2035 supply gap in the current project pipeline; treat as binding-risk screen.",
            "lithium": "IEA projects strong demand growth and persistent medium-term supply risk.",
            "nickel": "Large absolute demand growth; chemistry substitution materially changes the result.",
            "steel": "Large tonnage but generally less geologically scarce; energy/process emissions remain important.",
        },
        "assumptions": asdict(a),
    }


def workforce_screen(
    electricity: Dict,
    s: prm.Scenario,
    land_case: str,
    a: WorkforceAssumptions = WorkforceAssumptions(),
) -> Dict:
    p = electricity["portfolio"]
    land = p["land_nexus"]
    by_path = {r["pathway"]: float(r["cdr_gtco2_yr"]) for r in p["rows"]}
    # Existing model values are used where available; the productivity denominators are
    # new explicit engineering-screen assumptions.
    ew_gt = by_path.get("Enhanced silicate weathering", 0.0)
    mineral_gt = by_path.get("Direct/passive mineral carbonation", 0.0)
    rock_gt = (ew_gt + mineral_gt) * 2.5  # transparent stoichiometric/logistics screen
    spreading_mha = float(land.get("ew_spreading_area_mha", 0.0))
    restoration_mha = float(land.get("biological_restoration_land_mha", 0.0))
    if not restoration_mha:
        # The land nexus exposes realized total CDR land. Keep a conservative fallback.
        restoration_mha = 0.20 * float(land.get("realized_cdr_land_mha", 0.0))
    biomass_gt = 0.0
    land_cfg = prm.LAND_CASES[land_case]
    for pathway in ("Biochar", "BiCRS / BECCS / durable biomass storage"):
        biomass_gt += prm._biomass_land_and_water(pathway, by_path.get(pathway, 0.0), land_cfg)["dedicated_biomass_gt_yr"]

    rock_mining_fte = rock_gt * 1e9 / a.rock_mined_t_per_worker_yr
    rock_spreading_fte = spreading_mha * 1e6 / a.rock_spread_ha_per_worker_yr
    biomass_fte = biomass_gt * 1e9 / a.biomass_handled_t_per_worker_yr
    engineered_gt = sum(v for k, v in by_path.items() if k != "Biological restoration")
    cdr_ops_fte = engineered_gt * 1e9 / a.engineered_cdr_tco2_per_worker_yr
    restoration_fte = restoration_mha * 1e6 / a.ecosystem_restoration_ha_per_worker_yr
    avg_load_mw = electricity["total_twh_yr"] / 8760.0 * 1e6
    power_ops_fte = avg_load_mw / a.operations_mw_per_worker
    # Spread the one-time build across 25 years for an annual build-labor screen.
    minerals = critical_minerals_screen(electricity["total_twh_yr"])
    nameplate_mw = (minerals["variable_renewable_nameplate_tw"]
                    + minerals["firm_clean_nameplate_tw"]) * 1e6
    power_build_fte = nameplate_mw / 25.0 / a.power_build_mw_per_worker_yr
    total = sum((rock_mining_fte, rock_spreading_fte, biomass_fte, cdr_ops_fte,
                 restoration_fte, power_ops_fte, power_build_fte))
    return {
        "classification": "Global order-of-magnitude workforce screen; excludes supply-chain multipliers and regional skill matching.",
        "mature_ongoing_plus_annualized_build_fte": total,
        "rock_mining_fte": rock_mining_fte,
        "rock_spreading_fte": rock_spreading_fte,
        "biomass_logistics_fte": biomass_fte,
        "engineered_cdr_operations_fte": cdr_ops_fte,
        "ecosystem_restoration_fte": restoration_fte,
        "power_operations_fte": power_ops_fte,
        "power_build_annualized_fte_over_25yr": power_build_fte,
        "rock_flow_gt_yr_screen": rock_gt,
        "spreading_area_mha": spreading_mha,
        "restoration_area_mha": restoration_mha,
        "dedicated_biomass_gt_yr": biomass_gt,
        "assumptions": asdict(a),
    }


# ======================================================================================
# 8. ICON state-variable registry / coupling contract
# ======================================================================================

ICON_STATE_REGISTRY: List[Dict] = [
    # Atmosphere
    {"component":"Atmosphere","state_family":"virtual_potential_temperature","unit":"K","kind":"prognostic","vertical_levels":"90","source":"ICON-Atmo"},
    {"component":"Atmosphere","state_family":"air_density","unit":"kg m-3","kind":"prognostic","vertical_levels":"90","source":"ICON-Atmo"},
    {"component":"Atmosphere","state_family":"wind_normal_components","unit":"m s-1","kind":"prognostic","vertical_levels":"90","source":"ICON-Atmo"},
    {"component":"Atmosphere","state_family":"water_vapour_qv","unit":"kg kg-1","kind":"tracer","vertical_levels":"90","source":"ICON tracer transport"},
    {"component":"Atmosphere","state_family":"cloud_liquid_qc","unit":"kg kg-1","kind":"tracer","vertical_levels":"90","source":"ICON tracer transport"},
    {"component":"Atmosphere","state_family":"rain_qr","unit":"kg kg-1","kind":"tracer","vertical_levels":"90","source":"ICON tracer transport"},
    {"component":"Atmosphere","state_family":"cloud_ice_qi","unit":"kg kg-1","kind":"tracer","vertical_levels":"90","source":"ICON tracer transport"},
    {"component":"Atmosphere","state_family":"snow_qs","unit":"kg kg-1","kind":"tracer","vertical_levels":"90","source":"ICON tracer transport"},
    {"component":"Atmosphere","state_family":"graupel_qg","unit":"kg kg-1","kind":"tracer","vertical_levels":"90","source":"ICON microphysics"},
    {"component":"Atmosphere","state_family":"co2","unit":"ppmv / mass fraction","kind":"tracer","vertical_levels":"90","source":"ICON carbon-cycle coupling"},
    {"component":"Atmosphere","state_family":"ozone_o3","unit":"mixing ratio","kind":"tracer","vertical_levels":"90","source":"ICON radiation/tracer"},
    {"component":"Atmosphere","state_family":"methane_ch4","unit":"ppbv / mixing ratio","kind":"radiatively active gas","vertical_levels":"90","source":"ICON ecRad gas interface"},
    {"component":"Atmosphere","state_family":"nitrous_oxide_n2o","unit":"ppbv / mixing ratio","kind":"radiatively active gas","vertical_levels":"90","source":"ICON ecRad gas interface"},
    {"component":"Atmosphere","state_family":"aerosol_optical_depth_by_species","unit":"1","kind":"prognostic option","vertical_levels":"column","source":"ICON Prog2DAero"},
    # Land / vegetation
    {"component":"Land","state_family":"soil_temperature","unit":"K","kind":"prognostic","vertical_levels":"5 in benchmark configuration","source":"ICON-Land/JSBACH"},
    {"component":"Land","state_family":"soil_water","unit":"kg m-2 / fraction","kind":"prognostic","vertical_levels":"5 in benchmark configuration","source":"ICON-Land/JSBACH"},
    {"component":"Land","state_family":"snow_and_surface_water","unit":"kg m-2","kind":"prognostic","vertical_levels":"surface/soil","source":"ICON-Land/JSBACH"},
    {"component":"Land","state_family":"runoff_drainage","unit":"kg m-2 s-1","kind":"flux/state diagnostic","vertical_levels":"surface/soil","source":"ICON-Land/JSBACH"},
    {"component":"Vegetation","state_family":"plant_functional_type_fraction","unit":"fraction","kind":"state","vertical_levels":"up to 11 PFTs in paper benchmark","source":"JSBACH"},
    {"component":"Vegetation","state_family":"leaf_area_index","unit":"m2 m-2","kind":"predicted","vertical_levels":"PFT tiles","source":"JSBACH"},
    {"component":"Vegetation","state_family":"terrestrial_carbon_pools_01_21","unit":"kg C m-2","kind":"prognostic pool family","vertical_levels":"PFT/soil","source":"paper Table 2: 21 additional carbon pools"},
    {"component":"Land","state_family":"albedo_roughness_surface_fluxes","unit":"mixed","kind":"coupling diagnostics","vertical_levels":"surface","source":"ICON-Land"},
    {"component":"Land","state_family":"fire_disturbance_land_cover_change","unit":"mixed","kind":"process/state","vertical_levels":"tiles","source":"JSBACH natural carbon-cycle/disturbance processes"},
    {"component":"Land","state_family":"permafrost_active_layer_carbon","unit":"kg C m-2","kind":"restoration-model extension","vertical_levels":"soil","source":"advanced extension; adapter target"},
    # Ocean / sea ice
    {"component":"Ocean","state_family":"potential_temperature","unit":"K / degC","kind":"prognostic","vertical_levels":"72 in benchmark configuration","source":"ICON-O"},
    {"component":"Ocean","state_family":"salinity","unit":"g kg-1","kind":"prognostic tracer","vertical_levels":"72","source":"ICON-O"},
    {"component":"Ocean","state_family":"velocity","unit":"m s-1","kind":"prognostic","vertical_levels":"72","source":"ICON-O"},
    {"component":"Ocean","state_family":"sea_surface_height_pressure","unit":"m / Pa","kind":"prognostic","vertical_levels":"surface","source":"ICON-O"},
    {"component":"Sea ice","state_family":"sea_ice_concentration_thickness_snow","unit":"fraction/m","kind":"prognostic","vertical_levels":"surface","source":"ICON sea-ice"},
    # HAMOCC BGC: public documentation says at least 20 water-column tracers; exact set is configuration-dependent.
    {"component":"Ocean biogeochemistry","state_family":"dissolved_inorganic_carbon","unit":"mol C m-3","kind":"tracer","vertical_levels":"72","source":"HAMOCC"},
    {"component":"Ocean biogeochemistry","state_family":"total_alkalinity","unit":"mol eq m-3","kind":"tracer","vertical_levels":"72","source":"HAMOCC / advanced OAE coupling"},
    {"component":"Ocean biogeochemistry","state_family":"phosphate","unit":"mol P m-3","kind":"tracer","vertical_levels":"72","source":"HAMOCC nutrient"},
    {"component":"Ocean biogeochemistry","state_family":"nitrate","unit":"mol N m-3","kind":"tracer","vertical_levels":"72","source":"HAMOCC nutrient"},
    {"component":"Ocean biogeochemistry","state_family":"silicate","unit":"mol Si m-3","kind":"tracer","vertical_levels":"72","source":"HAMOCC nutrient"},
    {"component":"Ocean biogeochemistry","state_family":"iron","unit":"mol Fe m-3","kind":"tracer","vertical_levels":"72","source":"HAMOCC nutrient"},
    {"component":"Ocean biogeochemistry","state_family":"oxygen","unit":"mol O2 m-3","kind":"tracer","vertical_levels":"72","source":"HAMOCC"},
    {"component":"Ocean biogeochemistry","state_family":"phytoplankton_zooplankton_detritus","unit":"mol element m-3","kind":"tracer families","vertical_levels":"72","source":"HAMOCC NPZD"},
    {"component":"Ocean biogeochemistry","state_family":"dissolved_organic_matter","unit":"mol element m-3","kind":"tracer family","vertical_levels":"72","source":"HAMOCC"},
    {"component":"Ocean biogeochemistry","state_family":"inorganic_particles_caco3_opal","unit":"mol m-3","kind":"tracer family","vertical_levels":"72","source":"HAMOCC"},
    {"component":"Ocean sediment","state_family":"active_sediment_bgc_layers","unit":"mixed","kind":"prognostic/process pools","vertical_levels":"12 active + burial layer","source":"HAMOCC"},
]


ICON_CONFIGURATION_COUNTS = {
    "paper_benchmark_1p25km": {
        "atmosphere_cells": 3.36e8,
        "atmosphere_levels": 90,
        "atmosphere_prognostic_variables_effective": 12.5,
        "atmosphere_timestep_s": 10,
        "land_cells": 0.98e8,
        "land_levels": 5,
        "land_physical_state_variables": 4,
        "vegetation_pfts_max": 11,
        "vegetation_predicted_variables": 22,
        "land_carbon_pools": 21,
        "ocean_seaice_cells": 2.38e8,
        "ocean_levels": 72,
        "ocean_seaice_prognostic_variables": 5,
        "ocean_timestep_s": 60,
        "ocean_biogeochemistry_variables_paper": 19,
        "physical_spatial_degrees_of_freedom": 7.9e11,
        "paper_text_approx_total_dof": 1.0e12,
        "double_precision_state_memory_tib_approx": 8.0,
    },
    "coupling": {
        "atmosphere_ocean_exchange": ["energy", "water", "carbon"],
        "atmosphere_ocean_coupling_interval_simulated_minutes": 10,
    },
}


# ======================================================================================
# 9. Full coupled run
# ======================================================================================

def run_advanced_model(
    s: prm.Scenario = prm.Scenario(),
    land_case: str = "central",
    assumptions: AdvancedAssumptions = AdvancedAssumptions(),
) -> Dict:
    # First driver: legacy temperature path. Subsequent fixed-point iterations feed the
    # advanced temperature response back into permafrost and climate-sensitive reversal.
    core = prm.carbon_cycle(s, land_case, maintain_after_target_years=assumptions.maintenance_after_target_years)
    legacy_climate = prm.climate_run(core["rows"])
    temp_driver = _temperature_by_year(legacy_climate["rows"])
    coupled_history = []

    carbon = None
    climate = None
    gas_rows = None
    permafrost = None
    for iteration in range(assumptions.coupling_iterations):
        driver_rows = [{"year": y, "surface_warming_c": t} for y, t in sorted(temp_driver.items())]
        permafrost = permafrost_source_from_temperature(driver_rows, assumptions.permafrost)
        carbon = durable_carbon_cycle(
            s, land_case, temp_driver, permafrost,
            maintain_after_target_years=assumptions.maintenance_after_target_years)
        years = [int(r["year"]) for r in carbon["rows"]]
        gas_rows = dynamic_nonco2_states(years, s, land_case, assumptions.gas)
        climate = climate_with_dynamic_nonco2(carbon["rows"], gas_rows)
        new_temp = _temperature_by_year(climate["rows"])
        overlap = sorted(set(temp_driver) & set(new_temp))
        max_delta = max((abs(new_temp[y] - temp_driver[y]) for y in overlap), default=0.0)
        coupled_history.append({"iteration": iteration + 1, "max_temperature_change_c": max_delta,
                                "return_280_year": carbon["crossing_year"],
                                "peak_warming_c": climate["peak_warming_c"]})
        temp_driver = new_temp

    assert carbon is not None and climate is not None and gas_rows is not None
    ocean = ocean_surface_state(carbon["rows"], carbon["pathway_rows"], assumptions.ocean)

    # No-action uses the same reduced carbon and gas/climate structures so avoided damages
    # are internally comparable rather than mixing unrelated climate models.
    end_year = int(carbon["rows"][-1]["year"])
    no_emis = {y: no_action_emissions(y) for y in range(prm.START_YEAR, end_year + 1)}
    no_permafrost: Dict[int, float] = {}
    no_carbon = no_gases = no_climate = None
    for _ in range(assumptions.coupling_iterations):
        no_carbon = carbon_cycle_from_emissions(no_emis, end_year, no_permafrost)
        no_gases = dynamic_nonco2_states(range(prm.START_YEAR, end_year + 1), s, land_case,
                                         assumptions.gas, emissions_override=no_emis)
        no_climate = climate_with_dynamic_nonco2(no_carbon, no_gases)
        no_permafrost = permafrost_source_from_temperature(no_climate["rows"],
                                                           assumptions.permafrost)
    assert no_carbon is not None and no_climate is not None
    damages = avoided_damage_screen(climate["rows"], no_climate["rows"], s, assumptions.damage)
    economics = economic_balance_screen(damages, carbon["rows"], s, land_case, assumptions.damage)
    social_dividend = post_restoration_social_dividend_screen(
        economics, carbon["rows"], s, land_case, assumptions.social_dividend)

    electricity = mature_electricity_screen(s, land_case)
    minerals = critical_minerals_screen(electricity["total_twh_yr"], assumptions.minerals)
    workforce = workforce_screen(electricity, s, land_case, assumptions.workforce)
    leakage = homogeneous_leakage_sensitivity(carbon["rows"])

    # A compact headline block intentionally avoids claiming kilometre-scale skill.
    pH_today = next((r["surface_ocean_ph"] for r in ocean if r["year"] == prm.START_YEAR), None)
    pH_target = next((r["surface_ocean_ph"] for r in ocean if r["atmospheric_pco2_ppm"] <= 280.0), None)
    no2100 = next((r for r in no_climate["rows"] if r["year"] == 2100), None)
    adv2100 = next((r for r in climate["rows"] if r["year"] == 2100), None)
    return {
        "model_version": ADVANCED_MODEL_VERSION,
        "release_label": ADVANCED_RELEASE_LABEL,
        "classification": (
            "Self-consistent reduced-complexity planetary-restoration screening model with an ICON-compatible "
            "state/coupling registry. It is not a 1.25-km dynamical Earth-system simulation."),
        "scenario": asdict(s),
        "advanced_assumptions": {
            "gas": asdict(assumptions.gas), "ocean": asdict(assumptions.ocean),
            "permafrost": asdict(assumptions.permafrost), "damage": asdict(assumptions.damage),
            "minerals": asdict(assumptions.minerals), "workforce": asdict(assumptions.workforce),
            "social_dividend": asdict(assumptions.social_dividend),
            "pathway_storage": {k: asdict(v) for k, v in PATHWAY_STORAGE.items()},
        },
        "headline": {
            "peak_co2_ppm": carbon["peak_co2_ppm"],
            "peak_co2_year": carbon["peak_year"],
            "return_280_year": carbon["crossing_year"],
            "cumulative_cdr_to_280_gtco2": carbon["cumulative_incremental_cdr_to_target_gtco2"],
            "cumulative_reversal_to_280_gtco2": carbon["cumulative_reversal_to_target_gtco2"],
            "cumulative_permafrost_to_280_gtco2": carbon["cumulative_permafrost_to_target_gtco2"],
            "stored_carbon_stock_end_gtco2": carbon["stock_at_end_gtco2"],
            "peak_warming_c": climate["peak_warming_c"],
            "peak_warming_year": climate["peak_year"],
            "warming_at_280_c": climate["warming_at_co2_target_c"],
            "surface_ocean_ph_2026": pH_today,
            "surface_ocean_ph_at_or_below_280": pH_target,
            "restoration_warming_2100_c": adv2100["surface_warming_c"] if adv2100 else None,
            "no_action_warming_2100_c": no2100["surface_warming_c"] if no2100 else None,
            "central_cumulative_avoided_damage_usd_tn": damages["cumulative_avoided_damage_usd_tn"]["central_5pct_at_3c"],
            "central_cumulative_net_benefit_through_2100_usd_tn": (economics["through_2100"] or {}).get("cumulative_net_benefit_usd_tn_central_5pct_at_3c"),
            "central_pv_net_benefit_through_2100_usd_tn": (economics["through_2100"] or {}).get("pv_cumulative_net_benefit_usd_tn_central_5pct_at_3c"),
            "central_full_horizon_net_benefit_usd_tn": (economics["full_horizon"] or {}).get("cumulative_net_benefit_usd_tn_central_5pct_at_3c"),
            "central_sustained_cumulative_break_even_year": economics["sustained_cumulative_break_even_year_central"],
            "central_cumulative_net_benefit_at_280_usd_tn": (economics["at_280"] or {}).get("cumulative_net_benefit_usd_tn_central_5pct_at_3c"),
            "mature_pre_cdr_plus_cdr_electricity_twh_yr": electricity["total_twh_yr"],
            "copper_mt_buildout_screen": minerals["copper_mt_buildout"],
            "lithium_mt_buildout_screen": minerals["lithium_mt_buildout"],
            "mature_workforce_fte_screen": workforce["mature_ongoing_plus_annualized_build_fte"],
            "post_280_first_year_allocable_social_dividend_usd_tn": social_dividend["first_year_allocable_usd_tn"],
            "post_280_all_years_positive_social_dividend_headroom": social_dividend["all_post_crossing_years_positive_headroom"],
        },
        "coupling_convergence": coupled_history,
        "durable_carbon": carbon,
        "nonco2_states": gas_rows,
        "climate": climate,
        "ocean_surface": ocean,
        "no_action": {"carbon": no_carbon, "nonco2_states": no_gases, "climate": no_climate},
        "avoided_damages": damages,
        "economic_balance": economics,
        "post_restoration_social_dividend": social_dividend,
        "critical_minerals": minerals,
        "workforce": workforce,
        "homogeneous_leakage_sensitivity": leakage,
        "icon": {"configuration_counts": ICON_CONFIGURATION_COUNTS,
                 "state_registry": ICON_STATE_REGISTRY,
                 "integration_mode": "external-source adapter / validation hierarchy"},
    }


# ======================================================================================
# 10. Output, plots and tests
# ======================================================================================

def _write_csv(path: Path, rows: Sequence[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: List[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                keys.append(k); seen.add(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in keys})


def run_advanced_tests(result: Optional[Dict] = None) -> None:
    r = result or run_advanced_model()
    carbon = r["durable_carbon"]
    assert carbon["rows"], "missing carbon trajectory"
    assert carbon["pathway_rows"], "missing pathway stocks"
    assert all(x["stock_gtco2"] >= -1e-9 for x in carbon["pathway_rows"])
    assert all(x["reversal_gtco2"] >= -1e-12 for x in carbon["pathway_rows"])
    # Year/pathway stock balance.
    prev = {p: 0.0 for p in PATHWAY_STORAGE}
    for x in carbon["pathway_rows"]:
        p = x["pathway"]
        expected = prev[p] - x["reversal_gtco2"] + x["new_storage_gtco2"]
        assert abs(expected - x["stock_gtco2"]) < 1e-7, (x, expected)
        prev[p] = x["stock_gtco2"]
    assert min(x["surface_ocean_ph"] for x in r["ocean_surface"]) > 7.5
    assert max(x["surface_ocean_ph"] for x in r["ocean_surface"]) < 8.5
    assert all(x["ch4_ppb"] >= CH4_PI_PPB for x in r["nonco2_states"])
    assert all(x["n2o_ppb"] >= N2O_PI_PPB for x in r["nonco2_states"])
    assert carbon["cumulative_permafrost_to_target_gtco2"] >= 0.0
    assert abs(carbon["rows"][0]["permafrost_source_gtco2"]) < 1e-12
    assert r["critical_minerals"]["copper_mt_buildout"] > 0.0
    assert r["workforce"]["mature_ongoing_plus_annualized_build_fte"] > 0.0
    assert r["economic_balance"]["through_2100"] is not None
    sd=r["post_restoration_social_dividend"]
    assert abs(sum(sd["allocation_fractions"].values())-1.0) < 1e-9
    if sd["crossing_year"] is not None:
        post=[x for x in sd["rows"] if x["year"] >= sd["crossing_year"]]
        assert post and all(x["annual_allocable_social_dividend_usd_tn"] >= 0.0 for x in post)
    # OAE must be able to affect its own pH state once deployed.
    assert max(abs(x["oae_ph_increment"]) for x in r["ocean_surface"]) > 0.0
    # No-action should be warmer by 2100 under the defined comparator if both runs extend there.
    h = r["headline"]
    if h["restoration_warming_2100_c"] is not None and h["no_action_warming_2100_c"] is not None:
        assert h["no_action_warming_2100_c"] > h["restoration_warming_2100_c"]
    print("ADVANCED EARTH-SYSTEM EXTENSION TESTS PASSED")


# ============================================================================================
# VERSION 52 RECONCILED OVERRIDES
# Implements v52_reconciled_change_order.md C1-C12. The earlier definitions remain available
# as low-level helpers, but every Version 52 headline/output is generated by the functions below.
# ============================================================================================

V52_MODEL_VERSION = "52.0"
V52_RELEASE_LABEL = "Planetary Restoration Model Version 52 — reconciled screening release"

@dataclass(frozen=True)
class GDPPathAssumptions:
    key: str
    label: str
    initial_growth: float
    asymptotic_growth: float
    decay_tau_yr: float
    status: str = "AUTHOR_DEFINED_LONG_RUN_SENSITIVITY"

GDP_CASES: Dict[str, GDPPathAssumptions] = {
    # C4 specifies the central path. Low/high are explicit sensitivity assumptions, not forecasts.
    "low": GDPPathAssumptions("low", "Low long-run growth", 0.015, 0.005, 60.0),
    "central": GDPPathAssumptions("central", "Central asymptotic growth", 0.025, 0.010, 75.0),
    "high": GDPPathAssumptions("high", "High long-run growth", 0.035, 0.015, 90.0),
}

@dataclass(frozen=True)
class RestorationControllerAssumptions:
    target_ppm: float = 280.0
    band_half_width_ppm: float = 0.5
    cdr_ramp_limit_gtco2_yr2: float = 0.5  # explicit controller sensitivity; safety overrides are logged

@dataclass(frozen=True)
class PermafrostLagAssumptions:
    # Inherited literature screen: 18 PgC / degC, converted to GtCO2 only when released.
    carbon_feedback_pgc_per_c: float = 18.0
    methane_feedback_pgc_equiv_per_c: float = 2.8
    activation_warming_c: float = 1.20
    thaw_release_tau_yr: float = 50.0
    methane_equivalent_lifetime_yr: float = 11.8
    # The methane term is retained as a forcing-side CO2e proxy, not added to carbon mass.
    include_methane_as_co2e_in_carbon_cycle: bool = False

@dataclass(frozen=True)
class NonCO2MitigationCase:
    key: str
    label: str
    ch4_target_2100_ppb: Optional[float]
    n2o_target_2100_ppb: Optional[float]
    status: str = "AUTHOR_DEFINED_CONCENTRATION_PATHWAY_SENSITIVITY"

NONCO2_MITIGATION_CASES: Dict[str, NonCO2MitigationCase] = {
    "baseline": NonCO2MitigationCase("baseline", "Baseline non-CO2 pathway", None, None),
    "strong": NonCO2MitigationCase("strong", "Strong CH4/N2O mitigation", 1000.0, 300.0),
    "near_pi": NonCO2MitigationCase("near_pi", "Near-preindustrial CH4/N2O", 750.0, 275.0),
}

@dataclass(frozen=True)
class FinancingAssumptionsV52:
    settlement_envelope_fraction_gdp: float = 0.0214
    transition_public_share: float = 0.35
    cdr_public_share: float = 1.00
    bridge_real_interest_rate: float = 0.02
    public_share_sweep_low: float = 0.25
    public_share_sweep_high: float = 0.60
    public_share_sweep_step: float = 0.01

@dataclass(frozen=True)
class SocialDividendAssumptionsV52:
    settlement_envelope_fraction_gdp: float = 0.0214
    maintenance_reserve_years: float = 5.0
    sustainable_average_years: int = 20
    real_discount_rate: float = 0.02
    housing_fraction: float = 0.25
    job_creation_fraction: float = 0.20
    health_fraction: float = 0.15
    food_security_fraction: float = 0.10
    education_fraction: float = 0.10
    clean_water_sanitation_fraction: float = 0.08
    disaster_resilience_fraction: float = 0.05
    ecosystems_biodiversity_fraction: float = 0.05
    direct_cash_emergency_fraction: float = 0.02

    def allocations(self) -> Dict[str, float]:
        return {
            "housing_and_homelessness": self.housing_fraction,
            "job_creation_local_enterprise_and_vocational_training": self.job_creation_fraction,
            "public_health_and_preventive_care": self.health_fraction,
            "food_security_and_child_nutrition": self.food_security_fraction,
            "education_and_scholarships": self.education_fraction,
            "clean_water_and_sanitation": self.clean_water_sanitation_fraction,
            "disaster_resilience_and_adaptation": self.disaster_resilience_fraction,
            "ecosystems_and_biodiversity": self.ecosystems_biodiversity_fraction,
            "direct_cash_and_emergency_relief": self.direct_cash_emergency_fraction,
        }

@dataclass(frozen=True)
class V52Assumptions:
    gas: GasCycleAssumptions = GasCycleAssumptions()
    ocean: OceanCarbonateAssumptions = OceanCarbonateAssumptions()
    damage: DamageAssumptions = DamageAssumptions()
    minerals: MineralAssumptions = MineralAssumptions()
    workforce: WorkforceAssumptions = WorkforceAssumptions()
    controller: RestorationControllerAssumptions = RestorationControllerAssumptions()
    permafrost: PermafrostLagAssumptions = PermafrostLagAssumptions()
    financing: FinancingAssumptionsV52 = FinancingAssumptionsV52()
    social_dividend: SocialDividendAssumptionsV52 = SocialDividendAssumptionsV52()
    coupling_iterations: int = 4
    maintenance_after_target_years: int = 30


def gdp_growth_rate_v52(year: int, case: GDPPathAssumptions) -> float:
    t = max(0.0, float(year - START_YEAR))
    return case.asymptotic_growth + (case.initial_growth - case.asymptotic_growth) * math.exp(-t / case.decay_tau_yr)


def gdp_series_v52(end_year: int, case_key: str = "central", start_gdp_usd_tn: float = 126.3) -> Dict[int, float]:
    if case_key not in GDP_CASES:
        raise KeyError(case_key)
    case = GDP_CASES[case_key]
    out = {START_YEAR: float(start_gdp_usd_tn)}
    gdp = float(start_gdp_usd_tn)
    for year in range(START_YEAR, end_year):
        gdp *= 1.0 + gdp_growth_rate_v52(year, case)
        out[year + 1] = gdp
    return out


def _move_toward(current: float, target: float, max_step: float) -> float:
    if target > current:
        return min(target, current + max_step)
    return max(target, current - max_step)


def permafrost_feedback_v52(
    temp_rows: Sequence[Mapping], assumptions: PermafrostLagAssumptions = PermafrostLagAssumptions()
) -> Dict:
    """Causal peak-ratchet commitment with a finite lagged release reservoir.

    Historical feedback implicit in the starting concentration is excluded by initializing the
    commitment target at the first model temperature. New commitment arises only when the RUNNING
    peak temperature increases. The committed pool then releases with a finite e-folding time.
    The methane-equivalent branch is carried separately as a forcing-side proxy and never added
    to atmospheric CO2 mass in the default model.
    """
    if not temp_rows:
        return {"co2_release_by_year": {}, "methane_equiv_release_by_year": {}, "rows": []}
    first_t = float(temp_rows[0]["surface_warming_c"])
    running_peak = first_t
    prev_commit_c = assumptions.carbon_feedback_pgc_per_c * max(0.0, first_t - assumptions.activation_warming_c)
    prev_commit_m = assumptions.methane_feedback_pgc_equiv_per_c * max(0.0, first_t - assumptions.activation_warming_c)
    pool_c = 0.0
    pool_m = 0.0
    f = 1.0 - math.exp(-1.0 / max(1e-9, assumptions.thaw_release_tau_yr))
    rows=[]; co2={}; methane={}
    for rec in temp_rows:
        year=int(rec["year"]); t=float(rec["surface_warming_c"])
        running_peak=max(running_peak,t)
        target_c=assumptions.carbon_feedback_pgc_per_c*max(0.0,running_peak-assumptions.activation_warming_c)
        target_m=assumptions.methane_feedback_pgc_equiv_per_c*max(0.0,running_peak-assumptions.activation_warming_c)
        new_c=max(0.0,target_c-prev_commit_c); new_m=max(0.0,target_m-prev_commit_m)
        # Add new commitment before releasing this year's fraction, preserving mass exactly.
        pool_c += new_c; pool_m += new_m
        release_c_pgc = pool_c*f; release_m_pgc_eq = pool_m*f
        pool_c -= release_c_pgc; pool_m -= release_m_pgc_eq
        co2_gt = release_c_pgc * CO2_GTC_TO_GTCO2
        meth_gtco2e = release_m_pgc_eq * CO2_GTC_TO_GTCO2
        co2[year]=co2_gt; methane[year]=meth_gtco2e
        rows.append({
            "year":year,"surface_warming_c":t,"running_peak_warming_c":running_peak,
            "commitment_target_carbon_pgc":target_c,"new_commitment_carbon_pgc":new_c,
            "unreleased_carbon_pool_pgc":pool_c,"carbon_release_gtco2":co2_gt,
            "commitment_target_methane_pgc_equiv":target_m,"new_commitment_methane_pgc_equiv":new_m,
            "unreleased_methane_pool_pgc_equiv":pool_m,"methane_equiv_release_gtco2e":meth_gtco2e,
            "thaw_release_tau_yr":assumptions.thaw_release_tau_yr,
        })
        prev_commit_c=target_c; prev_commit_m=target_m
    return {"co2_release_by_year":co2,"methane_equiv_release_by_year":methane,"rows":rows,
            "classification":"Causal running-peak commitment target plus lagged 30/50/70-year release reservoir; historical starting-state commitment is not re-injected."}


def dynamic_nonco2_states_v52(
    years: Iterable[int], s: Scenario, land_case: str, assumptions: GasCycleAssumptions,
    mitigation: NonCO2MitigationCase, emissions_override: Optional[Mapping[int,float]]=None,
) -> List[Dict]:
    """One-box gas states plus explicit Version 52 concentration-pathway mitigation axes."""
    rows = dynamic_nonco2_states(years, s, land_case, assumptions, emissions_override)
    out=[]
    for r in rows:
        q=dict(r); year=int(q["year"])
        ch4=float(q["ch4_ppb"]); n2o=float(q["n2o_ppb"])
        if mitigation.ch4_target_2100_ppb is not None:
            ch4_cap=_interp(year,{START_YEAR:CH4_2026_PPB,2100:mitigation.ch4_target_2100_ppb,2400:mitigation.ch4_target_2100_ppb})
            ch4=min(ch4,ch4_cap)
        if mitigation.n2o_target_2100_ppb is not None:
            n2o_cap=_interp(year,{START_YEAR:N2O_2026_PPB,2100:mitigation.n2o_target_2100_ppb,2400:mitigation.n2o_target_2100_ppb})
            n2o=min(n2o,n2o_cap)
        f_ch4=0.036*(math.sqrt(ch4)-math.sqrt(CH4_PI_PPB))
        f_n2o=0.12*(math.sqrt(n2o)-math.sqrt(N2O_PI_PPB))
        total=f_ch4+f_n2o+float(q["aerosol_forcing_w_m2"])+float(q["residual_nonco2_forcing_w_m2"])
        q.update({"ch4_ppb":ch4,"n2o_ppb":n2o,"ch4_forcing_w_m2":f_ch4,"n2o_forcing_w_m2":f_n2o,
                  "nonco2_forcing_w_m2":total,"nonco2_mitigation_case":mitigation.key})
        out.append(q)
    return out


def methane_equiv_forcing_proxy_v52(
    methane_release_gtco2e_by_year: Mapping[int,float], years: Sequence[int], lifetime_yr: float=11.8
) -> Dict[int,float]:
    """Forcing-side CO2e proxy for permafrost methane-equivalent release.

    This is intentionally NOT an atmospheric CH4 chemistry calculation. The PgC-equivalent
    inherited sensitivity is converted to an atmospheric CO2-equivalent burden, given a
    methane-like decay lifetime, and translated with the Myhre CO2 forcing expression. It is
    reported separately so it cannot be mistaken for measured or fully modeled methane forcing.
    """
    burden_gtco2e=0.0; out={}
    decay=math.exp(-1.0/max(1e-9,lifetime_yr))
    gtco2_per_ppm=CO2_MASS_GTC_PER_PPM*CO2_GTC_TO_GTCO2
    for y in years:
        burden_gtco2e*=decay
        burden_gtco2e+=float(methane_release_gtco2e_by_year.get(y,0.0))
        eq_ppm=burden_gtco2e/gtco2_per_ppm
        out[y]=MYHRE_ALPHA*math.log((CLIMATE_PREINDUSTRIAL_PPM+eq_ppm)/CLIMATE_PREINDUSTRIAL_PPM) if eq_ppm>0 else 0.0
    return out


def climate_with_dynamic_nonco2_v52(
    co2_rows: Sequence[Mapping], gas_rows: Sequence[Mapping],
    permafrost_methane_equiv_release: Optional[Mapping[int,float]]=None,
    p: ClimateParams = ClimateParams(), methane_equiv_lifetime_yr: float=11.8,
) -> Dict:
    gas={int(r["year"]):r for r in gas_rows}; years=[int(r["year"]) for r in co2_rows]
    pf_forcing=methane_equiv_forcing_proxy_v52(permafrost_methane_equiv_release or {},years,methane_equiv_lifetime_yr)
    init=climate_spinup(p,end_year=START_YEAR-1); t=init["surface_warming_c"]; td=init["deep_ocean_warming_c"]
    rows=[]; peak=t; peak_year=START_YEAR; above15=above20=0; warming_at_target=None
    for rec in co2_rows:
        y=int(rec["year"]); ppm=float(rec["co2_ppm"]); fco2=co2_forcing(ppm)
        fgas=float(gas[y]["nonco2_forcing_w_m2"]); fpf=float(pf_forcing.get(y,0.0)); f=fco2+fgas+fpf
        t,td,imb,heat=_climate_step(t,td,f,p)
        if t>peak: peak=t;peak_year=y
        above15+=int(t>1.5);above20+=int(t>2.0)
        if warming_at_target is None and ppm<=TARGET_CO2_PPM: warming_at_target=t
        rows.append({"year":y,"co2_ppm":ppm,"co2_forcing_w_m2":fco2,"nonco2_forcing_w_m2":fgas,
                     "permafrost_methane_forcing_proxy_w_m2":fpf,"total_forcing_w_m2":f,
                     "surface_warming_c":t,"deep_ocean_warming_c":td,"earth_energy_imbalance_w_m2":imb,
                     "ocean_heat_uptake_w_m2":heat,"ch4_ppb":gas[y]["ch4_ppb"],"n2o_ppb":gas[y]["n2o_ppb"],
                     "aerosol_forcing_w_m2":gas[y]["aerosol_forcing_w_m2"]})
    return {"peak_warming_c":peak,"peak_year":peak_year,"years_above_1p5":above15,"years_above_2p0":above20,
            "warming_at_co2_target_c":warming_at_target,"rows":rows,
            "permafrost_methane_treatment":"forcing-side CO2e proxy with methane-like decay; not an atmospheric CH4 chemistry model"}


def durable_carbon_cycle_v52(
    s: Scenario, land_case: str, temperature_driver: Mapping[int,float], permafrost_source_gtco2: Mapping[int,float],
    controller: RestorationControllerAssumptions, maintain_after_target_years: int=30,
) -> Dict:
    """V52 durable-carbon cycle with a 279.5-280.5 ppm operating band.

    Drawdown is not artificially slowed decades before restoration. The rate limit governs normal
    maintenance adjustments; a transparent boundary-safety override is permitted when the clipped
    command would otherwise leave the band. This removes the audited one-year maintenance spike without
    pretending a hard 0.5-Gt/yr^2 ramp can simultaneously satisfy an exact atmospheric boundary.
    """
    init=initialize_carbon_state(START_CO2_PPM,s.observed_natural_sink_gtc_yr);state=list(init["state_gtc"])
    stocks={p:0.0 for p in PATHWAY_STORAGE};rows=[];pathway_rows=[]
    peak_ppm=START_CO2_PPM;peak_year=START_YEAR;crossing=None;band_entry=None;maintenance_years=0
    cum_cdr=cum_rev=cum_pf=0.0;shortfalls=[];prev_actual=0.0;ramp_overrides=[]
    lower=controller.target_ppm-controller.band_half_width_ppm;upper=controller.target_ppm+controller.band_half_width_ppm
    for year in range(START_YEAR,s.end_year+1):
        warming=float(temperature_driver.get(year,temperature_driver.get(year-1,1.37)));emissions=float(gross_emissions_path(year,s));pf=float(permafrost_source_gtco2.get(year,0.0))
        plan=effective_cdr_path(year,s,land_case);feasible_map={r["pathway"]:float(r["cdr_gtco2_yr"]) for r in plan["rows"]};feasible=sum(feasible_map.values())
        reversals={};after={}
        for pathway,stock in stocks.items():
            cfg=PATHWAY_STORAGE[pathway];rate=cfg.annual_reversal_fraction*_climate_reversal_multiplier(pathway,warming);rev=min(stock,max(0.0,stock*rate));reversals[pathway]=rev;after[pathway]=stock-rev
        rev_total=sum(reversals.values());current_ppm=PREINDUSTRIAL_CO2_PPM+sum(state)/CO2_MASS_GTC_PER_PPM;ramp_override=False
        if current_ppm>upper:
            requested=feasible;controller_mode="full_drawdown"
            test_state,_=_advance_reservoirs(list(state),emissions+pf+rev_total-requested);test_ppm=PREINDUSTRIAL_CO2_PPM+sum(test_state)/CO2_MASS_GTC_PER_PPM
            if test_ppm<upper:
                net_b=_required_net_flux_for_target(state,upper);requested=max(0.0,min(feasible,emissions+pf+rev_total-net_b));ramp_override=True;controller_mode="band_entry_boundary_override";ramp_overrides.append(year)
        else:
            net_mid=_required_net_flux_for_target(state,controller.target_ppm);desired=max(0.0,min(feasible,emissions+pf+rev_total-net_mid))
            candidate=min(feasible,max(0.0,_move_toward(prev_actual,desired,controller.cdr_ramp_limit_gtco2_yr2)))
            test_state,_=_advance_reservoirs(list(state),emissions+pf+rev_total-candidate);test_ppm=PREINDUSTRIAL_CO2_PPM+sum(test_state)/CO2_MASS_GTC_PER_PPM
            requested=candidate;controller_mode="band_hold_rate_limited"
            if test_ppm<lower:
                net_b=_required_net_flux_for_target(state,lower);requested=max(0.0,min(feasible,emissions+pf+rev_total-net_b));ramp_override=True;controller_mode="band_lower_boundary_override"
            elif test_ppm>upper:
                net_b=_required_net_flux_for_target(state,upper);requested=max(0.0,min(feasible,emissions+pf+rev_total-net_b));ramp_override=True;controller_mode="band_upper_boundary_override"
            if ramp_override:ramp_overrides.append(year)
        scale=min(1.0,requested/feasible) if feasible>0 else 0.0;proposed={p:feasible_map.get(p,0.0)*scale for p in PATHWAY_STORAGE};actual={};sat_short=0.0
        for pathway,amount in proposed.items():
            cfg=PATHWAY_STORAGE[pathway];accepted=amount if cfg.stock_capacity_gtco2 is None else min(amount,max(0.0,cfg.stock_capacity_gtco2-after[pathway]));actual[pathway]=accepted;sat_short+=max(0.0,amount-accepted);stocks[pathway]=after[pathway]+accepted
        actual_total=sum(actual.values());prev_actual=actual_total;net=emissions+pf+rev_total-actual_total;state,sink=_advance_reservoirs(state,net);ppm=PREINDUSTRIAL_CO2_PPM+sum(state)/CO2_MASS_GTC_PER_PPM
        if band_entry is None and lower<=ppm<=upper:band_entry=year
        if crossing is None:cum_cdr+=actual_total;cum_rev+=rev_total;cum_pf+=pf
        if ppm>peak_ppm:peak_ppm=ppm;peak_year=year
        if crossing is None and ppm<=controller.target_ppm:crossing=year
        active=band_entry is not None
        if active:maintenance_years+=1
        if active and actual_total+1e-9<requested:shortfalls.append(year)
        rows.append({"year":year,"phase":"target_band" if active else "drawdown","controller_mode":controller_mode,"controller_ramp_override":ramp_override,
                     "gross_emissions_gtco2":emissions,"permafrost_source_gtco2":pf,"stored_carbon_reversal_gtco2":rev_total,"planned_incremental_cdr_gtco2":float(plan["planned_cdr_gtco2_yr"]),
                     "feasible_incremental_cdr_gtco2":feasible,"requested_incremental_cdr_gtco2":requested,"actual_incremental_cdr_gtco2":actual_total,"saturation_shortfall_gtco2":sat_short,
                     "net_anthropogenic_gtco2":net,"natural_reservoir_flux_to_sinks_gtc":sink,"co2_ppm":ppm,"total_stored_carbon_stock_gtco2":sum(stocks.values()),
                     "biological_restoration_stock_gtco2":stocks["Biological restoration"],"biochar_stock_gtco2":stocks["Biochar"],"land_binding":bool(plan["land_nexus"]["binding"]),
                     "surface_warming_driver_c":warming,"target_band_lower_ppm":lower,"target_band_upper_ppm":upper})
        for pathway in PATHWAY_STORAGE:
            pathway_rows.append({"year":year,"pathway":pathway,"new_storage_gtco2":actual[pathway],"reversal_gtco2":reversals[pathway],"stock_gtco2":stocks[pathway],
                                 "annual_reversal_fraction":PATHWAY_STORAGE[pathway].annual_reversal_fraction,"climate_reversal_multiplier":_climate_reversal_multiplier(pathway,warming),"stock_capacity_gtco2":PATHWAY_STORAGE[pathway].stock_capacity_gtco2})
        if active and maintenance_years>=maintain_after_target_years:break
    return {"model_class":"Joos four-reservoir + storage/reversal + lagged permafrost + target-band/rate-limited controller with explicit safety overrides",
            "scenario":asdict(s),"land_case":land_case,"initialization":init,"peak_co2_ppm":peak_ppm,"peak_year":peak_year,"crossing_year":crossing,"target_band_entry_year":band_entry,
            "cumulative_incremental_cdr_to_target_gtco2":cum_cdr,"cumulative_reversal_to_target_gtco2":cum_rev,"cumulative_permafrost_to_target_gtco2":cum_pf,
            "stock_at_end_gtco2":sum(stocks.values()),"pathway_stock_at_end_gtco2":dict(stocks),"maintenance_shortfall_years":shortfalls,"target_held":not shortfalls if band_entry is not None else None,
            "controller_ramp_override_years":ramp_overrides,"controller_assumptions":asdict(controller),"rows":rows,"pathway_rows":pathway_rows}


def avoided_damage_screen_v52(restoration_rows: Sequence[Mapping], noaction_rows: Sequence[Mapping],
                               gdp_case_key: str, assumptions: DamageAssumptions) -> Dict:
    restoration={int(r["year"]):r for r in restoration_rows}; noaction={int(r["year"]):r for r in noaction_rows}
    common=sorted(set(restoration)&set(noaction)); gdp=gdp_series_v52(max(common),gdp_case_key)
    cases={"low_2pct_at_3c":assumptions.low_damage_at_3c_fraction_gdp,"central_5pct_at_3c":assumptions.central_damage_at_3c_fraction_gdp,
           "high_15pct_at_3c":assumptions.high_damage_at_3c_fraction_gdp}; cumul={k:0.0 for k in cases}; rows=[]
    for y in common:
        row={"year":y,"gdp_screen_usd_tn":gdp[y],"restoration_warming_c":float(restoration[y]["surface_warming_c"]),
             "no_action_warming_c":float(noaction[y]["surface_warming_c"])}
        for key,at3 in cases.items():
            dr=damage_fraction(row["restoration_warming_c"],at3,assumptions.reference_warming_c)
            dn=damage_fraction(row["no_action_warming_c"],at3,assumptions.reference_warming_c)
            avoided=(dn-dr)*gdp[y]  # C1: symmetric, negative during aerosol-unmasking window.
            cumul[key]+=avoided
            row[f"restoration_damage_fraction_{key}"]=dr;row[f"no_action_damage_fraction_{key}"]=dn
            row[f"avoided_damage_usd_tn_{key}"]=avoided;row[f"cumulative_avoided_damage_usd_tn_{key}"]=cumul[key]
        rows.append(row)
    return {"classification":"Symmetric illustrative damage screen; negative avoided damages are retained. Not an IAM welfare result.",
            "gdp_case":gdp_case_key,"gdp_assumptions":asdict(GDP_CASES[gdp_case_key]),
            "cumulative_avoided_damage_usd_tn":cumul,"rows":rows}


def annual_cdr_cost_rows_v52(carbon: Dict, s: Scenario, land_case: str, dac_cost_override_usd_t: Optional[float]=None) -> List[Dict]:
    actual_by_year=defaultdict(dict)
    for r in carbon["pathway_rows"]: actual_by_year[int(r["year"])][r["pathway"]]=float(r["new_storage_gtco2"])
    cumulative={k:a.initial_cumulative_gt for k,a in DEFAULT_LEARNING.items()}; rows=[]
    for cr in carbon["rows"]:
        y=int(cr["year"]); p=effective_cdr_path(y,s,land_case); feasible=max(1e-12,float(cr["feasible_incremental_cdr_gtco2"]))
        scale=float(cr["actual_incremental_cdr_gtco2"])/feasible if feasible>0 else 0.0
        util={r["pathway"]:float(r.get("resource_utilization_fraction",0.0))*scale for r in p["rows"]}
        econ=pathway_economics(cumulative,util); total=0.0;detail=[]
        for name in PATHWAY_STORAGE:
            amt=float(actual_by_year[y].get(name,0.0)); cost=float(econ[name]["marginal_cost_usd_t"])
            if name=="DACCS" and dac_cost_override_usd_t is not None: cost=float(dac_cost_override_usd_t)
            spend=amt*cost/1000.0;total+=spend;cumulative[name]+=amt
            detail.append({"pathway":name,"actual_cdr_gtco2":amt,"marginal_cost_usd_t":cost,"annual_spend_usd_tn":spend})
        rows.append({"year":y,"advanced_cdr_cost_usd_tn":total,"dac_cost_override_usd_t":dac_cost_override_usd_t,
                     "pathway_detail":detail})
    return rows


def economic_balance_screen_v52(damage: Dict, carbon: Dict, s: Scenario, land_case: str, assumptions: DamageAssumptions,
                                 dac_cost_override_usd_t: Optional[float]=None) -> Dict:
    end=int(carbon["rows"][-1]["year"]); trans=transition_run_case(getattr(s,"transition_case_key","iea_nze_reference"),end)
    trans_by={int(r["year"]):r for r in trans["rows"]}; cdr_cost=annual_cdr_cost_rows_v52(carbon,s,land_case,dac_cost_override_usd_t)
    cdr_by={r["year"]:r for r in cdr_cost}; dmg={int(r["year"]):r for r in damage["rows"]}
    cumul_cost=pv_cost=0.0;cumul_net={k:0.0 for k in ("low_2pct_at_3c","central_5pct_at_3c","high_15pct_at_3c")};pv_net={k:0.0 for k in cumul_net};rows=[]
    for cr in carbon["rows"]:
        y=int(cr["year"]);tc=float(trans_by.get(y,{}).get("transition_investment_usd_tn",0.0) or 0.0);cc=float(cdr_by[y]["advanced_cdr_cost_usd_tn"])
        gross=tc+cc;disc=1/((1+assumptions.real_discount_rate)**(y-START_YEAR));cumul_cost+=gross;pv_cost+=gross*disc
        row={"year":y,"transition_investment_usd_tn":tc,"advanced_cdr_cost_usd_tn":cc,"gross_programme_cost_usd_tn":gross,
             "cumulative_gross_programme_cost_usd_tn":cumul_cost,"pv_gross_programme_cost_usd_tn":pv_cost,
             "dac_cost_override_usd_t":dac_cost_override_usd_t}
        for key in cumul_net:
            b=float(dmg.get(y,{}).get(f"avoided_damage_usd_tn_{key}",0.0));net=b-gross;cumul_net[key]+=net;pv_net[key]+=net*disc
            row[f"avoided_damage_usd_tn_{key}"]=b;row[f"net_benefit_usd_tn_{key}"]=net
            row[f"cumulative_net_benefit_usd_tn_{key}"]=cumul_net[key];row[f"pv_cumulative_net_benefit_usd_tn_{key}"]=pv_net[key]
        rows.append(row)
    def snap(y):
        z=[r for r in rows if r["year"]<=y];return z[-1] if z else None
    be=None
    for i,r in enumerate(rows):
        if r["cumulative_net_benefit_usd_tn_central_5pct_at_3c"]>=0 and all(x["cumulative_net_benefit_usd_tn_central_5pct_at_3c"]>=0 for x in rows[i:]):be=r["year"];break
    target=carbon.get("crossing_year") or carbon.get("target_band_entry_year") or int(carbon["rows"][-1]["year"])
    return {"classification":"Incremental transition conversion + actual CDR cost versus symmetric avoided-damage screen; PV reported with every long-horizon total.",
            "discount_rate_real":assumptions.real_discount_rate,"sustained_cumulative_break_even_year_central":be,
            "through_2100":snap(2100),"at_280":snap(target),"full_horizon":rows[-1] if rows else None,"rows":rows}


def sources_and_uses_ledger_v52(economics: Dict, damage: Dict, gdp_case_key: str,
                                assumptions: FinancingAssumptionsV52=FinancingAssumptionsV52()) -> Dict:
    end=economics["rows"][-1]["year"];gdp=gdp_series_v52(end,gdp_case_key);case=SETTLEMENT_COLLECTION_CASES[0]
    rows=[];debt=0.0;max_req_share=[]
    for e in economics["rows"]:
        y=int(e["year"]);transition=float(e["transition_investment_usd_tn"]);cdr=float(e["advanced_cdr_cost_usd_tn"])
        private_transition=transition*(1-assumptions.transition_public_share);public_transition=transition*assumptions.transition_public_share
        public_cdr=cdr*assumptions.cdr_public_share;ordinary_private_replacement=0.0
        policy_cap=gdp[y]*assumptions.settlement_envelope_fraction_gdp;network=settlement_maximum_collection(gdp[y],case)["max_collection_usd_tn"]
        receipts=min(policy_cap,network)
        # Bridge debt is a financing stock, not free capital. Interest capitalizes first;
        # current receipts then cover current public uses, and any surplus repays debt.
        interest=debt*assumptions.bridge_real_interest_rate
        debt += interest
        current_public_uses=public_transition+public_cdr
        bridge_draw=max(0.0,current_public_uses-receipts);debt += bridge_draw
        surplus_before_repay=max(0.0,receipts-current_public_uses)
        repay=min(debt,surplus_before_repay);debt-=repay;residual=max(0.0,surplus_before_repay-repay)
        allowed_share=(receipts-public_cdr)/transition if transition>1e-12 else math.inf
        max_req_share.append(allowed_share)
        rows.append({"year":y,"gdp_usd_tn":gdp[y],"private_transition_capital_usd_tn":private_transition,
                     "public_transition_contribution_usd_tn":public_transition,"cdr_funding_public_usd_tn":public_cdr,
                     "cdr_public_share":assumptions.cdr_public_share,"settlement_receipts_usd_tn":receipts,
                     "settlement_policy_cap_usd_tn":policy_cap,"settlement_network_capacity_usd_tn":network,
                     "ordinary_private_replacement_capital_usd_tn":ordinary_private_replacement,
                     "bridge_interest_usd_tn":interest,"bridge_draw_usd_tn":bridge_draw,"bridge_repayment_usd_tn":repay,
                     "bridge_debt_stock_usd_tn":debt,"residual_public_surplus_usd_tn":residual,
                     "public_requirement_before_debt_usd_tn":public_transition+public_cdr,
                     "public_requirement_fraction_gdp":(public_transition+public_cdr)/gdp[y]})
    finite=[x for x in max_req_share if math.isfinite(x)];threshold=max(0.0,min(finite)) if finite else 1.0
    sweep=[];x=assumptions.public_share_sweep_low
    while x<=assumptions.public_share_sweep_high+1e-12:
        breach=[]
        for r,e in zip(rows,economics["rows"]):
            req=float(e["transition_investment_usd_tn"])*x+float(e["advanced_cdr_cost_usd_tn"])*assumptions.cdr_public_share
            if req>r["settlement_receipts_usd_tn"]+1e-12:breach.append(r["year"])
        sweep.append({"transition_public_share":round(x,4),"breach":bool(breach),"first_breach_year":breach[0] if breach else None,
                      "breach_year_count":len(breach)});x+=assumptions.public_share_sweep_step
    first_fail=next((r for r in sweep if r["breach"]),None)
    peak_debt=max(rows,key=lambda r:r["bridge_debt_stock_usd_tn"]) if rows else {}
    return {"classification":"Annual public/private Sources & Uses ledger. Private transition capital is an explicit financing assumption; bridge debt is used only when public uses exceed settlement receipts, with real interest capitalized and later surpluses used for repayment.",
            "assumptions":asdict(assumptions),"public_share_analytical_failure_threshold":threshold,
            "public_share_sweep_first_failure":first_fail,"public_share_sweep":sweep,"ending_bridge_debt_usd_tn":debt,
            "peak_bridge_debt_usd_tn":peak_debt.get("bridge_debt_stock_usd_tn",0.0),"peak_bridge_debt_year":peak_debt.get("year"),
            "total_bridge_interest_usd_tn":sum(r["bridge_interest_usd_tn"] for r in rows),
            "total_bridge_draw_usd_tn":sum(r["bridge_draw_usd_tn"] for r in rows),"rows":rows}


def apply_financing_costs_to_economics_v52(economics: Dict, ledger: Dict, carbon: Dict, discount_rate: float=0.02) -> Dict:
    """Charge bridge-debt interest to the economic ledger as required by C2.

    Principal is financing of costs already counted and is not counted again. Interest is the
    incremental financing charge. The public/private split does not alter real programme cost.
    """
    led={int(r["year"]):r for r in ledger["rows"]};rows=[];cum_add=0.0;pv_add=0.0
    for base in economics["rows"]:
        y=int(base["year"]);q=dict(base);interest=float(led[y]["bridge_interest_usd_tn"]);disc=1/((1+discount_rate)**(y-START_YEAR))
        cum_add+=interest;pv_add+=interest*disc
        q["bridge_financing_interest_usd_tn"]=interest
        q["gross_programme_cost_usd_tn"]+=interest;q["cumulative_gross_programme_cost_usd_tn"]+=cum_add;q["pv_gross_programme_cost_usd_tn"]+=pv_add
        for key in ("low_2pct_at_3c","central_5pct_at_3c","high_15pct_at_3c"):
            q[f"net_benefit_usd_tn_{key}"]-=interest;q[f"cumulative_net_benefit_usd_tn_{key}"]-=cum_add;q[f"pv_cumulative_net_benefit_usd_tn_{key}"]-=pv_add
        rows.append(q)
    def snap(y):
        z=[r for r in rows if r["year"]<=y];return z[-1] if z else None
    be=None
    for i,r in enumerate(rows):
        if r["cumulative_net_benefit_usd_tn_central_5pct_at_3c"]>=0 and all(x["cumulative_net_benefit_usd_tn_central_5pct_at_3c"]>=0 for x in rows[i:]):be=r["year"];break
    target=carbon.get("crossing_year") or carbon.get("target_band_entry_year") or rows[-1]["year"]
    out=dict(economics);out.update({"classification":economics["classification"]+" Bridge-debt interest is additionally charged; principal is not double counted.",
                                    "sustained_cumulative_break_even_year_central":be,"through_2100":snap(2100),"at_280":snap(target),
                                    "full_horizon":rows[-1] if rows else None,"rows":rows,"total_bridge_interest_usd_tn":cum_add})
    return out


def social_dividend_screen_v52(ledger: Dict, economics: Dict, carbon: Dict,
                               assumptions: SocialDividendAssumptionsV52=SocialDividendAssumptionsV52()) -> Dict:
    alloc=assumptions.allocations()
    if abs(sum(alloc.values())-1.0)>1e-9:raise ValueError("social dividend allocations must sum to one")
    # Start only after the first actual <=280 ppm crossing, not merely first entry into the operating band.
    band_entry=carbon.get("crossing_year");econ={int(r["year"]):r for r in economics["rows"]}
    led={int(r["year"]):r for r in ledger["rows"]};rows=[];reserve=0.0;cumulative=0.0;pv=0.0;cumul_alloc={k:0.0 for k in alloc}
    post_costs=[float(econ[y]["gross_programme_cost_usd_tn"]) for y in sorted(econ) if band_entry and y>=band_entry][:10]
    reserve_target=assumptions.maintenance_reserve_years*(max(post_costs) if post_costs else 0.0)
    for y in sorted(econ):
        active=band_entry is not None and y>=band_entry;gross_headroom=float(led[y]["residual_public_surplus_usd_tn"]) if active else 0.0
        reserve_contrib=min(gross_headroom,max(0.0,reserve_target-reserve));reserve+=reserve_contrib
        distributable=max(0.0,gross_headroom-reserve_contrib)
        cumulative+=distributable;disc=1/((1+assumptions.real_discount_rate)**(y-START_YEAR));pv+=distributable*disc
        row={"year":y,"post_restoration_active":active,"gross_public_headroom_before_reserve_usd_tn":gross_headroom,
             "maintenance_reserve_target_usd_tn":reserve_target,"maintenance_reserve_contribution_usd_tn":reserve_contrib,
             "maintenance_reserve_balance_usd_tn":reserve,"annual_allocable_social_dividend_usd_tn":distributable,
             "cumulative_allocable_social_dividend_usd_tn":cumulative,"pv_cumulative_social_dividend_usd_tn":pv}
        for k,f in alloc.items():
            amt=distributable*f;cumul_alloc[k]+=amt;row[k+"_usd_tn"]=amt;row["cumulative_"+k+"_usd_tn"]=cumul_alloc[k]
        rows.append(row)
    post=[r for r in rows if r["post_restoration_active"]];after_reserve=[r for r in post if r["maintenance_reserve_balance_usd_tn"]>=reserve_target-1e-12]
    sample=after_reserve[:assumptions.sustainable_average_years]
    avg=sum(r["annual_allocable_social_dividend_usd_tn"] for r in sample)/len(sample) if sample else None
    return {"classification":"Fiscal policy screen only: continued levy receipts after planetary maintenance and reserve funding. Avoided damages are a separate welfare ledger and are never added to this cash flow.",
            "allocation_fractions":alloc,"target_band_entry_year":band_entry,"maintenance_reserve_target_usd_tn":reserve_target,
            "reserve_fully_funded_year":next((r["year"] for r in post if r["maintenance_reserve_balance_usd_tn"]>=reserve_target-1e-12),None),
            "first_year_gross_headroom_usd_tn":post[0]["gross_public_headroom_before_reserve_usd_tn"] if post else None,
            "first_year_allocable_after_reserve_usd_tn":post[0]["annual_allocable_social_dividend_usd_tn"] if post else None,
            "sustainable_average_years":assumptions.sustainable_average_years,"sustainable_average_after_reserve_usd_tn_yr":avg,
            "cumulative_allocable_usd_tn":cumulative,"pv_cumulative_allocable_usd_tn":pv,"rows":rows}


def _scenario_spec_v52(case_key: str) -> Tuple[Scenario,str,str]:
    if case_key=="accelerated":
        return Scenario(name="Accelerated Planetary Restoration Design",cdr_mode="accelerated"),"central","Accelerated Planetary Restoration Design"
    if case_key=="evidence":
        return Scenario(name="Evidence-Anchored Deployment Case",cdr_mode="evidence_benchmark"),"central","Evidence-Anchored Deployment Case"
    if case_key=="constraint":
        return Scenario(name="Constraint-Binding Stress Case",cdr_mode="accelerated"),"low_efficiency","Constraint-Binding Stress Case"
    raise KeyError(case_key)


def run_v52_case(case_key: str="accelerated", gdp_case_key: str="central", nonco2_case_key: str="baseline",
                 permafrost_tau_yr: float=50.0, dac_cost_override_usd_t: Optional[float]=None,
                 assumptions: V52Assumptions=V52Assumptions()) -> Dict:
    s,land_case,label=_scenario_spec_v52(case_key)
    if nonco2_case_key not in NONCO2_MITIGATION_CASES:raise KeyError(nonco2_case_key)
    mitigation=NONCO2_MITIGATION_CASES[nonco2_case_key]
    pfass=replace(assumptions.permafrost,thaw_release_tau_yr=permafrost_tau_yr)
    # Initial driver: audit-corrected global-mean climate. Fixed point then closes lagged permafrost + non-CO2 forcing.
    legacy=carbon_cycle(s,land_case,maintain_after_target_years=assumptions.maintenance_after_target_years)
    legacy_cl=climate_run(legacy["rows"]);temp=_temperature_by_year(legacy_cl["rows"]);history=[]
    carbon=climate=gases=pf=None
    for iteration in range(assumptions.coupling_iterations):
        driver=[{"year":y,"surface_warming_c":t} for y,t in sorted(temp.items())]
        pf=permafrost_feedback_v52(driver,pfass)
        carbon=durable_carbon_cycle_v52(s,land_case,temp,pf["co2_release_by_year"],assumptions.controller,assumptions.maintenance_after_target_years)
        years=[int(r["year"]) for r in carbon["rows"]]
        gases=dynamic_nonco2_states_v52(years,s,land_case,assumptions.gas,mitigation)
        climate=climate_with_dynamic_nonco2_v52(carbon["rows"],gases,pf["methane_equiv_release_by_year"],methane_equiv_lifetime_yr=pfass.methane_equivalent_lifetime_yr)
        new=_temperature_by_year(climate["rows"]);ov=sorted(set(temp)&set(new));delta=max((abs(new[y]-temp[y]) for y in ov),default=0.0)
        history.append({"iteration":iteration+1,"max_temperature_change_c":delta,"target_band_entry_year":carbon["target_band_entry_year"],
                        "first_below_280_year":carbon["crossing_year"],"peak_warming_c":climate["peak_warming_c"]});temp=new
    assert carbon and climate and gases and pf
    ocean=ocean_surface_state(carbon["rows"],carbon["pathway_rows"],assumptions.ocean)
    end=int(carbon["rows"][-1]["year"]);no_emis={y:no_action_emissions(y) for y in range(START_YEAR,end+1)};no_pf={};no_cl=None;no_carbon=None;no_gases=None
    for _ in range(assumptions.coupling_iterations):
        no_carbon=carbon_cycle_from_emissions(no_emis,end,{y:float(no_pf.get(y,0.0)) for y in range(START_YEAR,end+1)})
        no_gases=dynamic_nonco2_states_v52(range(START_YEAR,end+1),s,land_case,assumptions.gas,mitigation,emissions_override=no_emis)
        # Use previous temperature to update lagged feedback. First iteration has zero permafrost.
        pf_pack=permafrost_feedback_v52(no_cl["rows"],pfass) if no_cl else {"co2_release_by_year":{},"methane_equiv_release_by_year":{}}
        no_pf=pf_pack.get("co2_release_by_year",{})
        no_carbon=carbon_cycle_from_emissions(no_emis,end,no_pf)
        no_cl=climate_with_dynamic_nonco2_v52(no_carbon,no_gases,pf_pack.get("methane_equiv_release_by_year",{}),methane_equiv_lifetime_yr=pfass.methane_equivalent_lifetime_yr)
    damages=avoided_damage_screen_v52(climate["rows"],no_cl["rows"],gdp_case_key,assumptions.damage)
    economics_base=economic_balance_screen_v52(damages,carbon,s,land_case,assumptions.damage,dac_cost_override_usd_t)
    ledger=sources_and_uses_ledger_v52(economics_base,damages,gdp_case_key,assumptions.financing)
    economics=apply_financing_costs_to_economics_v52(economics_base,ledger,carbon,assumptions.damage.real_discount_rate)
    social=social_dividend_screen_v52(ledger,economics,carbon,assumptions.social_dividend)
    electricity=mature_electricity_screen(s,land_case);minerals=critical_minerals_screen(electricity["total_twh_yr"],assumptions.minerals);workforce=workforce_screen(electricity,s,land_case,assumptions.workforce)
    phfirst=ocean[0]["surface_ocean_ph"] if ocean else None;phtarget=next((r["surface_ocean_ph"] for r in ocean if r["atmospheric_pco2_ppm"]<=280.0),None)
    c2100=next((r for r in climate["rows"] if r["year"]==2100),None);n2100=next((r for r in no_cl["rows"] if r["year"]==2100),None)
    h={"scenario_key":case_key,"scenario_label":label,"gdp_case":gdp_case_key,"nonco2_case":nonco2_case_key,"permafrost_tau_yr":permafrost_tau_yr,
       "peak_co2_ppm":carbon["peak_co2_ppm"],"peak_co2_year":carbon["peak_year"],"target_band_entry_year":carbon["target_band_entry_year"],
       "first_below_280_year":carbon["crossing_year"],"cumulative_cdr_to_target_gtco2":carbon["cumulative_incremental_cdr_to_target_gtco2"],
       "cumulative_reversal_to_target_gtco2":carbon["cumulative_reversal_to_target_gtco2"],"cumulative_permafrost_to_target_gtco2":carbon["cumulative_permafrost_to_target_gtco2"],
       "peak_warming_c":climate["peak_warming_c"],"peak_warming_year":climate["peak_year"],"warming_at_280_c":climate["warming_at_co2_target_c"],
       "surface_ocean_ph_first_state":phfirst,"surface_ocean_ph_at_or_below_280":phtarget,
       "restoration_warming_2100_c":c2100["surface_warming_c"] if c2100 else None,"no_action_warming_2100_c":n2100["surface_warming_c"] if n2100 else None,
       "cumulative_avoided_damage_central_usd_tn":damages["cumulative_avoided_damage_usd_tn"]["central_5pct_at_3c"],
       "net_benefit_through_2100_usd_tn":economics["through_2100"]["cumulative_net_benefit_usd_tn_central_5pct_at_3c"],
       "pv_net_benefit_through_2100_usd_tn":economics["through_2100"]["pv_cumulative_net_benefit_usd_tn_central_5pct_at_3c"],
       "sustained_break_even_year":economics["sustained_cumulative_break_even_year_central"],
       "net_benefit_at_280_usd_tn":economics["at_280"]["cumulative_net_benefit_usd_tn_central_5pct_at_3c"] if economics["at_280"] else None,
       "pv_net_benefit_at_280_usd_tn":economics["at_280"]["pv_cumulative_net_benefit_usd_tn_central_5pct_at_3c"] if economics["at_280"] else None,
       "full_horizon_net_benefit_usd_tn":economics["full_horizon"]["cumulative_net_benefit_usd_tn_central_5pct_at_3c"],
       "full_horizon_pv_net_benefit_usd_tn":economics["full_horizon"]["pv_cumulative_net_benefit_usd_tn_central_5pct_at_3c"],
       "public_transition_share_failure_threshold":ledger["public_share_analytical_failure_threshold"],
       "public_share_sweep_first_failure":ledger["public_share_sweep_first_failure"],
       "peak_bridge_debt_usd_tn":ledger["peak_bridge_debt_usd_tn"],"peak_bridge_debt_year":ledger["peak_bridge_debt_year"],
       "total_bridge_interest_usd_tn":ledger["total_bridge_interest_usd_tn"],"ending_bridge_debt_usd_tn":ledger["ending_bridge_debt_usd_tn"],
       "social_dividend_first_year_gross_headroom_usd_tn":social["first_year_gross_headroom_usd_tn"],
       "social_dividend_reserve_fully_funded_year":social["reserve_fully_funded_year"],
       "social_dividend_sustainable_average_usd_tn_yr":social["sustainable_average_after_reserve_usd_tn_yr"],
       "social_dividend_cumulative_usd_tn":social["cumulative_allocable_usd_tn"],"social_dividend_pv_usd_tn":social["pv_cumulative_allocable_usd_tn"],
       "mature_electricity_twh_yr":electricity["total_twh_yr"],"external_pre_cdr_electricity_twh_yr":electricity["pre_cdr_twh_yr"],
       "battery_storage_screen_twh":minerals["battery_storage_twh"],"copper_mt_buildout_screen":minerals["copper_mt_buildout"],
       "lithium_mt_buildout_screen":minerals["lithium_mt_buildout"],"mature_workforce_fte_screen":workforce["mature_ongoing_plus_annualized_build_fte"]}
    return {"model_version":V52_MODEL_VERSION,"release_label":V52_RELEASE_LABEL,
            "classification":"Coupled global restoration screening model with mutually binding physical and financing screens; not a full Earth-system/IAM forecast.",
            "headline":h,"scenario":asdict(s),"land_case":land_case,"gdp_case":asdict(GDP_CASES[gdp_case_key]),"nonco2_case":asdict(mitigation),
            "permafrost_assumptions":asdict(pfass),"controller_assumptions":asdict(assumptions.controller),"coupling_convergence":history,
            "durable_carbon":carbon,"permafrost_feedback":pf,"nonco2_states":gases,"climate":climate,"ocean_surface":ocean,
            "no_action":{"carbon":no_carbon,"nonco2_states":no_gases,"climate":no_cl},"avoided_damages":damages,"economic_balance":economics,
            "sources_and_uses":ledger,"post_restoration_social_dividend":social,"critical_minerals":minerals,"workforce":workforce,
            "electricity":electricity}


def annual_state_v52(result: Dict) -> List[Dict]:
    """Single immutable annual state from which every annual CSV is projected (C11)."""
    maps={
        "carbon":{int(r["year"]):r for r in result["durable_carbon"]["rows"]},
        "pf":{int(r["year"]):r for r in result["permafrost_feedback"]["rows"]},
        "gas":{int(r["year"]):r for r in result["nonco2_states"]},
        "clim":{int(r["year"]):r for r in result["climate"]["rows"]},
        "ocean":{int(r["year"]):r for r in result["ocean_surface"]},
        "damage":{int(r["year"]):r for r in result["avoided_damages"]["rows"]},
        "econ":{int(r["year"]):r for r in result["economic_balance"]["rows"]},
        "ledger":{int(r["year"]):r for r in result["sources_and_uses"]["rows"]},
        "social":{int(r["year"]):r for r in result["post_restoration_social_dividend"]["rows"]},
    }
    years=sorted(maps["carbon"]);out=[]
    for y in years:
        c=maps["carbon"][y];p=maps["pf"].get(y,{});g=maps["gas"].get(y,{});cl=maps["clim"].get(y,{});o=maps["ocean"].get(y,{})
        d=maps["damage"].get(y,{});e=maps["econ"].get(y,{});l=maps["ledger"].get(y,{});s=maps["social"].get(y,{})
        out.append({"year":y,"co2_ppm":c.get("co2_ppm"),"gross_emissions_gtco2":c.get("gross_emissions_gtco2"),
                    "actual_cdr_gtco2":c.get("actual_incremental_cdr_gtco2"),"reversal_gtco2":c.get("stored_carbon_reversal_gtco2"),
                    "permafrost_co2_gtco2":c.get("permafrost_source_gtco2"),"permafrost_methane_equiv_gtco2e":p.get("methane_equiv_release_gtco2e",0.0),
                    "stored_carbon_stock_gtco2":c.get("total_stored_carbon_stock_gtco2"),"land_binding":c.get("land_binding"),
                    "surface_warming_c":cl.get("surface_warming_c"),"deep_ocean_warming_c":cl.get("deep_ocean_warming_c"),
                    "ch4_ppb":g.get("ch4_ppb"),"n2o_ppb":g.get("n2o_ppb"),"co2_forcing_w_m2":cl.get("co2_forcing_w_m2"),
                    "nonco2_forcing_w_m2":cl.get("nonco2_forcing_w_m2"),"permafrost_methane_forcing_proxy_w_m2":cl.get("permafrost_methane_forcing_proxy_w_m2"),
                    "surface_ocean_ph":o.get("surface_ocean_ph"),"total_alkalinity_umol_kg":o.get("total_alkalinity_umol_kg"),
                    "gdp_usd_tn":d.get("gdp_screen_usd_tn"),"avoided_damage_central_usd_tn":d.get("avoided_damage_usd_tn_central_5pct_at_3c"),
                    "gross_programme_cost_usd_tn":e.get("gross_programme_cost_usd_tn"),"cumulative_net_benefit_usd_tn":e.get("cumulative_net_benefit_usd_tn_central_5pct_at_3c"),
                    "pv_cumulative_net_benefit_usd_tn":e.get("pv_cumulative_net_benefit_usd_tn_central_5pct_at_3c"),
                    "settlement_receipts_usd_tn":l.get("settlement_receipts_usd_tn"),"public_requirement_usd_tn":l.get("public_requirement_before_debt_usd_tn"),
                    "bridge_debt_stock_usd_tn":l.get("bridge_debt_stock_usd_tn"),"residual_public_surplus_usd_tn":l.get("residual_public_surplus_usd_tn"),
                    "maintenance_reserve_balance_usd_tn":s.get("maintenance_reserve_balance_usd_tn"),
                    "social_dividend_usd_tn":s.get("annual_allocable_social_dividend_usd_tn")})
    return out


def run_v52_release() -> Dict:
    primary=run_v52_case("accelerated","central","baseline",50.0)
    # C6: three co-equal physical cases.
    cdr_cases=[primary,run_v52_case("evidence","central","baseline",50.0),run_v52_case("constraint","central","baseline",50.0)]
    cdr_summary=[r["headline"] for r in cdr_cases]
    # C4 GDP sensitivity: economics only must be re-derived because GDP changes damages, financing and social headroom.
    gdp_summary=[]
    for key in GDP_CASES:
        rr=primary if key=="central" else run_v52_case("accelerated",key,"baseline",50.0)
        gdp_summary.append(rr["headline"])
    # C8 lagged permafrost timescale sensitivity.
    pf_summary=[]
    for tau in (30.0,50.0,70.0):
        rr=primary if tau==50.0 else run_v52_case("accelerated","central","baseline",tau)
        pf_summary.append(rr["headline"])
    # C7 DACCS fixed-cost stresses.
    dac_summary=[]
    for cost in (250.0,400.0,600.0):
        rr=run_v52_case("accelerated","central","baseline",50.0,cost)
        x=dict(rr["headline"]);x["dac_cost_override_usd_t"]=cost;dac_summary.append(x)
    # C10 explicit independent CH4/N2O axes (3x3 concentration-target matrix).
    gas_summary=[]
    ch4_targets={"baseline":None,"strong":1000.0,"near_pi":750.0};n2o_targets={"baseline":None,"strong":300.0,"near_pi":275.0}
    for ck,ct in ch4_targets.items():
        for nk,nt in n2o_targets.items():
            key=f"matrix_{ck}_{nk}";NONCO2_MITIGATION_CASES[key]=NonCO2MitigationCase(key,f"CH4 {ck} / N2O {nk}",ct,nt)
            rr=primary if (ck=="baseline" and nk=="baseline") else run_v52_case("accelerated","central",key,50.0)
            gas_summary.append({"ch4_case":ck,"n2o_case":nk,**rr["headline"]})
    primary["scenario_matrix"]={"cdr_cases":cdr_summary,"gdp_cases":gdp_summary,"permafrost_tau_cases":pf_summary,
                                "daccs_cost_cases":dac_summary,"nonco2_matrix":gas_summary}
    primary["annual_state"]=annual_state_v52(primary)
    return primary


def write_v52_outputs(result: Dict, root: Path) -> None:
    data=root/"data";data.mkdir(exist_ok=True)
    # Full result is the machine-readable source of truth.
    (data/"planetary_restoration_v52_results.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    annual=result["annual_state"]
    _write_csv(data/"annual_state.csv",annual)
    # Every annual export is projected from the same immutable annual state (C11).
    _write_csv(data/"advanced_carbon_trajectory.csv",[{k:r[k] for k in ("year","co2_ppm","gross_emissions_gtco2","actual_cdr_gtco2","reversal_gtco2","permafrost_co2_gtco2","stored_carbon_stock_gtco2","land_binding")} for r in annual])
    _write_csv(data/"advanced_climate_trajectory.csv",[{k:r[k] for k in ("year","co2_ppm","surface_warming_c","deep_ocean_warming_c","co2_forcing_w_m2","nonco2_forcing_w_m2","permafrost_methane_forcing_proxy_w_m2","ch4_ppb","n2o_ppb")} for r in annual])
    _write_csv(data/"permafrost_feedback.csv",[{k:r[k] for k in ("year","surface_warming_c","permafrost_co2_gtco2","permafrost_methane_equiv_gtco2e","permafrost_methane_forcing_proxy_w_m2")} for r in annual])
    _write_csv(data/"ocean_surface.csv",[{k:r[k] for k in ("year","co2_ppm","surface_ocean_ph","total_alkalinity_umol_kg")} for r in annual])
    _write_csv(data/"avoided_damages.csv",[{k:r[k] for k in ("year","gdp_usd_tn","surface_warming_c","avoided_damage_central_usd_tn")} for r in annual])
    _write_csv(data/"economic_balance.csv",[{k:r[k] for k in ("year","gdp_usd_tn","gross_programme_cost_usd_tn","avoided_damage_central_usd_tn","cumulative_net_benefit_usd_tn","pv_cumulative_net_benefit_usd_tn")} for r in annual])
    _write_csv(data/"sources_and_uses.csv",[{k:r[k] for k in ("year","gdp_usd_tn","settlement_receipts_usd_tn","public_requirement_usd_tn","bridge_debt_stock_usd_tn","residual_public_surplus_usd_tn")} for r in annual])
    _write_csv(data/"post_restoration_social_dividend.csv",[{k:r[k] for k in ("year","maintenance_reserve_balance_usd_tn","social_dividend_usd_tn")} for r in annual])
    _write_csv(data/"stored_carbon_pathways.csv",result["durable_carbon"]["pathway_rows"])
    for name,rows in result["scenario_matrix"].items():_write_csv(data/(name+".csv"),rows)
    # Authoritative headline markdown.
    h=result["headline"];lines=["# Version 52 authoritative headline results","",
        "> Reduced-complexity screening outputs, not validated Earth-system forecasts.","",
        f"- Accelerated-design target-band entry: **{h['target_band_entry_year']}**; first <=280 ppm: **{h['first_below_280_year']}**.",
        f"- Peak CO2: **{h['peak_co2_ppm']:.2f} ppm in {h['peak_co2_year']}**.",
        f"- Peak warming: **{h['peak_warming_c']:.3f} C in {h['peak_warming_year']}**; warming at <=280 ppm: **{h['warming_at_280_c']:.3f} C**.",
        f"- Cumulative CDR to first <=280: **{h['cumulative_cdr_to_target_gtco2']:.1f} GtCO2**; lagged permafrost source: **{h['cumulative_permafrost_to_target_gtco2']:.1f} GtCO2**.",
        f"- Central-GDP net through 2100: **{h['net_benefit_through_2100_usd_tn']:.1f} tn USD**; PV: **{h['pv_net_benefit_through_2100_usd_tn']:.1f} tn USD**.",
        f"- Sustained cumulative break-even: **{h['sustained_break_even_year']}**.",
        f"- Net at <=280: **{h['net_benefit_at_280_usd_tn']:.1f} tn USD**; PV: **{h['pv_net_benefit_at_280_usd_tn']:.1f} tn USD**.",
        f"- Full-horizon net: **{h['full_horizon_net_benefit_usd_tn']:.1f} tn USD**; PV: **{h['full_horizon_pv_net_benefit_usd_tn']:.1f} tn USD**.",
        f"- Public transition-share analytical failure threshold: **{100*h['public_transition_share_failure_threshold']:.1f}%** under the central GDP/collection screen.",
        f"- Post-restoration gross first-year public headroom before reserve: **{h['social_dividend_first_year_gross_headroom_usd_tn']:.2f} tn USD/yr**.",
        f"- Planetary-maintenance reserve fully funded: **{h['social_dividend_reserve_fully_funded_year']}**; sustainable {result['post_restoration_social_dividend']['sustainable_average_years']}-year social-dividend average afterward: **{h['social_dividend_sustainable_average_usd_tn_yr']:.2f} tn USD/yr**.","",
        "## Permanent accounting boundary","",
        "The social dividend is continued levy collection after restoration and reserve funding; it is a policy choice, not wealth created by restoration. Avoided climate damages are a separate welfare ledger and are never added to the fiscal dividend.","",
        f"Mature electricity screen: **{h['mature_electricity_twh_yr']:.0f} TWh/yr**, of which **{h['external_pre_cdr_electricity_twh_yr']:.0f} TWh/yr** is an external pre-CDR energy-system screen.",
    ]
    (data/"HEADLINE_RESULTS_V52.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


def build_v52_workbook(result: Dict, root: Path) -> Path:
    from artifact_tool import Workbook, SpreadsheetFile
    wb=Workbook.create();h=result["headline"]
    sh=wb.worksheets.add("Dashboard");sh.merge_cells("A1:D1");sh.get_range("A1").values=[["Planetary Restoration Model — Version 52"]]
    sh.get_range("A1:D1").format={"fill":"#17365D","font":{"bold":True,"color":"#FFFFFF","size":16},"horizontal_alignment":"center"}
    sh.merge_cells("A3:D3");sh.get_range("A3").values=[["Reconciled reduced-complexity screening release. Three co-equal CDR cases, lagged permafrost, symmetric damages, asymptotic GDP sensitivity, financing ledger, target-band controller and non-CO2 restoration axes."]]
    sh.get_range("A3:D3").format={"fill":"#FFF2CC","font":{"bold":True,"color":"#7F6000"},"wrap_text":True,"row_height":44}
    rows=[["Metric","Value","Unit / status","Interpretation"],
          ["Accelerated target-band entry",h["target_band_entry_year"],"year","279.5-280.5 ppm operating band"],["First <=280 ppm",h["first_below_280_year"],"year","screening milestone, not forecast"],
          ["Peak CO2",h["peak_co2_ppm"],"ppm",f"{h['peak_co2_year']}"],["Peak warming",h["peak_warming_c"],"degC",f"{h['peak_warming_year']}"],
          ["Warming at <=280",h["warming_at_280_c"],"degC","residual dominated by non-CO2 forcing in baseline case"],
          ["Lagged permafrost source to <=280",h["cumulative_permafrost_to_target_gtco2"],"GtCO2","50-year central thaw-release time"],
          ["Net benefit through 2100",h["net_benefit_through_2100_usd_tn"],"USD tn","undiscounted"],["PV net through 2100",h["pv_net_benefit_through_2100_usd_tn"],"USD tn","2% real discount"],
          ["Sustained break-even",h["sustained_break_even_year"],"year","central GDP screen"],["Net at <=280",h["net_benefit_at_280_usd_tn"],"USD tn","undiscounted"],["PV net at <=280",h["pv_net_benefit_at_280_usd_tn"],"USD tn","2% real"],
          ["Full-horizon net",h["full_horizon_net_benefit_usd_tn"],"USD tn","undiscounted"],["Full-horizon PV net",h["full_horizon_pv_net_benefit_usd_tn"],"USD tn","2% real"],
          ["Public-share failure threshold",h["public_transition_share_failure_threshold"],"fraction","analytical central financing threshold"],
          ["First-year gross post-restoration headroom",h["social_dividend_first_year_gross_headroom_usd_tn"],"USD tn/yr","before reserve capitalization"],
          ["Reserve fully funded",h["social_dividend_reserve_fully_funded_year"],"year","5 years of screened maintenance cost"],
          ["Sustainable social-dividend average",h["social_dividend_sustainable_average_usd_tn_yr"],"USD tn/yr","20-year average after reserve funding"],
          ["Mature electricity",h["mature_electricity_twh_yr"],"TWh/yr",f"{h['external_pre_cdr_electricity_twh_yr']:.0f} TWh/yr is external pre-CDR screen"]]
    sh.get_range(f"A5:D{4+len(rows)}").values=rows;sh.get_range("A5:D5").format={"fill":"#D9EAF7","font":{"bold":True}}
    sh.get_range("A:D").format.wrap_text=True
    for c,w in [("A:A",42),("B:B",24),("C:C",22),("D:D",64)]:sh.get_range(c).format.column_width=w
    sh.get_range("B19:B19").format.number_format="0.0%"
    # Scenario matrix
    sm=wb.worksheets.add("Scenario_Matrix");allrows=[]
    for group,items in result["scenario_matrix"].items():
        for x in items:allrows.append({"group":group,**x})
    fields=["group","scenario_label","scenario_key","gdp_case","nonco2_case","permafrost_tau_yr","target_band_entry_year","first_below_280_year","peak_warming_c","warming_at_280_c","net_benefit_through_2100_usd_tn","pv_net_benefit_through_2100_usd_tn","sustained_break_even_year","full_horizon_net_benefit_usd_tn","full_horizon_pv_net_benefit_usd_tn","dac_cost_override_usd_t","ch4_case","n2o_case"]
    sm.get_range("A1:R1").values=[fields];sm.get_range("A1:R1").format={"fill":"#1F4E78","font":{"bold":True,"color":"#FFFFFF"}}
    sm.get_range(f"A2:R{len(allrows)+1}").values=[[r.get(f) for f in fields] for r in allrows];sm.freeze_panes.freeze_rows(1);sm.get_range("A:R").format.wrap_text=True
    sm.get_range("A:B").format.column_width=30;sm.get_range("C:R").format.column_width=18
    # Annual state
    a=wb.worksheets.add("Annual_State");annual=result["annual_state"];fields=list(annual[0].keys());last=chr(64+len(fields)) if len(fields)<=26 else "AE"
    # use generic conversion for >26 columns
    def col(n):
        s=""
        while n:n,rem=divmod(n-1,26);s=chr(65+rem)+s
        return s
    last=col(len(fields));a.get_range(f"A1:{last}1").values=[fields];a.get_range(f"A1:{last}1").format={"fill":"#548235","font":{"bold":True,"color":"#FFFFFF"}}
    a.get_range(f"A2:{last}{len(annual)+1}").values=[[r.get(f) for f in fields] for r in annual];a.freeze_panes.freeze_rows(1);a.get_range("A:A").format.column_width=10;a.get_range(f"B:{last}").format.column_width=18
    # Financing ledger
    fsh=wb.worksheets.add("Sources_Uses");lr=result["sources_and_uses"]["rows"];lf=list(lr[0].keys());last=col(len(lf));fsh.get_range(f"A1:{last}1").values=[lf];fsh.get_range(f"A1:{last}1").format={"fill":"#8064A2","font":{"bold":True,"color":"#FFFFFF"}}
    fsh.get_range(f"A2:{last}{len(lr)+1}").values=[[r.get(k) for k in lf] for r in lr];fsh.freeze_panes.freeze_rows(1);fsh.get_range("A:A").format.column_width=10;fsh.get_range(f"B:{last}").format.column_width=20
    # Social dividend
    sd=wb.worksheets.add("Social_Dividend");sr=result["post_restoration_social_dividend"]["rows"];sf=["year","gross_public_headroom_before_reserve_usd_tn","maintenance_reserve_target_usd_tn","maintenance_reserve_contribution_usd_tn","maintenance_reserve_balance_usd_tn","annual_allocable_social_dividend_usd_tn","cumulative_allocable_social_dividend_usd_tn","pv_cumulative_social_dividend_usd_tn"]
    sd.get_range("A1:H1").values=[sf];sd.get_range("A1:H1").format={"fill":"#C65911","font":{"bold":True,"color":"#FFFFFF"}}
    sd.get_range(f"A2:H{len(sr)+1}").values=[[r.get(k) for k in sf] for r in sr];sd.freeze_panes.freeze_rows(1);sd.get_range("A:A").format.column_width=10;sd.get_range("B:H").format.column_width=25
    # Claims boundary
    cb=wb.worksheets.add("Claims_Boundary");cr=[
        ["Domain","Version 52 position","Status"],["Restoration dates","Screening milestones only; calibrated FaIR/OSCAR and process-model validation still required.","NOT A FORECAST"],
        ["GDP / economics","Long-horizon dollar results are highly GDP-path and discount-rate sensitive; low/central/high cases are shown.","SENSITIVITY SCREEN"],
        ["Social dividend","Continued levy collection after reserve funding; never add to avoided damages.","FISCAL POLICY SCREEN"],
        ["Energy","86,181 TWh/yr of pre-CDR transformed electricity is externally supplied, not endogenously solved.","EXTERNAL SCREEN"],
        ["Fish / hunger / longevity / carrying capacity","Not dynamically predicted by Version 52.","EXTERNAL CONTEXT"],
        ["Non-CO2 endpoint","CH4/N2O concentration-pathway axes test temperature restoration; endpoints are authored scenario assumptions.","SCENARIO SCREEN"],
    ];cb.get_range(f"A1:C{len(cr)}").values=cr;cb.get_range("A1:C1").format={"fill":"#7030A0","font":{"bold":True,"color":"#FFFFFF"}};cb.get_range("A:C").format.wrap_text=True;cb.get_range("A:A").format.column_width=34;cb.get_range("B:B").format.column_width=90;cb.get_range("C:C").format.column_width=25
    # Read me
    rm=wb.worksheets.add("Read_Me");notes=[["Release",V52_RELEASE_LABEL],["Source of truth","planetary_restoration_model_v52.py -> one immutable annual state -> every annual CSV/workbook table."],["CDR cases","Accelerated design; Evidence-Anchored; Constraint-Binding stress."],["GDP central","2.5% real growth declining asymptotically toward 1.0%; low/high are sensitivities, not forecasts."],["Permafrost","Running-peak commitment; lagged 30/50/70-year release; 50 years central."],["Controller","279.5-280.5 ppm operating band with 0.5 GtCO2/yr^2 rate limit near target."],["Permanent fund boundary","Social dividend is continued levy revenue after reserve funding, not avoided damages as cash."]]
    rm.get_range(f"A1:B{len(notes)}").values=notes;rm.get_range("A:A").format={"font":{"bold":True}};rm.get_range("A:A").format.column_width=30;rm.get_range("B:B").format.column_width=100;rm.get_range("B:B").format.wrap_text=True
    out=root/"Planetary_Restoration_Model_V52.xlsx";SpreadsheetFile.export_xlsx(wb).save(str(out));return out


def build_v52_figures(result: Dict, root: Path) -> None:
    try:import matplotlib.pyplot as plt
    except ImportError:return
    figs=root/"figures";figs.mkdir(exist_ok=True);annual=result["annual_state"]
    plt.figure(figsize=(9,5));plt.plot([r["year"] for r in annual],[r["co2_ppm"] for r in annual],label="CO2 ppm");plt.axhspan(279.5,280.5,alpha=.12);plt.xlabel("Year");plt.ylabel("ppm");plt.title("Version 52 accelerated-design atmospheric CO2");plt.tight_layout();plt.savefig(figs/"v52_co2_target_band.png",dpi=180);plt.close()
    plt.figure(figsize=(9,5));plt.plot([r["year"] for r in annual],[r["surface_warming_c"] for r in annual],label="Restoration");plt.xlabel("Year");plt.ylabel("degC above preindustrial");plt.title("Version 52 global-mean temperature screen");plt.tight_layout();plt.savefig(figs/"v52_temperature.png",dpi=180);plt.close()
    post=[r for r in result["post_restoration_social_dividend"]["rows"] if r["post_restoration_active"]]
    if post:
        plt.figure(figsize=(9,5));plt.plot([r["year"] for r in post],[r["gross_public_headroom_before_reserve_usd_tn"] for r in post],label="Gross public headroom");plt.plot([r["year"] for r in post],[r["annual_allocable_social_dividend_usd_tn"] for r in post],label="Allocable after reserve");plt.xlabel("Year");plt.ylabel("USD tn/yr");plt.title("Version 52 post-restoration fiscal headroom");plt.legend();plt.tight_layout();plt.savefig(figs/"v52_social_dividend.png",dpi=180);plt.close()


def run_v52_tests(result: Optional[Dict]=None) -> None:
    r=result or run_v52_release();annual=r["annual_state"]
    # C1: negative avoided damages must exist during aerosol-unmasking window.
    pre=[x for x in r["avoided_damages"]["rows"] if 2027<=x["year"]<=2048]
    assert sum(float(x["avoided_damage_usd_tn_central_5pct_at_3c"]) for x in pre)<0
    # C8 mass bookkeeping: lagged permafrost release cannot exceed new post-start commitment.
    pf=r["permafrost_feedback"]["rows"];assert pf[0]["carbon_release_gtco2"]==0.0
    assert all(float(x["unreleased_carbon_pool_pgc"])>=-1e-12 for x in pf)
    # C11 annual-state identity: climate and permafrost writers share one value.
    cl={x["year"]:x for x in r["climate"]["rows"]}
    for x in annual:assert abs(float(x["surface_warming_c"])-float(cl[x["year"]]["surface_warming_c"]))<1e-12
    # Carbon flux identity.
    for x in r["durable_carbon"]["rows"]:
        lhs=float(x["net_anthropogenic_gtco2"]);rhs=float(x["gross_emissions_gtco2"])+float(x["permafrost_source_gtco2"])+float(x["stored_carbon_reversal_gtco2"])-float(x["actual_incremental_cdr_gtco2"])
        assert abs(lhs-rhs)<1e-9
    # Three co-equal CDR cases and nine non-CO2 combinations are published.
    assert len(r["scenario_matrix"]["cdr_cases"])==3;assert len(r["scenario_matrix"]["nonco2_matrix"])==9
    # Social/fiscal and welfare ledgers remain separate.
    assert "avoided_damage" not in " ".join(r["post_restoration_social_dividend"].keys()).lower()
    # External electricity label remains visible.
    assert r["headline"]["external_pre_cdr_electricity_twh_yr"]>0
    print("VERSION 52 RECONCILED TESTS PASSED")


def v52_main(argv: Optional[Sequence[str]]=None) -> int:
    import argparse
    ap=argparse.ArgumentParser(description=V52_RELEASE_LABEL);ap.add_argument("--tests",action="store_true");ap.add_argument("--no-write",action="store_true")
    args=ap.parse_args(argv);result=run_v52_release();_core_run_tests();_core_run_new_section_tests();run_advanced_tests(run_advanced_model());run_v52_tests(result)
    if not args.no_write:
        root=Path(__file__).resolve().parent;write_v52_outputs(result,root);build_v52_workbook(result,root);build_v52_figures(result,root)
    print(json.dumps(result["headline"],indent=2,sort_keys=True));return 0


# Version 52 entry point superseded by Version 53 below.

# ============================================================================================
# VERSION 53 — adversarial-audit hardening
# ============================================================================================

V53_MODEL_VERSION = "53.1"
V53_RELEASE_LABEL = "Planetary Restoration Model Version 53.1 — Nature-readiness internal candidate"
V53_RELEASE_STATUS = "INTERNAL_NATURE_READINESS_CANDIDATE_EXTERNAL_FAIR_BENCHMARK_STILL_BLOCKING"


def _percentile_v53(xs: Sequence[float], p: float) -> Optional[float]:
    vals=sorted(float(x) for x in xs)
    if not vals:return None
    pos=(len(vals)-1)*p;lo=int(math.floor(pos));hi=int(math.ceil(pos));f=pos-lo
    return vals[lo] if lo==hi else vals[lo]*(1.0-f)+vals[hi]*f


def durable_carbon_cycle_v53(
    s: Scenario, land_case: str, temperature_driver: Mapping[int,float],
    permafrost_source_gtco2: Mapping[int,float], controller: RestorationControllerAssumptions,
    maintain_after_target_years: int=30, funding_scale_by_year: Optional[Mapping[int,float]]=None,
) -> Dict:
    """V53 advanced carbon-cycle screen with optional degraded collection feedback.

    This retains V52 storage/reversal, lagged permafrost and target-band logic, but
    exposes all four Joos reservoir states and permits a year-specific funded-CDR
    scale. The Joos states are diagnostics only: negative perturbation boxes are
    treated as an extrapolation warning, not as publication-grade carbon-cycle truth.
    """
    init=initialize_carbon_state(START_CO2_PPM,s.observed_natural_sink_gtc_yr);state=list(init["state_gtc"])
    stocks={p:0.0 for p in PATHWAY_STORAGE};rows=[];pathway_rows=[]
    peak_ppm=START_CO2_PPM;peak_year=START_YEAR;crossing=None;band_entry=None;maintenance_years=0
    cum_cdr=cum_rev=cum_pf=0.0;shortfalls=[];prev_actual=0.0;ramp_overrides=[]
    lower=controller.target_ppm-controller.band_half_width_ppm;upper=controller.target_ppm+controller.band_half_width_ppm
    funding_scale_by_year=funding_scale_by_year or {}
    for year in range(START_YEAR,s.end_year+1):
        warming=float(temperature_driver.get(year,temperature_driver.get(year-1,1.37)))
        emissions=float(gross_emissions_path(year,s));pf=float(permafrost_source_gtco2.get(year,0.0))
        plan=effective_cdr_path(year,s,land_case)
        funding_scale=max(0.0,min(1.0,float(funding_scale_by_year.get(year,1.0))))
        feasible_map={r["pathway"]:float(r["cdr_gtco2_yr"])*funding_scale for r in plan["rows"]}
        feasible=sum(feasible_map.values())
        reversals={};after={}
        for pathway,stock in stocks.items():
            cfg=PATHWAY_STORAGE[pathway];rate=cfg.annual_reversal_fraction*_climate_reversal_multiplier(pathway,warming)
            rev=min(stock,max(0.0,stock*rate));reversals[pathway]=rev;after[pathway]=stock-rev
        rev_total=sum(reversals.values());current_ppm=PREINDUSTRIAL_CO2_PPM+sum(state)/CO2_MASS_GTC_PER_PPM;ramp_override=False
        if current_ppm>upper:
            requested=feasible;controller_mode="full_drawdown"
            test_state,_=_advance_reservoirs(list(state),emissions+pf+rev_total-requested)
            test_ppm=PREINDUSTRIAL_CO2_PPM+sum(test_state)/CO2_MASS_GTC_PER_PPM
            if test_ppm<upper:
                net_b=_required_net_flux_for_target(state,upper)
                requested=max(0.0,min(feasible,emissions+pf+rev_total-net_b));ramp_override=True
                controller_mode="band_entry_boundary_override";ramp_overrides.append(year)
        else:
            net_mid=_required_net_flux_for_target(state,controller.target_ppm)
            desired=max(0.0,min(feasible,emissions+pf+rev_total-net_mid))
            candidate=min(feasible,max(0.0,_move_toward(prev_actual,desired,controller.cdr_ramp_limit_gtco2_yr2)))
            test_state,_=_advance_reservoirs(list(state),emissions+pf+rev_total-candidate)
            test_ppm=PREINDUSTRIAL_CO2_PPM+sum(test_state)/CO2_MASS_GTC_PER_PPM
            requested=candidate;controller_mode="band_hold_rate_limited"
            if test_ppm<lower:
                net_b=_required_net_flux_for_target(state,lower)
                requested=max(0.0,min(feasible,emissions+pf+rev_total-net_b));ramp_override=True;controller_mode="band_lower_boundary_override"
            elif test_ppm>upper:
                net_b=_required_net_flux_for_target(state,upper)
                requested=max(0.0,min(feasible,emissions+pf+rev_total-net_b));ramp_override=True;controller_mode="band_upper_boundary_override"
            if ramp_override:ramp_overrides.append(year)
        requested_scale=min(1.0,requested/feasible) if feasible>0 else 0.0
        actual={};sat_short=0.0
        for pathway,amount in feasible_map.items():
            cfg=PATHWAY_STORAGE[pathway];proposed=amount*requested_scale
            accepted=proposed if cfg.stock_capacity_gtco2 is None else min(proposed,max(0.0,cfg.stock_capacity_gtco2-after[pathway]))
            actual[pathway]=accepted;sat_short+=max(0.0,proposed-accepted);stocks[pathway]=after[pathway]+accepted
        actual_total=sum(actual.values());prev_actual=actual_total
        net=emissions+pf+rev_total-actual_total;state,sink=_advance_reservoirs(state,net)
        ppm=PREINDUSTRIAL_CO2_PPM+sum(state)/CO2_MASS_GTC_PER_PPM
        if band_entry is None and lower<=ppm<=upper:band_entry=year
        if crossing is None:cum_cdr+=actual_total;cum_rev+=rev_total;cum_pf+=pf
        if ppm>peak_ppm:peak_ppm=ppm;peak_year=year
        if crossing is None and ppm<=controller.target_ppm:crossing=year
        active=band_entry is not None
        if active:maintenance_years+=1
        if active and actual_total+1e-9<requested:shortfalls.append(year)
        rows.append({
            "year":year,"phase":"target_band" if active else "drawdown","controller_mode":controller_mode,
            "controller_ramp_override":ramp_override,"gross_emissions_gtco2":emissions,"permafrost_source_gtco2":pf,
            "stored_carbon_reversal_gtco2":rev_total,"planned_incremental_cdr_gtco2":float(plan["planned_cdr_gtco2_yr"]),
            "physical_feasible_incremental_cdr_gtco2":sum(float(r["cdr_gtco2_yr"]) for r in plan["rows"]),
            "collection_funding_scale":funding_scale,"feasible_incremental_cdr_gtco2":feasible,
            "requested_incremental_cdr_gtco2":requested,"actual_incremental_cdr_gtco2":actual_total,
            "saturation_shortfall_gtco2":sat_short,"net_anthropogenic_gtco2":net,
            "natural_reservoir_flux_to_sinks_gtc":sink,"co2_ppm":ppm,
            "reservoir_permanent_gtc":state[0],"reservoir_slow_gtc":state[1],"reservoir_medium_gtc":state[2],"reservoir_fast_gtc":state[3],
            "total_stored_carbon_stock_gtco2":sum(stocks.values()),"biological_restoration_stock_gtco2":stocks["Biological restoration"],
            "biochar_stock_gtco2":stocks["Biochar"],"land_binding":bool(plan["land_nexus"]["binding"]),
            "surface_warming_driver_c":warming,"target_band_lower_ppm":lower,"target_band_upper_ppm":upper,
        })
        for pathway in PATHWAY_STORAGE:
            pathway_rows.append({"year":year,"pathway":pathway,"new_storage_gtco2":actual[pathway],"reversal_gtco2":reversals[pathway],
                                 "stock_gtco2":stocks[pathway],"annual_reversal_fraction":PATHWAY_STORAGE[pathway].annual_reversal_fraction,
                                 "climate_reversal_multiplier":_climate_reversal_multiplier(pathway,warming),"stock_capacity_gtco2":PATHWAY_STORAGE[pathway].stock_capacity_gtco2})
        if active and maintenance_years>=maintain_after_target_years:break
    first_fast_negative=next((r["year"] for r in rows if float(r["reservoir_fast_gtc"])<0.0),None)
    first_net_outgassing=next((r["year"] for r in rows if float(r["natural_reservoir_flux_to_sinks_gtc"])<0.0),None)
    return {
        "model_class":"Joos four-reservoir diagnostic + durable storage/reversal + lagged permafrost + target-band controller",
        "publication_boundary":"Joos IRF is a diagnostic only under sustained large negative emissions. Official calibrated/constrained FaIR/OSCAR validation is a release gate.",
        "scenario":asdict(s),"land_case":land_case,"initialization":init,"peak_co2_ppm":peak_ppm,"peak_year":peak_year,
        "crossing_year":crossing,"target_band_entry_year":band_entry,"cumulative_incremental_cdr_to_target_gtco2":cum_cdr,
        "cumulative_reversal_to_target_gtco2":cum_rev,"cumulative_permafrost_to_target_gtco2":cum_pf,
        "stock_at_end_gtco2":sum(stocks.values()),"pathway_stock_at_end_gtco2":dict(stocks),"maintenance_shortfall_years":shortfalls,
        "target_held":not shortfalls if band_entry is not None else None,"controller_ramp_override_years":ramp_overrides,
        "controller_assumptions":asdict(controller),"first_negative_fast_reservoir_year":first_fast_negative,
        "first_natural_flux_outgassing_year":first_net_outgassing,"minimum_fast_reservoir_gtc":min(float(r["reservoir_fast_gtc"]) for r in rows),
        "rows":rows,"pathway_rows":pathway_rows,
    }


def _v53_funding_scale_path(s: Scenario, land_case: str, collection_case_index: int) -> Dict[int,float]:
    if collection_case_index==0:return {}
    fp=funding_constrained_cdr_path(s,SETTLEMENT_COLLECTION_CASES[collection_case_index],land_case)
    return {int(r["year"]):float(r["funding_scale"]) for r in fp["rows"]}


def run_v53_physical_case(
    s: Scenario, land_case: str="central", permafrost_tau_yr: float=50.0,
    nonco2_case_key: str="baseline", collection_case_index: int=0,
    coupling_iterations: int=3, maintenance_after_target_years: int=30,
) -> Dict:
    """Run the complete V53 physical state without the long-horizon welfare ledger."""
    if nonco2_case_key not in NONCO2_MITIGATION_CASES:raise KeyError(nonco2_case_key)
    a=V52Assumptions(coupling_iterations=coupling_iterations,maintenance_after_target_years=maintenance_after_target_years)
    pfass=replace(a.permafrost,thaw_release_tau_yr=float(permafrost_tau_yr));mitigation=NONCO2_MITIGATION_CASES[nonco2_case_key]
    funding=_v53_funding_scale_path(s,land_case,collection_case_index)
    legacy=carbon_cycle(s,land_case,maintain_after_target_years=max(1,maintenance_after_target_years))
    legacy_cl=climate_run(legacy["rows"]);temp=_temperature_by_year(legacy_cl["rows"]);history=[]
    carbon=climate=gases=pf=None
    for iteration in range(coupling_iterations):
        driver=[{"year":y,"surface_warming_c":t} for y,t in sorted(temp.items())]
        pf=permafrost_feedback_v52(driver,pfass)
        carbon=durable_carbon_cycle_v53(s,land_case,temp,pf["co2_release_by_year"],a.controller,maintenance_after_target_years,funding)
        years=[int(r["year"]) for r in carbon["rows"]]
        gases=dynamic_nonco2_states_v52(years,s,land_case,a.gas,mitigation)
        climate=climate_with_dynamic_nonco2_v52(carbon["rows"],gases,pf["methane_equiv_release_by_year"],methane_equiv_lifetime_yr=pfass.methane_equivalent_lifetime_yr)
        new=_temperature_by_year(climate["rows"]);ov=sorted(set(temp)&set(new));delta=max((abs(new[y]-temp[y]) for y in ov),default=0.0)
        history.append({"iteration":iteration+1,"max_temperature_change_c":delta,"first_below_280_year":carbon["crossing_year"],"peak_warming_c":climate["peak_warming_c"]})
        temp=new
    assert carbon and climate and gases and pf
    return {"carbon":carbon,"climate":climate,"permafrost":pf,"nonco2":gases,"coupling_convergence":history,
            "collection_case":SETTLEMENT_COLLECTION_CASES[collection_case_index].name}


def full_advanced_sensitivity_ensemble_v53(n: int=700, seed: int=20260902, deterministic_crossing_year: Optional[int]=2155) -> Dict:
    """Full advanced physical ensemble, without settlement stress mixed into probability-like percentiles.

    The ensemble propagates transition architecture, CDR scale/timing, land efficiency,
    initial sink strength, stored-carbon reversals, lagged permafrost and dynamic non-CO2
    forcing through the same advanced annual state used by V53. Collection degradation is
    intentionally reported as a separate stress family below. Weights are authored scenario
    weights, not estimated probabilities.
    """
    rnd=random.Random(seed);years=[];peaks=[];temps=[];noncross=0;landbind=0;draw_rows=[]
    transition_keys=["iea_nze_reference","high_acceleration","current_investment_constrained","natural_turnover","delayed_finance"]
    transition_weights=[0.35,0.15,0.20,0.15,0.15]
    land_keys=["central","low_efficiency","high_efficiency"];land_weights=[0.60,0.20,0.20]
    for draw_index in range(n):
        key=rnd.choices(transition_keys,weights=transition_weights,k=1)[0]
        mature_cdr=rnd.triangular(10.0,16.0,15.2)
        maturity_year=int(round(rnd.triangular(2040,2055,2043)))
        sink_strength=rnd.triangular(5.4,7.2,6.3)
        s=Scenario(name="V53.1 full-advanced sensitivity draw",emissions_mode="endogenous",transition_case_key=key,cdr_mode="accelerated",
                   mature_incremental_cdr_gtco2=mature_cdr,cdr_maturity_year=maturity_year,
                   observed_natural_sink_gtc_yr=sink_strength,end_year=2400)
        land=rnd.choices(land_keys,weights=land_weights,k=1)[0];tau=rnd.triangular(30.0,70.0,50.0)
        rr=run_v53_physical_case(s,land,tau,"baseline",0,3,6)
        c=rr["carbon"];cl=rr["climate"];peaks.append(float(c["peak_co2_ppm"]));temps.append(float(cl["peak_warming_c"]))
        bound=any(bool(r.get("land_binding")) for r in c["rows"])
        if bound:landbind+=1
        if c["crossing_year"] is None:noncross+=1
        else:years.append(float(c["crossing_year"]))
        draw_rows.append({"draw":draw_index+1,"transition_case":key,"land_case":land,
                          "mature_incremental_cdr_gtco2_yr":mature_cdr,"cdr_maturity_year":maturity_year,
                          "observed_natural_sink_gtc_yr":sink_strength,"permafrost_tau_yr":tau,
                          "first_below_280_year":c["crossing_year"],"peak_co2_ppm":float(c["peak_co2_ppm"]),
                          "peak_warming_c":float(cl["peak_warming_c"]),"land_binding":bound})
    rank=(sum(1 for x in years if x<=float(deterministic_crossing_year))/len(years)) if (years and deterministic_crossing_year is not None) else None
    censored=years+[float("inf")]*noncross
    def cen(p):
        v=_percentile_v53(censored,p);return None if (v is None or math.isinf(v)) else v
    return {
        "classification":"Full V53.1 advanced physical sensitivity ensemble. Conditional percentiles are over returning draws; all-draw percentiles reinsert non-returning draws as right-censored. Authored ranges/weights are not empirical probabilities.",
        "samples":n,"crossing_samples":len(years),"noncrossing_samples":noncross,"fraction_not_restored_within_horizon":noncross/n if n else math.nan,
        "return_year_p05_conditional":_percentile_v53(years,0.05),"return_year_p50_conditional":_percentile_v53(years,0.50),"return_year_p95_conditional":_percentile_v53(years,0.95),
        "return_year_p50_all_draws":cen(0.50),"return_year_p95_all_draws":cen(0.95),
        "accelerated_design_crossing_year":deterministic_crossing_year,"accelerated_design_percentile_rank_among_returning":rank,
        "peak_co2_p05":_percentile_v53(peaks,0.05),"peak_co2_p50":_percentile_v53(peaks,0.50),"peak_co2_p95":_percentile_v53(peaks,0.95),
        "peak_warming_p05":_percentile_v53(temps,0.05),"peak_warming_p50":_percentile_v53(temps,0.50),"peak_warming_p95":_percentile_v53(temps,0.95),
        "land_binding_fraction":landbind/n if n else math.nan,
        "transition_case_weights":dict(zip(transition_keys,transition_weights)),"land_case_weights":dict(zip(land_keys,land_weights)),
        "parameter_ranges":{"mature_incremental_cdr_gtco2_yr":"triangular 10-16 mode 15.2","cdr_maturity_year":"triangular 2040-2055 mode 2043","observed_natural_sink_gtc_yr":"triangular 5.4-7.2 mode 6.3","permafrost_tau_yr":"triangular 30-70 mode 50"},
        "nonco2_treatment":"baseline V53.1 CH4/N2O pathway held fixed so the ensemble isolates physical/deployment uncertainty; non-CO2 mitigation is reported separately.",
        "draw_rows":draw_rows,
    }


def collection_stress_physics_v53() -> Dict:
    s=Scenario(name="Accelerated Planetary Restoration Design — collection stress",emissions_mode="endogenous",transition_case_key="iea_nze_reference",cdr_mode="accelerated",mature_incremental_cdr_gtco2=15.2,cdr_maturity_year=2043,end_year=2400)
    rows=[]
    for i,case in enumerate(SETTLEMENT_COLLECTION_CASES):
        rr=run_v53_physical_case(s,"central",50.0,"baseline",i,4,30);c=rr["carbon"];cl=rr["climate"]
        fp=funding_constrained_cdr_path(s,case,"central");mat=next(r for r in fp["rows"] if r["year"]==s.cdr_maturity_year)
        crossed=c["crossing_year"]
        rows.append({"case":case.name,"first_below_280_year":crossed,
                     "return_status":"RETURNED_WITHIN_HORIZON" if crossed is not None else "CENSORED_NOT_RETURNED_BY_HORIZON",
                     "censored":crossed is None,"censor_horizon_year":2400,"plot_year":crossed if crossed is not None else 2400,
                     "peak_co2_ppm":c["peak_co2_ppm"],"peak_warming_c":cl["peak_warming_c"],
                     "maturity_funding_scale":mat["funding_scale"],"maturity_funded_cdr_gtco2_yr":mat["funded_cdr_gtco2_yr"],
                     "funding_binding_year_count":sum(1 for r in fp["rows"] if r["funding_binding"]),"first_funding_binding_year":next((r["year"] for r in fp["rows"] if r["funding_binding"]),None)})
    return {"classification":"Degraded settlement collection propagated through the full V53.1 advanced physical state. Monetary reserve/liquidity failures are reported separately and are not treated as the same mechanism.","rows":rows}


def grid_adjusted_materials_v53(frontier_row: Mapping, demand_twh_yr: float,
                                a: MineralAssumptions=MineralAssumptions(), w: WorkforceAssumptions=WorkforceAssumptions()) -> Dict:
    solar_gw=float(frontier_row.get("required_solar_capacity_gw") or 0.0);wind_gw=float(frontier_row.get("required_wind_capacity_gw") or 0.0)
    firm_gw=float(frontier_row.get("firm_clean_capacity_gw") or 0.0);storage_gwh=float(frontier_row.get("storage_energy_gwh") or 0.0)
    vre_mw=(solar_gw+wind_gw)*1000.0;firm_mw=firm_gw*1000.0;avg_load_mw=demand_twh_yr/8760.0*1e6;storage_kwh=storage_gwh*1e6
    copper_mt=(vre_mw*a.vre_copper_t_per_mw+firm_mw*a.firm_copper_t_per_mw+avg_load_mw*a.grid_copper_t_per_mw_avg_load)/1e6
    lithium_mt=storage_kwh*a.lithium_kg_per_kwh/1e9;nickel_mt=storage_kwh*a.nickel_battery_share*a.nickel_kg_per_kwh_for_nickel_chemistries/1e9
    steel_gt=(vre_mw*a.vre_steel_t_per_mw+firm_mw*a.firm_steel_t_per_mw+avg_load_mw*a.grid_steel_t_per_mw_avg_load)/1e9
    power_build_fte=(vre_mw+firm_mw)/25.0/w.power_build_mw_per_worker_yr;power_ops_fte=avg_load_mw/w.operations_mw_per_worker
    return {"case":frontier_row.get("case"),"minimum_vre_overbuild":frontier_row.get("minimum_vre_overbuild"),"solar_capacity_gw":solar_gw,"wind_capacity_gw":wind_gw,
            "firm_clean_capacity_gw":firm_gw,"storage_energy_gwh":storage_gwh,"curtailment_twh":frontier_row.get("curtailment_twh"),
            "copper_mt_buildout":copper_mt,"lithium_mt_buildout":lithium_mt,"nickel_mt_buildout":nickel_mt,"steel_gt_buildout":steel_gt,
            "power_build_annualized_fte_over_25yr":power_build_fte,"power_operations_fte":power_ops_fte}


def energy_and_grid_v53(primary: Dict) -> Dict:
    e=primary["electricity"];demand=float(e["total_twh_yr"]);grid=grid_reliability_stress_table(demand)
    frontier=[r for r in grid.get("adequacy_frontier_rows",[]) if r.get("frontier_found")]
    adjusted=[grid_adjusted_materials_v53(r,demand) for r in frontier];central=next((r for r in adjusted if str(r.get("case","")).startswith("Balanced")),adjusted[0] if adjusted else None)
    external=float(e["pre_cdr_twh_yr"]);cdr=float(e["cdr_twh_yr"])
    return {
        "classification":"Energy-boundary and synthetic adequacy propagation. The 86,181.327-TWh/yr pre-CDR base is not sectorally decomposed in the supplied source and remains an explicit publication blocker rather than being silently invented.",
        "demand_decomposition":[
            {"component":"Externally supplied pre-CDR transformed electricity screen","twh_yr":external,"status":"EXTERNAL_SCREEN_UNDECOMPOSED_BY_SECTOR"},
            {"component":"Endogenous mature CDR direct electricity","twh_yr":cdr,"status":"MODEL_DERIVED_FROM_CDR_PORTFOLIO"},
            {"component":"Mature electricity total used for adequacy stress","twh_yr":demand,"status":"SUM_OF_EXTERNAL_PLUS_MODEL_DERIVED"},
        ],
        "external_share_fraction":external/demand if demand else None,"sectoral_external_decomposition_status":"NOT_AVAILABLE_IN_SOURCE_PACKAGE",
        "default_adequacy_rows":grid.get("rows",[]),"adequacy_frontier_rows":frontier,"grid_adjusted_materials_rows":adjusted,
        "default_failed_case_count":len(grid.get("failed_cases",[])),"default_case_count":len(grid.get("rows",[])),
        "minimum_vre_overbuild_range":[min((float(r["minimum_vre_overbuild"]) for r in frontier),default=None),max((float(r["minimum_vre_overbuild"]) for r in frontier),default=None)],
        "balanced_72h_grid_adjusted_materials":central,
    }


def external_validation_manifest_v53() -> Dict:
    import importlib.util
    fair_available=importlib.util.find_spec("fair") is not None;oscar_available=importlib.util.find_spec("oscar") is not None
    return {
        "release_gate":"BLOCKING",
        "fair":{"status":"AVAILABLE_NOT_RUN" if fair_available else "NOT_EXECUTED_DEPENDENCY_UNAVAILABLE_IN_BUILD_ENVIRONMENT",
                "required_version":"FaIR 2.2.4 official package","calibration":"fair-calibrate 1.4.1 calibrated/constrained 841-member ensemble",
                "package_url":"https://pypi.org/project/fair/2.2.4/","documentation_url":"https://docs.fairmodel.net/en/latest/examples/calibrated_constrained_ensemble.html",
                "calibration_data_url":"https://github.com/OMS-NetZero/FAIR/tree/master/examples/data/calibrated_constrained_ensemble"},
        "oscar":{"status":"AVAILABLE_NOT_RUN" if oscar_available else "NOT_EXECUTED_DEPENDENCY_UNAVAILABLE_IN_BUILD_ENVIRONMENT",
                 "required_model":"Official IIASA OSCAR; v4 is beta as of the V53 build date, so archive the exact commit/data library used.",
                 "repository_url":"https://github.com/iiasa/OSCAR"},
        "trajectory_contract":"data/external_validation_net_co2_trajectory.csv contains the actual V53.1 advanced annual net CO2 pathway (gross CO2 + permafrost CO2 + storage reversals - CDR). External model runs must ingest this pathway or an exactly documented equivalent and archive parameter/config identifiers.",
        "publication_rule":"No precise restoration year may be presented as validated until official calibrated/constrained FaIR and an archived OSCAR configuration have been run on the V53.1 trajectory and their spread reported.",
    }


def run_v53_release(ensemble_samples: int=700) -> Dict:
    # Run the full-advanced ensemble before constructing the very large V52 release object.
    # Keeping those working sets separate avoids pathological memory/GC interaction in a single
    # process while preserving identical deterministic calculations.
    s=Scenario(name="Accelerated Planetary Restoration Design",emissions_mode="endogenous",transition_case_key="iea_nze_reference",cdr_mode="accelerated",mature_incremental_cdr_gtco2=15.2,cdr_maturity_year=2043,end_year=2400)
    diag=run_v53_physical_case(s,"central",50.0,"baseline",0,4,30)
    design_crossing=diag["carbon"]["crossing_year"]
    ensemble=full_advanced_sensitivity_ensemble_v53(ensemble_samples,20260902,design_crossing)
    base=run_v52_release()
    collection=collection_stress_physics_v53()
    energy_grid=energy_and_grid_v53(base)
    monetary=monetary_stress_table()
    evidence=next(x for x in base["scenario_matrix"]["cdr_cases"] if x.get("scenario_key")=="evidence")
    constraint=next(x for x in base["scenario_matrix"]["cdr_cases"] if x.get("scenario_key")=="constraint")
    external=external_validation_manifest_v53()
    h=dict(base["headline"])
    crossing_year=int(h["first_below_280_year"])
    crossing_state=next(r for r in base["annual_state"] if int(r["year"])==crossing_year)
    residual_co2_forcing=float(crossing_state["co2_forcing_w_m2"])
    residual_nonco2_forcing=float(crossing_state["nonco2_forcing_w_m2"])
    residual_pf_methane_forcing=float(crossing_state.get("permafrost_methane_forcing_proxy_w_m2") or 0.0)
    residual_total_forcing=residual_co2_forcing+residual_nonco2_forcing+residual_pf_methane_forcing
    residual_warming=float(crossing_state["surface_warming_c"])
    effective_c_per_wm2=residual_warming/residual_total_forcing if residual_total_forcing else None
    h.update({
        "headline_return_year_conditional_full_advanced_ensemble_median":ensemble["return_year_p50_conditional"],
        "headline_return_year_p05_conditional":ensemble["return_year_p05_conditional"],"headline_return_year_p95_conditional":ensemble["return_year_p95_conditional"],
        "headline_fraction_not_restored_within_horizon":ensemble["fraction_not_restored_within_horizon"],
        "accelerated_design_percentile_rank_among_returning":ensemble["accelerated_design_percentile_rank_among_returning"],
        "evidence_anchored_first_below_280_year":evidence.get("first_below_280_year"),"constraint_binding_first_below_280_year":constraint.get("first_below_280_year"),
        "joos_first_negative_fast_reservoir_year":diag["carbon"]["first_negative_fast_reservoir_year"],
        "joos_first_natural_flux_outgassing_year":diag["carbon"]["first_natural_flux_outgassing_year"],
        "external_electricity_share_fraction":energy_grid["external_share_fraction"],"default_grid_cases_failed":energy_grid["default_failed_case_count"],
        "default_grid_case_count":energy_grid["default_case_count"],"minimum_vre_overbuild_low":energy_grid["minimum_vre_overbuild_range"][0],"minimum_vre_overbuild_high":energy_grid["minimum_vre_overbuild_range"][1],
        "monetary_liquidity_failed_cases":len(monetary.get("failed_cases",[])),"monetary_liquidity_total_cases":len(monetary.get("rows",[])),
        "official_fair_oscar_release_gate":"BLOCKING_OFFICIAL_FAIR_NOT_EXECUTED_IN_BUILD_ENVIRONMENT",
        "residual_forcing_at_280_total_w_m2":residual_total_forcing,
        "residual_forcing_at_280_co2_w_m2":residual_co2_forcing,
        "residual_forcing_at_280_nonco2_w_m2":residual_nonco2_forcing,
        "residual_forcing_at_280_permafrost_methane_proxy_w_m2":residual_pf_methane_forcing,
        "residual_warming_at_280_c":residual_warming,
        "effective_temperature_response_at_280_c_per_w_m2":effective_c_per_wm2,
        "doubling_scale_equivalent_c_at_3p71_w_m2":effective_c_per_wm2*3.71 if effective_c_per_wm2 is not None else None,
    })
    result={"model_version":V53_MODEL_VERSION,"release_label":V53_RELEASE_LABEL,"release_status":V53_RELEASE_STATUS,
            "classification":"Coupled global restoration screening/validation candidate. Ensemble median is conditional on return and uses authored sensitivity ranges; not a validated forecast.",
            "headline":h,"primary_v52_state":base,"central_joos_diagnostic":diag,"full_advanced_sensitivity_ensemble":ensemble,
            "degraded_collection_physics":collection,"monetary_liquidity_stress":monetary,"energy_and_grid":energy_grid,
            "external_validation":external}
    return result


def _write_csv_v53(path: Path, rows: Sequence[Mapping]) -> None:
    _write_csv(path,rows)


def write_v53_outputs(result: Dict, root: Path) -> None:
    data=root/"data";data.mkdir(exist_ok=True)
    base=result["primary_v52_state"];annual=base["annual_state"]
    compact={
        "model_version":result["model_version"],"release_label":result["release_label"],"release_status":result["release_status"],
        "classification":result["classification"],"headline":result["headline"],
        "full_advanced_sensitivity_ensemble":result["full_advanced_sensitivity_ensemble"],
        "degraded_collection_physics":result["degraded_collection_physics"],
        "monetary_liquidity_stress":result["monetary_liquidity_stress"],"energy_and_grid":result["energy_and_grid"],
        "external_validation":result["external_validation"],
        "central_joos_diagnostic_summary":{k:v for k,v in result["central_joos_diagnostic"]["carbon"].items() if k not in ("rows","pathway_rows")},
        "primary_screen_headline":base["headline"],"scenario_matrix":base["scenario_matrix"],
    }
    (data/"planetary_restoration_v53_1_results.json").write_text(json.dumps(compact,indent=2),encoding="utf-8")
    _write_csv_v53(data/"annual_state.csv",annual)
    _write_csv_v53(data/"advanced_carbon_trajectory.csv",[{k:r.get(k) for k in ("year","co2_ppm","gross_emissions_gtco2","actual_cdr_gtco2","reversal_gtco2","permafrost_co2_gtco2","stored_carbon_stock_gtco2","land_binding")} for r in annual])
    _write_csv_v53(data/"advanced_climate_trajectory.csv",[{k:r.get(k) for k in ("year","co2_ppm","surface_warming_c","deep_ocean_warming_c","co2_forcing_w_m2","nonco2_forcing_w_m2","permafrost_methane_forcing_proxy_w_m2","ch4_ppb","n2o_ppb")} for r in annual])
    _write_csv_v53(data/"permafrost_feedback.csv",[{k:r.get(k) for k in ("year","surface_warming_c","permafrost_co2_gtco2","permafrost_methane_equiv_gtco2e","permafrost_methane_forcing_proxy_w_m2")} for r in annual])
    _write_csv_v53(data/"economic_balance.csv",base["economic_balance"]["rows"]);_write_csv_v53(data/"sources_and_uses.csv",base["sources_and_uses"]["rows"]);_write_csv_v53(data/"post_restoration_social_dividend.csv",base["post_restoration_social_dividend"]["rows"])
    _write_csv_v53(data/"cdr_cases.csv",base["scenario_matrix"]["cdr_cases"]);_write_csv_v53(data/"gdp_cases.csv",base["scenario_matrix"]["gdp_cases"]);_write_csv_v53(data/"nonco2_matrix.csv",base["scenario_matrix"]["nonco2_matrix"])
    ens=result["full_advanced_sensitivity_ensemble"]
    _write_csv_v53(data/"v53_full_advanced_ensemble_summary.csv",[{k:v for k,v in ens.items() if not isinstance(v,(dict,list))}])
    _write_csv_v53(data/"v53_full_advanced_ensemble_draws.csv",ens.get("draw_rows",[]))
    _write_csv_v53(data/"v53_degraded_collection_physics.csv",result["degraded_collection_physics"]["rows"]);_write_csv_v53(data/"v53_monetary_liquidity_stress.csv",result["monetary_liquidity_stress"]["rows"])
    _write_csv_v53(data/"v53_grid_adequacy_frontier.csv",result["energy_and_grid"]["adequacy_frontier_rows"]);_write_csv_v53(data/"v53_grid_adjusted_materials.csv",result["energy_and_grid"]["grid_adjusted_materials_rows"]);_write_csv_v53(data/"v53_energy_boundary.csv",result["energy_and_grid"]["demand_decomposition"])
    diag_rows=result["central_joos_diagnostic"]["carbon"]["rows"];_write_csv_v53(data/"v53_joos_diagnostic.csv",[{k:r.get(k) for k in ("year","co2_ppm","net_anthropogenic_gtco2","natural_reservoir_flux_to_sinks_gtc","reservoir_permanent_gtc","reservoir_slow_gtc","reservoir_medium_gtc","reservoir_fast_gtc")} for r in diag_rows])
    _write_csv_v53(data/"external_validation_net_co2_trajectory.csv",[{"year":r["year"],"gross_co2_gtco2":r["gross_emissions_gtco2"],"permafrost_co2_gtco2":r["permafrost_source_gtco2"],"stored_carbon_reversal_gtco2":r["stored_carbon_reversal_gtco2"],"cdr_gtco2":r["actual_incremental_cdr_gtco2"],"net_co2_gtco2":r["net_anthropogenic_gtco2"],"joos_diagnostic_co2_ppm":r["co2_ppm"]} for r in diag_rows])
    h=result["headline"]
    text=f"""# Version 53.1 headline results — Nature-readiness internal candidate\n\n**Do not circulate as a validated forecast. Official calibrated/constrained FaIR benchmark execution remains a blocking release gate for Nature-level claims.**\n\n## Primary uncertainty headline\n- Full-advanced conditional return-year median: **{h['headline_return_year_conditional_full_advanced_ensemble_median']:.0f}**.\n- Conditional p05/p95: **{h['headline_return_year_p05_conditional']:.0f}/{h['headline_return_year_p95_conditional']:.0f}**.\n- Fraction not returning by 2400: **{100*h['headline_fraction_not_restored_within_horizon']:.1f}%**.\n- Accelerated design: **{h['first_below_280_year']}**, at the **{100*h['accelerated_design_percentile_rank_among_returning']:.1f}th percentile** among returning full-advanced draws.\n- Evidence-anchored deployment: **{h['evidence_anchored_first_below_280_year']}**.\n- Constraint-binding stress: **{h['constraint_binding_first_below_280_year']}**.\n\n## Main-result non-CO2 endpoint\n- At the accelerated-design <=280 ppm milestone, residual forcing is **{h['residual_forcing_at_280_total_w_m2']:.3f} W/m2**: CO2 **{h['residual_forcing_at_280_co2_w_m2']:.3f} W/m2**, non-CO2 **{h['residual_forcing_at_280_nonco2_w_m2']:.3f} W/m2**, and the permafrost-methane forcing proxy **{h['residual_forcing_at_280_permafrost_methane_proxy_w_m2']:.4f} W/m2**.\n- Residual modeled warming is **{h['residual_warming_at_280_c']:.3f} C**. The effective state-specific response is **{h['effective_temperature_response_at_280_c_per_w_m2']:.3f} C per W/m2**, equivalent to **{h['doubling_scale_equivalent_c_at_3p71_w_m2']:.2f} C per 3.71 W/m2**.\n- The temperature result comes from the model's thermal state and forcing response; subtracting forcing terms is not a derivation of degrees C.\n- Therefore CO2 restoration alone does not restore temperature; the CH4/N2O scenario matrix is a main result.\n\n## Carbon-cycle diagnostic warning\n- Joos fast perturbation reservoir first becomes negative in **{h['joos_first_negative_fast_reservoir_year']}**.\n- Joos diagnostic natural land/ocean flux first becomes net outgassing in **{h['joos_first_natural_flux_outgassing_year']}**.\n- The Joos result is retained only as an internal diagnostic; precise dates require official state-dependent model validation.\n\n## Energy / grid boundary\n- External pre-CDR electricity share: **{100*h['external_electricity_share_fraction']:.1f}%** of the mature electricity screen.\n- Default synthetic adequacy cases failed: **{h['default_grid_cases_failed']}/{h['default_grid_case_count']}**.\n- Minimum VRE overbuild frontier: **{h['minimum_vre_overbuild_low']:.2f}–{h['minimum_vre_overbuild_high']:.2f}x**.\n- The external 86,181.327-TWh/yr base has no sector decomposition in the supplied source; this remains a publication blocker rather than being invented.\n\n## Settlement / monetary stress\n- Degraded collection is propagated through the full advanced physical state in `v53_degraded_collection_physics.csv`. Non-returning cases carry an explicit censoring flag/horizon.\n- Monetary liquidity/reserve stress failures: **{h['monetary_liquidity_failed_cases']}/{h['monetary_liquidity_total_cases']}**. These are separate from collection leakage.\n"""
    (data/"HEADLINE_RESULTS_V53_1.md").write_text(text,encoding="utf-8")

def build_v53_figures(result: Dict, root: Path) -> None:
    try:import matplotlib.pyplot as plt
    except ImportError:return
    figs=root/"figures";figs.mkdir(exist_ok=True)
    # Uncertainty framing: median first, design second.
    e=result["full_advanced_sensitivity_ensemble"];vals=[e["return_year_p05_conditional"],e["return_year_p50_conditional"],e["return_year_p95_conditional"]]
    plt.figure(figsize=(8.5,4.8));plt.bar(["p05","p50 median","p95"],vals);plt.axhline(result["headline"]["first_below_280_year"],linestyle="--",linewidth=1,label="Accelerated design");plt.ylabel("Year of first <=280 ppm");plt.title("V53.1 full-advanced conditional sensitivity range");plt.legend();plt.tight_layout();plt.savefig(figs/"v53_1_ensemble_headline.png",dpi=180);plt.close()
    # Collection stress.
    rows=result["degraded_collection_physics"]["rows"];plt.figure(figsize=(9,4.8));vals=[r["plot_year"] for r in rows];bars=plt.bar(range(len(rows)),vals)
    for i,(bar,r) in enumerate(zip(bars,rows)):
        if r.get("censored"):
            bar.set_hatch("///");plt.text(i,2395,">2400\ncensored",ha="center",va="top",fontsize=8)
    plt.xticks(range(len(rows)),[r["case"] for r in rows],rotation=20,ha="right");plt.ylabel("First <=280 ppm year; hatched = censored at 2400");plt.title("V53.1 collection efficiency propagated through advanced physics");plt.tight_layout();plt.savefig(figs/"v53_1_collection_stress.png",dpi=180);plt.close()
    # Grid frontier.
    fr=result["energy_and_grid"]["adequacy_frontier_rows"];plt.figure(figsize=(9,4.8));plt.bar(range(len(fr)),[r["minimum_vre_overbuild"] for r in fr]);plt.xticks(range(len(fr)),[r["case"] for r in fr],rotation=20,ha="right");plt.ylabel("Minimum VRE overbuild factor");plt.title("V53.1 synthetic adequacy frontier");plt.tight_layout();plt.savefig(figs/"v53_1_grid_overbuild.png",dpi=180);plt.close()



def build_v53_workbook(result: Dict, root: Path) -> Path:
    """Regenerate the Version 53.1 workbook from the current in-memory release state."""
    from artifact_tool import Workbook, SpreadsheetFile
    wb=Workbook.create()
    def col(n:int)->str:
        out=""
        while n:
            n,rem=divmod(n-1,26);out=chr(65+rem)+out
        return out
    def write_table(sh,rows,fields=None,start=1,header_fill="#1F4E78"):
        if not rows:return
        if fields is None:
            fields=[]
            for r in rows:
                for k in r:
                    if k not in fields:fields.append(k)
        last=col(len(fields));sh.get_range(f"A{start}:{last}{start}").values=[fields]
        sh.get_range(f"A{start}:{last}{start}").format={"fill":header_fill,"font":{"bold":True,"color":"#FFFFFF"}}
        sh.get_range(f"A{start+1}:{last}{start+len(rows)}").values=[[json.dumps(r.get(f),ensure_ascii=False) if isinstance(r.get(f),(dict,list)) else r.get(f) for f in fields] for r in rows]
        sh.freeze_panes.freeze_rows(start);sh.get_range(f"A:{last}").format.wrap_text=True
    h=result["headline"]
    sh=wb.worksheets.add("Dashboard");sh.get_range("A1:D1").merge();sh.get_range("A1").values=[[V53_RELEASE_LABEL]];sh.get_range("A1").format={"fill":"#17365D","font":{"bold":True,"color":"#FFFFFF","size":16}}
    sh.get_range("A3:D3").merge();sh.get_range("A3").values=[["VALIDATION CANDIDATE — official calibrated/constrained FaIR and archived OSCAR runs remain a blocking gate. The ensemble median below is conditional on return and is not a forecast."]];sh.get_range("A3").format.wrap_text=True
    rows=[["Metric","Value","Unit / status","Interpretation"],
          ["Full-advanced ensemble conditional median",h["headline_return_year_conditional_full_advanced_ensemble_median"],"year","Primary V53.1 uncertainty headline"],
          ["Full-advanced conditional p05 / p95",f"{h['headline_return_year_p05_conditional']:.0f} / {h['headline_return_year_p95_conditional']:.0f}","year","Returning draws only"],
          ["Non-return by 2400",h["headline_fraction_not_restored_within_horizon"],"fraction","Right-censored draws"],
          ["Accelerated design <=280",h["first_below_280_year"],"year","High-ambition design; not central forecast"],
          ["Accelerated design percentile rank",h["accelerated_design_percentile_rank_among_returning"],"fraction of returning draws","Optimistic corner of authored sensitivity set"],
          ["Evidence-anchored <=280",h["evidence_anchored_first_below_280_year"],"year","State-of-CDR anchored deployment screen"],
          ["Constraint-binding <=280",h["constraint_binding_first_below_280_year"],"year","Stress case"],
          ["Joos fast box first negative",h["joos_first_negative_fast_reservoir_year"],"year","IRF extrapolation warning"],
          ["Joos natural flux first outgassing",h["joos_first_natural_flux_outgassing_year"],"year","Drawdown diagnostic"],
          ["External mature-electricity share",h["external_electricity_share_fraction"],"fraction","86,181.327 TWh/yr base remains undecomposed by sector"],
          ["Synthetic grid cases failed",f"{h['default_grid_cases_failed']}/{h['default_grid_case_count']}","cases","0.01% unserved-energy criterion"],
          ["VRE overbuild frontier",f"{h['minimum_vre_overbuild_low']:.3f}–{h['minimum_vre_overbuild_high']:.3f}x","factor","Fixed storage/firm-share synthetic cases"],
          ["Monetary liquidity failures",f"{h['monetary_liquidity_failed_cases']}/{h['monetary_liquidity_total_cases']}","cases","Separate from collection leakage"],
          ["Residual forcing at <=280",h["residual_forcing_at_280_total_w_m2"],"W/m2","CO2 + non-CO2 + permafrost-methane proxy"],
          ["Residual non-CO2 forcing at <=280",h["residual_forcing_at_280_nonco2_w_m2"],"W/m2","Dominant residual forcing term"],
          ["Residual warming at <=280",h["residual_warming_at_280_c"],"degC","CO2 restoration is not temperature restoration"],
          ["Effective response at <=280",h["effective_temperature_response_at_280_c_per_w_m2"],"degC per W/m2","State-specific diagnostic, not ECS"],
          ["Official FaIR/OSCAR","OPEN / BLOCKING","status","Official calibrated/constrained external benchmark not executed; no validated precise restoration date yet"]]
    sh.get_range(f"A5:D{4+len(rows)}").values=rows;sh.get_range("A5:D5").format={"fill":"#D9EAF7","font":{"bold":True}}
    for c,wid in [("A:A",44),("B:B",32),("C:C",24),("D:D",70)]:sh.get_range(c).format.column_width=wid
    sh.get_range("A:D").format.wrap_text=True;sh.get_range("B8:B8").format.number_format="0.0%";sh.get_range("B10:B10").format.number_format="0.0%";sh.get_range("B15:B15").format.number_format="0.0%"
    ens=wb.worksheets.add("Ensemble");e=result["full_advanced_sensitivity_ensemble"]
    erows=[{"metric":k,"value":json.dumps(v) if isinstance(v,(dict,list)) else v} for k,v in e.items() if k!="return_year_samples"]
    write_table(ens,erows,["metric","value"],1,"#548235");ens.get_range("A:A").format.column_width=48;ens.get_range("B:B").format.column_width=80
    write_table(wb.worksheets.add("CDR_Cases"),result["primary_v52_state"]["scenario_matrix"]["cdr_cases"],None,1,"#4472C4")
    write_table(wb.worksheets.add("Collection_Stress"),result["degraded_collection_physics"]["rows"],None,1,"#C65911")
    write_table(wb.worksheets.add("Grid_Adequacy"),result["energy_and_grid"]["adequacy_frontier_rows"],None,1,"#8064A2")
    write_table(wb.worksheets.add("Grid_Materials"),result["energy_and_grid"]["grid_adjusted_materials_rows"],None,1,"#8064A2")
    write_table(wb.worksheets.add("Monetary_Stress"),result["monetary_liquidity_stress"]["rows"],None,1,"#A64D79")
    write_table(wb.worksheets.add("Energy_Boundary"),result["energy_and_grid"]["demand_decomposition"],None,1,"#70AD47")
    ev=wb.worksheets.add("External_Validation");evrows=[]
    for k,v in result["external_validation"].items():evrows.append({"item":k,"value":json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v})
    write_table(ev,evrows,["item","value"],1,"#BF9000");ev.get_range("A:A").format.column_width=36;ev.get_range("B:B").format.column_width=110
    diag=wb.worksheets.add("Joos_Diagnostic");write_table(diag,result["central_joos_diagnostic"]["carbon"]["rows"],["year","co2_ppm","net_anthropogenic_gtco2","natural_reservoir_flux_to_sinks_gtc","reservoir_permanent_gtc","reservoir_slow_gtc","reservoir_medium_gtc","reservoir_fast_gtc"],1,"#7F6000")
    annual=wb.worksheets.add("Annual_State");write_table(annual,result["primary_v52_state"]["annual_state"],None,1,"#548235")
    rm=wb.worksheets.add("Read_Me");notes=[
        ["Release",V53_RELEASE_LABEL],["Status",V53_RELEASE_STATUS],["Primary headline","Conditional median of the full-advanced authored sensitivity ensemble, not the accelerated design case."],
        ["Carbon-cycle boundary","Joos is diagnostic only once its perturbation boxes enter extrapolated negative territory. Official FaIR/OSCAR is a blocking release gate."],
        ["Permafrost","V53.1 uses the V52/V53 lagged committed-release pool; positive release continues after peak warming."],
        ["Energy","86,181.327 TWh/yr remains an external undecomposed base. Grid overbuild is propagated to capacity/material/workforce stress outputs."],
        ["Finance","Collection leakage and monetary reserve/liquidity failures are separate mechanisms and are reported separately."],
        ["Export precision","CSV files preserve Python float values; displayed 280.000000 values are formatted/rounded representations, not exact controller shooting."],
        ["Non-CO2 endpoint","At the <=280 ppm design milestone, residual forcing is dominated by non-CO2 agents; see Dashboard and nonco2_matrix.csv."],
    ];rm.get_range(f"A1:B{len(notes)}").values=notes;rm.get_range("A:A").format={"font":{"bold":True}};rm.get_range("A:A").format.column_width=34;rm.get_range("B:B").format.column_width=110;rm.get_range("B:B").format.wrap_text=True
    nr=wb.worksheets.add("Nature_Readiness");nrrows=[
        ["Nature-readiness checklist","Status","Evidence / next action"],
        ["Full advanced ensemble leads headline (2188; 2158–2319 conditional)","CLOSED","Dashboard + data/HEADLINE_RESULTS_V53_1.md"],
        ["Accelerated 2155 design explicitly non-central","CLOSED","Dashboard + manuscript methods"],
        ["Severe-migration non-return explicitly censored","CLOSED","Collection_Stress; no fake 2401 data point"],
        ["Export precision documented","CLOSED","data/DATA_README.md"],
        ["Non-CO2 endpoint promoted to main result","CLOSED","0.825 W/m2 total forcing -> 0.762 C through modeled thermal response"],
        ["Full source line inspection","CLOSED","SOURCE_VERIFICATION_V53_1.md"],
        ["Independent economics/financing arithmetic replication","CLOSED","ECONOMICS_FINANCING_REPLICATION.md"],
        ["Pinned core Python environment","CLOSED","requirements.txt"],
        ["Outbound license + citation metadata","CLOSED","LICENSE + CITATION.cff"],
        ["Official calibrated/constrained FaIR benchmark","OPEN — BLOCKING","Cannot execute in this build environment; see FAIR_BENCHMARK_STATUS.md"],
        ["Archived official OSCAR or equivalent independent SCM benchmark","OPEN — BLOCKING","External execution/archive required"],
        ["Persistent public code archive / DOI","OPEN — PUBLICATION ACTION","Create after external validation; no DOI is claimed in this package"],
    ];nr.get_range(f"A1:C{len(nrrows)}").values=nrrows;nr.get_range("A1:C1").format={"fill":"#1F4E78","font":{"bold":True,"color":"#FFFFFF"}};nr.get_range("A:A").format.column_width=60;nr.get_range("B:B").format.column_width=24;nr.get_range("C:C").format.column_width=86;nr.get_range("A:C").format.wrap_text=True;nr.freeze_panes.freeze_rows(1)
    rep_path=root/"data"/"economics_financing_replication.json"
    if rep_path.exists():
        rep=json.loads(rep_path.read_text(encoding="utf-8"));m=rep.get("max_abs_error_usd_tn",{});er=wb.worksheets.add("Econ_Replication");errows=[
            ["Independent economics / financing arithmetic replication","Value","Interpretation"],
            ["Economic rows checked",rep.get("rows_economics"),"CSV-only reconstruction; did not import model code."],
            ["Sources & uses rows checked",rep.get("rows_sources_uses"),"Same annual horizon."],
            ["All identities <= 1e-10 USD tn",rep.get("all_accounting_identities_within_1e-10"),"Floating-point accounting tolerance."],
            ["Max gross-cost identity error",m.get("gross_cost_identity"),"USD tn"],
            ["Max annual-net identity error",m.get("annual_net_identity"),"USD tn"],
            ["Max cumulative-net identity error",m.get("cumulative_net_identity"),"USD tn"],
            ["Max PV cumulative identity error",m.get("pv_net_identity"),"USD tn"],
            ["Max settlement-cap identity error",m.get("settlement_cap_2p14pct_gdp"),"USD tn"],
            ["Max bridge-debt recursion error",m.get("bridge_debt_stock_recursion"),"USD tn"],
            ["Avoided damages 2027–2048",rep.get("sum_avoided_damage_2027_2048_usd_tn"),"Negative values retained during aerosol-unmasking window."],
            ["Total bridge interest",rep.get("total_bridge_interest_usd_tn"),"USD tn"],
            ["Ending bridge debt",rep.get("ending_bridge_debt_usd_tn"),"USD tn"],
        ];er.get_range(f"A1:C{len(errows)}").values=errows;er.get_range("A1:C1").format={"fill":"#548235","font":{"bold":True,"color":"#FFFFFF"}};er.get_range("A:A").format.column_width=48;er.get_range("B:B").format.column_width=28;er.get_range("C:C").format.column_width=74;er.get_range("A:C").format.wrap_text=True;er.freeze_panes.freeze_rows(1)
    out=root/"Planetary_Restoration_Model_V53_1.xlsx";SpreadsheetFile.export_xlsx(wb).save(str(out));return out

def run_v53_tests(result: Optional[Dict]=None) -> None:
    r=result or run_v53_release(120);h=r["headline"];e=r["full_advanced_sensitivity_ensemble"]
    assert e["return_year_p50_conditional"] is not None and e["samples"]>0
    assert h["first_below_280_year"] < e["return_year_p50_conditional"]
    assert r["central_joos_diagnostic"]["carbon"]["first_negative_fast_reservoir_year"] is not None
    pf=r["central_joos_diagnostic"]["permafrost"]["rows"]
    peak_year=r["central_joos_diagnostic"]["climate"]["peak_year"]
    assert any(int(x["year"])>int(peak_year) and float(x["carbon_release_gtco2"])>0 for x in pf)
    assert r["energy_and_grid"]["default_failed_case_count"]==r["energy_and_grid"]["default_case_count"]==4
    lo,hi=r["energy_and_grid"]["minimum_vre_overbuild_range"];assert 1.0<lo<=hi
    severe=next(x for x in r["degraded_collection_physics"]["rows"] if x["case"]=="Severe migration stress")
    assert severe["maturity_funded_cdr_gtco2_yr"]<4.0 and severe["first_below_280_year"] is None
    assert severe["censored"] is True and severe["return_status"]=="CENSORED_NOT_RETURNED_BY_HORIZON" and severe["censor_horizon_year"]==2400
    assert len(r["monetary_liquidity_stress"]["failed_cases"])==3
    assert 0.80 < h["residual_forcing_at_280_total_w_m2"] < 0.85
    assert h["residual_forcing_at_280_nonco2_w_m2"] > 20*h["residual_forcing_at_280_co2_w_m2"]
    print("VERSION 53.1 NATURE-READINESS TESTS PASSED")


def v53_main(argv: Optional[Sequence[str]]=None) -> int:
    import argparse
    ap=argparse.ArgumentParser(description=V53_RELEASE_LABEL);ap.add_argument("--tests",action="store_true");ap.add_argument("--no-write",action="store_true");ap.add_argument("--skip-workbook",action="store_true",help="Skip optional XLSX report generation; scientific CSV/JSON/figures remain fully generated.");ap.add_argument("--ensemble-samples",type=int,default=700)
    args=ap.parse_args(argv);result=run_v53_release(args.ensemble_samples)
    _core_run_tests();_core_run_new_section_tests();run_advanced_tests(run_advanced_model());run_v52_tests(result["primary_v52_state"]);run_v53_tests(result)
    if not args.no_write:
        root=Path(__file__).resolve().parent;write_v53_outputs(result,root)
        if not args.skip_workbook:
            try: build_v53_workbook(result,root)
            except (ImportError,ModuleNotFoundError) as exc: print(f"WORKBOOK SKIPPED: optional artifact_tool environment unavailable: {exc}")
        build_v53_figures(result,root)
    print(json.dumps(result["headline"],indent=2,sort_keys=True));return 0


if __name__ == "__main__":
    # Some optional report-generation dependencies keep background helper threads alive.
    # Flush streams and terminate explicitly after all outputs are safely written so RUN_MODEL
    # completes deterministically in batch/release environments.
    import sys as _sys, os as _os
    _code=v53_main()
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(int(_code))
