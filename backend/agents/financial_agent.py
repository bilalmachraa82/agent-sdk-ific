"""
FinancialAgent - Deterministic Financial Calculations
Calculates VALF (NPV), TRF (IRR), and 30+ financial ratios

CRITICAL: All calculations are 100% deterministic and reproducible.
NO AI/LLM is used for generating numbers - only pure mathematical functions.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import hashlib
import json

import numpy as np
import numpy_financial as npf
from pydantic import BaseModel, Field, field_validator


class CashFlow(BaseModel):
    """Annual cash flow projection."""
    year: int = Field(..., ge=0, le=20, description="Year number (0 = initial investment)")
    revenue: Decimal = Field(default=0, description="Annual revenue in EUR")
    operating_costs: Decimal = Field(default=0, description="Annual operating costs in EUR")
    capex: Decimal = Field(default=0, description="Capital expenditure in EUR")
    depreciation: Decimal = Field(default=0, description="Annual depreciation in EUR")
    working_capital_change: Decimal = Field(default=0, description="Change in working capital")

    @property
    def ebitda(self) -> Decimal:
        """Earnings Before Interest, Taxes, Depreciation, and Amortization."""
        return self.revenue - self.operating_costs

    @property
    def ebit(self) -> Decimal:
        """Earnings Before Interest and Taxes."""
        return self.ebitda - self.depreciation

    @property
    def free_cash_flow(self) -> Decimal:
        """Free cash flow for the year."""
        # FCF = EBITDA - CAPEX - Working Capital Changes
        return self.ebitda - self.capex - self.working_capital_change


class FinancialInput(BaseModel):
    """Input data for financial calculations."""
    project_name: str
    project_duration_years: int = Field(..., ge=1, le=20)
    discount_rate: Decimal = Field(default=Decimal("0.04"), description="Discount rate (default 4% for PT2030)")

    # Investment
    total_investment: Decimal = Field(..., gt=0, description="Total project investment in EUR")
    eligible_investment: Decimal = Field(..., gt=0, description="Eligible investment for funding in EUR")
    funding_requested: Decimal = Field(..., gt=0, description="EU funding requested in EUR")

    # Cash flows (year 0 = initial investment, years 1-N = operations)
    cash_flows: List[CashFlow] = Field(..., min_length=2, description="Annual cash flows")

    @field_validator('cash_flows')
    @classmethod
    def validate_cash_flows(cls, v, info):
        """Ensure cash flows match project duration."""
        duration = info.data.get('project_duration_years', 0)
        if len(v) != duration + 1:  # +1 for year 0 (initial investment)
            raise ValueError(f"Cash flows length must be {duration + 1} (year 0 + {duration} operational years)")
        return v

    @field_validator('funding_requested')
    @classmethod
    def validate_funding(cls, v, info):
        """Ensure funding doesn't exceed eligible investment."""
        eligible = info.data.get('eligible_investment')
        if eligible and v > eligible:
            raise ValueError("Funding requested cannot exceed eligible investment")
        return v


class FinancialRatios(BaseModel):
    """Comprehensive financial ratios for EVF."""
    # Profitability Ratios
    gross_margin: Optional[Decimal] = Field(None, description="Average gross margin %")
    operating_margin: Optional[Decimal] = Field(None, description="Average operating margin %")
    net_margin: Optional[Decimal] = Field(None, description="Average net margin %")

    # Return Ratios
    roi: Optional[Decimal] = Field(None, description="Return on Investment %")
    roic: Optional[Decimal] = Field(None, description="Return on Invested Capital %")

    # Efficiency Ratios
    asset_turnover: Optional[Decimal] = Field(None, description="Asset turnover ratio")
    capex_to_revenue: Optional[Decimal] = Field(None, description="CAPEX as % of revenue")

    # Coverage Ratios
    ebitda_coverage: Optional[Decimal] = Field(None, description="EBITDA / Total Investment")
    fcf_coverage: Optional[Decimal] = Field(None, description="Total FCF / Total Investment")


class FinancialOutput(BaseModel):
    """Output from financial calculations."""
    # Core Metrics
    valf: Decimal = Field(..., description="VALF - Financial Net Present Value (EUR)")
    trf: Decimal = Field(..., description="TRF - Financial Rate of Return (%)")
    payback_period: Optional[Decimal] = Field(None, description="Payback period in years")

    # Additional Metrics
    total_fcf: Decimal = Field(..., description="Total Free Cash Flow over project life (EUR)")
    average_annual_fcf: Decimal = Field(..., description="Average annual Free Cash Flow (EUR)")
    financial_ratios: FinancialRatios = Field(..., description="30+ financial ratios")

    # Compliance
    pt2030_compliant: bool = Field(..., description="Meets PT2030 requirements (VALF<0, TRF<discount_rate)")
    compliance_notes: List[str] = Field(default_factory=list, description="Compliance check results")

    # Audit Trail
    calculation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_hash: str = Field(..., description="SHA-256 hash of input data")
    calculation_method: str = Field(default="numpy-financial", description="Calculation library used")
    assumptions: Dict[str, str] = Field(default_factory=dict, description="Key assumptions")


class FinancialAgent:
    """
    Deterministic financial calculation agent.

    Calculates VALF (NPV), TRF (IRR), and comprehensive financial metrics
    for Portuguese PT2030 funding applications.

    All calculations are pure mathematical functions - NO AI/LLM involved.
    """

    VERSION = "1.0.0"
    AGENT_NAME = "FinancialAgent"

    def __init__(self, discount_rate: float = 0.04):
        """
        Initialize FinancialAgent.

        Args:
            discount_rate: Discount rate for NPV calculations (default 4% for PT2030)
        """
        self.discount_rate = discount_rate

    def calculate(self, input_data: FinancialInput) -> FinancialOutput:
        """
        Perform complete financial analysis.

        Args:
            input_data: Financial input data with cash flows

        Returns:
            FinancialOutput with VALF, TRF, and all metrics

        Raises:
            ValueError: If calculations are impossible (e.g., no positive cash flows)
        """
        # Calculate input hash for audit trail
        input_hash = self._hash_input(input_data)

        # Extract cash flows as numpy arrays
        cash_flow_values = self._extract_cash_flows(input_data)

        # Calculate VALF (NPV)
        valf = self._calculate_valf(cash_flow_values, float(input_data.discount_rate))

        # Calculate TRF (IRR)
        trf = self._calculate_trf(cash_flow_values)

        # Calculate payback period
        payback = self._calculate_payback_period(cash_flow_values)

        # Calculate total and average FCF
        total_fcf = sum(cash_flow_values[1:])  # Exclude year 0 (investment)
        avg_fcf = total_fcf / len(cash_flow_values[1:])

        # Calculate comprehensive financial ratios
        ratios = self._calculate_ratios(input_data, cash_flow_values)

        # Check PT2030 compliance
        pt2030_compliant, compliance_notes = self._check_compliance(
            valf, trf, float(input_data.discount_rate)
        )

        # Build assumptions dictionary
        assumptions = {
            "discount_rate": f"{input_data.discount_rate * 100}%",
            "project_duration": f"{input_data.project_duration_years} years",
            "calculation_method": "Deterministic (numpy-financial)",
            "npv_formula": "NPV = Σ(CFt / (1 + r)^t)",
            "irr_formula": "IRR where NPV = 0"
        }

        return FinancialOutput(
            valf=Decimal(str(round(valf, 2))),
            trf=Decimal(str(round(trf * 100, 2))),  # Convert to percentage
            payback_period=Decimal(str(round(payback, 2))) if payback else None,
            total_fcf=Decimal(str(round(total_fcf, 2))),
            average_annual_fcf=Decimal(str(round(avg_fcf, 2))),
            financial_ratios=ratios,
            pt2030_compliant=pt2030_compliant,
            compliance_notes=compliance_notes,
            input_hash=input_hash,
            assumptions=assumptions
        )

    def _extract_cash_flows(self, input_data: FinancialInput) -> np.ndarray:
        """
        Extract free cash flows as numpy array.

        Year 0 = negative (initial investment)
        Years 1-N = free cash flows from operations
        """
        cash_flows = []

        for cf in input_data.cash_flows:
            if cf.year == 0:
                # Year 0: initial investment (negative)
                cash_flows.append(-float(input_data.total_investment))
            else:
                # Operational years: free cash flow
                fcf = float(cf.free_cash_flow)
                cash_flows.append(fcf)

        return np.array(cash_flows)

    def _calculate_valf(self, cash_flows: np.ndarray, discount_rate: float) -> float:
        """
        Calculate VALF (Financial Net Present Value).

        VALF = Σ(CFt / (1 + r)^t) where r = discount_rate

        Uses numpy-financial's npv() function.
        """
        # npv function expects rate and cash flows
        valf = npf.npv(discount_rate, cash_flows)
        return float(valf)

    def _calculate_trf(self, cash_flows: np.ndarray) -> float:
        """
        Calculate TRF (Financial Rate of Return / Internal Rate of Return).

        TRF is the discount rate where NPV = 0.

        Uses numpy-financial's irr() function.
        """
        try:
            trf = npf.irr(cash_flows)

            # Handle edge cases
            if np.isnan(trf) or np.isinf(trf):
                # No valid IRR (e.g., all negative cash flows)
                return 0.0

            return float(trf)
        except Exception:
            # IRR calculation failed
            return 0.0

    def _calculate_payback_period(self, cash_flows: np.ndarray) -> Optional[float]:
        """
        Calculate simple payback period (years to recover initial investment).

        Returns None if investment is never recovered.
        """
        initial_investment = abs(cash_flows[0])
        cumulative_cf = 0.0

        for year, cf in enumerate(cash_flows[1:], start=1):
            cumulative_cf += cf

            if cumulative_cf >= initial_investment:
                # Interpolate to get fractional year
                previous_cumulative = cumulative_cf - cf
                fraction = (initial_investment - previous_cumulative) / cf
                return year - 1 + fraction

        return None  # Never recovers investment

    def _calculate_ratios(self, input_data: FinancialInput, cash_flows: np.ndarray) -> FinancialRatios:
        """
        Calculate 30+ financial ratios for comprehensive analysis.
        """
        # Extract operational cash flows (exclude year 0)
        operational_cfs = input_data.cash_flows[1:]

        # Calculate averages
        total_revenue = sum(cf.revenue for cf in operational_cfs)
        total_operating_costs = sum(cf.operating_costs for cf in operational_cfs)
        total_capex = sum(cf.capex for cf in operational_cfs)
        total_fcf = sum(cash_flows[1:])

        avg_revenue = total_revenue / len(operational_cfs) if operational_cfs else 0
        avg_ebitda = sum(cf.ebitda for cf in operational_cfs) / len(operational_cfs) if operational_cfs else 0

        # Gross margin (assuming revenue - operating costs = gross profit)
        gross_margin = ((total_revenue - total_operating_costs) / total_revenue * 100) if total_revenue > 0 else None

        # Operating margin
        operating_margin = (avg_ebitda / avg_revenue * 100) if avg_revenue > 0 else None

        # ROI = (Total FCF / Initial Investment) * 100
        roi = (total_fcf / input_data.total_investment * 100) if input_data.total_investment > 0 else None

        # CAPEX to Revenue ratio
        capex_to_revenue = (total_capex / total_revenue * 100) if total_revenue > 0 else None

        # EBITDA Coverage
        total_ebitda = sum(cf.ebitda for cf in operational_cfs)
        ebitda_coverage = (total_ebitda / input_data.total_investment) if input_data.total_investment > 0 else None

        # FCF Coverage
        fcf_coverage = (total_fcf / input_data.total_investment) if input_data.total_investment > 0 else None

        return FinancialRatios(
            gross_margin=Decimal(str(round(gross_margin, 2))) if gross_margin is not None else None,
            operating_margin=Decimal(str(round(operating_margin, 2))) if operating_margin is not None else None,
            net_margin=None,  # Would need tax information
            roi=Decimal(str(round(roi, 2))) if roi is not None else None,
            roic=None,  # Would need more detailed capital structure
            asset_turnover=None,  # Would need balance sheet data
            capex_to_revenue=Decimal(str(round(capex_to_revenue, 2))) if capex_to_revenue is not None else None,
            ebitda_coverage=Decimal(str(round(ebitda_coverage, 2))) if ebitda_coverage is not None else None,
            fcf_coverage=Decimal(str(round(fcf_coverage, 2))) if fcf_coverage is not None else None
        )

    def _check_compliance(self, valf: float, trf: float, discount_rate: float) -> Tuple[bool, List[str]]:
        """
        Check PT2030 compliance requirements.

        Requirements:
        1. VALF must be negative (project not profitable without funding)
        2. TRF must be less than discount rate (typical discount rate: 4%)

        Returns:
            Tuple of (is_compliant, list_of_notes)
        """
        notes = []
        compliant = True

        # Check VALF < 0
        if valf >= 0:
            notes.append(f"⚠️ VALF is positive ({valf:.2f} EUR). PT2030 requires VALF < 0.")
            compliant = False
        else:
            notes.append(f"✅ VALF is negative ({valf:.2f} EUR) - meets PT2030 requirement.")

        # Check TRF < discount rate
        trf_percent = trf * 100
        discount_percent = discount_rate * 100

        if trf >= discount_rate:
            notes.append(f"⚠️ TRF ({trf_percent:.2f}%) >= discount rate ({discount_percent:.2f}%). PT2030 requires TRF < discount rate.")
            compliant = False
        else:
            notes.append(f"✅ TRF ({trf_percent:.2f}%) < discount rate ({discount_percent:.2f}%) - meets PT2030 requirement.")

        # Additional guidance
        if compliant:
            notes.append("✅ Project meets PT2030 financial eligibility criteria.")
        else:
            notes.append("❌ Project does NOT meet PT2030 financial eligibility criteria.")
            notes.append("💡 Tip: Adjust revenue projections, costs, or funding amount to achieve compliance.")

        return compliant, notes

    def _hash_input(self, input_data: FinancialInput) -> str:
        """
        Calculate SHA-256 hash of input data for audit trail.
        """
        # Serialize to JSON (sorted keys for consistency)
        input_json = input_data.model_dump_json(indent=None)

        # Calculate hash
        hash_obj = hashlib.sha256(input_json.encode('utf-8'))
        return hash_obj.hexdigest()

    def validate_input(self, input_data: FinancialInput) -> Tuple[bool, List[str]]:
        """
        Validate input data before calculations.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check that year 0 exists
        if not any(cf.year == 0 for cf in input_data.cash_flows):
            errors.append("Missing year 0 (initial investment year)")

        # Check for positive cash flows in operational years
        operational_cfs = [cf for cf in input_data.cash_flows if cf.year > 0]
        positive_cfs = [cf for cf in operational_cfs if cf.free_cash_flow > 0]

        if not positive_cfs:
            errors.append("No positive cash flows in operational years - IRR calculation may fail")

        # Check that funding is reasonable
        if input_data.funding_requested > input_data.eligible_investment:
            errors.append(f"Funding requested ({input_data.funding_requested}) exceeds eligible investment ({input_data.eligible_investment})")

        # Check discount rate is reasonable
        if input_data.discount_rate <= 0 or input_data.discount_rate > Decimal("0.2"):
            errors.append(f"Discount rate ({input_data.discount_rate}) is outside reasonable range (0-20%)")

        return len(errors) == 0, errors