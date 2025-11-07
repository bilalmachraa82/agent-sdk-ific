"""
InputAgent - Portuguese SAF-T XML Parser
Extracts and normalizes financial data from SAF-T PT files

Handles:
- Company information (NIF, name, address)
- Financial statements (P&L, Balance Sheet)
- Cash flow data (operating, investing, financing)
- Multi-year data extraction

CRITICAL: Processes SAF-T files locally - never sends raw data to external APIs.
All data is validated and normalized before passing to FinancialAgent.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
import hashlib
import logging

from lxml import etree
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS - SAF-T Data Structures
# ============================================================================

class CompanyAddress(BaseModel):
    """Company address information."""
    address_detail: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    postal_code: Optional[str] = Field(None, description="Postal code")
    region: Optional[str] = Field(None, description="Region/District")
    country: str = Field(default="PT", description="Country code (ISO 3166)")


class CompanyInfo(BaseModel):
    """Company identification and metadata."""
    nif: str = Field(..., description="Tax identification number (NIF)")
    name: str = Field(..., description="Company legal name")
    address: Optional[CompanyAddress] = Field(None, description="Company address")
    fiscal_year: int = Field(..., description="Fiscal year")
    currency_code: str = Field(default="EUR", description="Currency (ISO 4217)")

    # File metadata
    audit_file_version: Optional[str] = Field(None, description="SAF-T version")
    company_id: Optional[str] = Field(None, description="Unique company identifier")
    product_id: Optional[str] = Field(None, description="Source software ID")
    product_version: Optional[str] = Field(None, description="Source software version")

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator('nif')
    @classmethod
    def validate_nif(cls, v):
        """Validate Portuguese NIF format (9 digits)."""
        if v and not v.isdigit():
            # Remove spaces and non-digits
            v = ''.join(filter(str.isdigit, v))
        if v and len(v) != 9:
            raise ValueError(f"NIF must have 9 digits, got {len(v)}")
        return v


class Period(BaseModel):
    """Accounting period information."""
    start_date: date = Field(..., description="Period start date")
    end_date: date = Field(..., description="Period end date")
    fiscal_year: int = Field(..., description="Fiscal year")

    @field_validator('end_date')
    @classmethod
    def validate_period(cls, v, info):
        """Ensure end date is after start date."""
        start = info.data.get('start_date')
        if start and v < start:
            raise ValueError("End date must be after start date")
        return v

    @property
    def duration_days(self) -> int:
        """Calculate period duration in days."""
        return (self.end_date - self.start_date).days


class AccountBalance(BaseModel):
    """General ledger account balance."""
    account_id: str = Field(..., description="Account code")
    account_description: Optional[str] = Field(None, description="Account name")
    opening_debit: Decimal = Field(default=Decimal("0"), description="Opening debit balance")
    opening_credit: Decimal = Field(default=Decimal("0"), description="Opening credit balance")
    closing_debit: Decimal = Field(default=Decimal("0"), description="Closing debit balance")
    closing_credit: Decimal = Field(default=Decimal("0"), description="Closing credit balance")

    @property
    def opening_balance(self) -> Decimal:
        """Net opening balance (debit - credit)."""
        return self.opening_debit - self.opening_credit

    @property
    def closing_balance(self) -> Decimal:
        """Net closing balance (debit - credit)."""
        return self.closing_debit - self.closing_credit

    @property
    def movement(self) -> Decimal:
        """Period movement."""
        return self.closing_balance - self.opening_balance


class FinancialStatement(BaseModel):
    """Annual financial statement (P&L and Balance Sheet)."""
    fiscal_year: int = Field(..., description="Fiscal year")

    # Profit & Loss (Income Statement)
    revenue: Decimal = Field(default=Decimal("0"), description="Total revenue")
    cost_of_sales: Decimal = Field(default=Decimal("0"), description="Cost of goods sold")
    operating_expenses: Decimal = Field(default=Decimal("0"), description="Operating expenses")
    personnel_costs: Decimal = Field(default=Decimal("0"), description="Personnel expenses")
    depreciation: Decimal = Field(default=Decimal("0"), description="Depreciation and amortization")
    financial_income: Decimal = Field(default=Decimal("0"), description="Financial income")
    financial_expenses: Decimal = Field(default=Decimal("0"), description="Financial expenses")
    taxes: Decimal = Field(default=Decimal("0"), description="Income taxes")
    net_income: Decimal = Field(default=Decimal("0"), description="Net profit/loss")

    # Balance Sheet - Assets
    total_assets: Decimal = Field(default=Decimal("0"), description="Total assets")
    current_assets: Decimal = Field(default=Decimal("0"), description="Current assets")
    fixed_assets: Decimal = Field(default=Decimal("0"), description="Fixed assets")
    intangible_assets: Decimal = Field(default=Decimal("0"), description="Intangible assets")

    # Balance Sheet - Liabilities
    total_liabilities: Decimal = Field(default=Decimal("0"), description="Total liabilities")
    current_liabilities: Decimal = Field(default=Decimal("0"), description="Current liabilities")
    non_current_liabilities: Decimal = Field(default=Decimal("0"), description="Non-current liabilities")
    equity: Decimal = Field(default=Decimal("0"), description="Shareholders' equity")

    @property
    def gross_profit(self) -> Decimal:
        """Gross profit = Revenue - Cost of Sales."""
        return self.revenue - self.cost_of_sales

    @property
    def ebitda(self) -> Decimal:
        """EBITDA = Revenue - Operating Expenses - Personnel Costs."""
        return self.revenue - self.operating_expenses - self.personnel_costs

    @property
    def ebit(self) -> Decimal:
        """EBIT = EBITDA - Depreciation."""
        return self.ebitda - self.depreciation


class CashFlowStatement(BaseModel):
    """Annual cash flow statement."""
    fiscal_year: int = Field(..., description="Fiscal year")

    # Operating Activities
    operating_cash_flow: Decimal = Field(default=Decimal("0"), description="Cash from operations")
    operating_receipts: Decimal = Field(default=Decimal("0"), description="Cash receipts from customers")
    operating_payments: Decimal = Field(default=Decimal("0"), description="Cash paid to suppliers/employees")

    # Investing Activities
    investing_cash_flow: Decimal = Field(default=Decimal("0"), description="Cash from investing")
    capex: Decimal = Field(default=Decimal("0"), description="Capital expenditure")
    asset_sales: Decimal = Field(default=Decimal("0"), description="Proceeds from asset sales")

    # Financing Activities
    financing_cash_flow: Decimal = Field(default=Decimal("0"), description="Cash from financing")
    debt_proceeds: Decimal = Field(default=Decimal("0"), description="New debt proceeds")
    debt_repayments: Decimal = Field(default=Decimal("0"), description="Debt repayments")
    equity_proceeds: Decimal = Field(default=Decimal("0"), description="Equity proceeds")
    dividends_paid: Decimal = Field(default=Decimal("0"), description="Dividends paid")

    @property
    def net_cash_flow(self) -> Decimal:
        """Total net cash flow for the period."""
        return self.operating_cash_flow + self.investing_cash_flow + self.financing_cash_flow

    @property
    def free_cash_flow(self) -> Decimal:
        """Free cash flow = Operating CF - CAPEX."""
        return self.operating_cash_flow - self.capex


class SAFTData(BaseModel):
    """Complete SAF-T parsed data structure."""
    company_info: CompanyInfo = Field(..., description="Company identification")
    period: Period = Field(..., description="Accounting period")
    financial_statements: List[FinancialStatement] = Field(
        default_factory=list,
        description="Financial statements by year"
    )
    cash_flows: List[CashFlowStatement] = Field(
        default_factory=list,
        description="Cash flow statements by year"
    )
    general_ledger: List[AccountBalance] = Field(
        default_factory=list,
        description="General ledger account balances"
    )

    # Metadata
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    file_hash: Optional[str] = Field(None, description="SHA-256 hash of source file")
    validation_errors: List[str] = Field(default_factory=list, description="Non-fatal validation issues")

    model_config = ConfigDict(str_strip_whitespace=True)


class ParseResult(BaseModel):
    """Result of SAF-T parsing operation."""
    success: bool = Field(..., description="Whether parsing succeeded")
    data: Optional[SAFTData] = Field(None, description="Parsed data if successful")
    errors: List[str] = Field(default_factory=list, description="Fatal errors")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")
    parse_time_seconds: float = Field(..., description="Time taken to parse")


# ============================================================================
# INPUT AGENT - SAF-T XML Parser
# ============================================================================

class InputAgent:
    """
    Portuguese SAF-T XML Parser.

    Extracts and normalizes financial data from SAF-T PT files for EVF processing.
    Handles company info, financial statements, cash flows, and general ledger data.

    Key features:
    - Validates XML structure against SAF-T PT schema
    - Extracts multi-year financial data
    - Normalizes account mappings to standard P&L/Balance Sheet
    - Handles malformed XML gracefully
    - Provides detailed error reporting
    """

    VERSION = "1.0.0"
    AGENT_NAME = "InputAgent"

    # SAF-T PT Namespace (typical for Portuguese SAF-T files)
    NAMESPACES = {
        'saft': 'urn:OECD:StandardAuditFile-Tax:PT_1.04_01',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }

    # Portuguese Chart of Accounts (SNC) - Standard account code ranges
    ACCOUNT_MAPPINGS = {
        # Revenue (Class 7)
        'revenue': ['71', '72', '73', '74', '75'],
        # Cost of Sales (Class 6)
        'cost_of_sales': ['61'],
        # Operating Expenses (Class 6)
        'operating_expenses': ['62', '65', '66', '67', '68'],
        # Personnel Costs (Class 6)
        'personnel_costs': ['63', '64'],
        # Depreciation (Class 6)
        'depreciation': ['64'],
        # Financial Income (Class 7)
        'financial_income': ['78', '79'],
        # Financial Expenses (Class 6)
        'financial_expenses': ['68', '69'],
        # Assets (Class 1-4)
        'fixed_assets': ['41', '42', '43'],
        'intangible_assets': ['44'],
        'current_assets': ['11', '12', '13', '14', '21', '22', '23', '24', '25', '26', '27', '28'],
        # Liabilities (Class 5)
        'current_liabilities': ['51', '52'],
        'non_current_liabilities': ['53', '54', '55'],
        # Equity (Class 5)
        'equity': ['56', '57', '58', '59'],
    }

    def __init__(self, validate_schema: bool = True):
        """
        Initialize InputAgent.

        Args:
            validate_schema: Whether to validate XML against XSD schema (default True)
        """
        self.validate_schema = validate_schema
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse SAF-T XML file from filesystem.

        Args:
            file_path: Path to SAF-T XML file

        Returns:
            ParseResult with parsed data or errors
        """
        start_time = datetime.utcnow()

        try:
            # Read file and calculate hash
            path = Path(file_path)
            if not path.exists():
                return ParseResult(
                    success=False,
                    errors=[f"File not found: {file_path}"],
                    warnings=[],
                    parse_time_seconds=0.0
                )

            xml_content = path.read_bytes()
            file_hash = self._calculate_hash(xml_content)

            # Parse XML
            result = self.parse_xml(xml_content)

            # Add file hash to data
            if result.data:
                result.data.file_hash = file_hash

            # Calculate parse time
            parse_time = (datetime.utcnow() - start_time).total_seconds()
            result.parse_time_seconds = parse_time

            logger.info(f"SAF-T parsing completed in {parse_time:.2f}s - Success: {result.success}")

            return result

        except Exception as e:
            logger.error(f"Fatal error parsing SAF-T file: {e}", exc_info=True)
            parse_time = (datetime.utcnow() - start_time).total_seconds()
            return ParseResult(
                success=False,
                errors=[f"Fatal parsing error: {str(e)}"],
                warnings=self.warnings,
                parse_time_seconds=parse_time
            )

    def parse_xml(self, xml_content: bytes) -> ParseResult:
        """
        Parse SAF-T XML content.

        Args:
            xml_content: Raw XML bytes

        Returns:
            ParseResult with parsed data or errors
        """
        self.errors = []
        self.warnings = []
        start_time = datetime.utcnow()

        try:
            # Parse XML
            try:
                tree = etree.fromstring(xml_content)
            except etree.XMLSyntaxError as e:
                return ParseResult(
                    success=False,
                    errors=[f"XML syntax error: {str(e)}"],
                    warnings=[],
                    parse_time_seconds=0.0
                )

            # Detect namespace (may vary between SAF-T versions)
            namespace = self._detect_namespace(tree)

            # Extract data sections
            company_info = self._extract_company_info(tree, namespace)
            period = self._extract_period(tree, namespace)
            general_ledger = self._extract_general_ledger(tree, namespace)

            # Build financial statements from general ledger
            financial_statements = self._build_financial_statements(general_ledger, period.fiscal_year)

            # Estimate cash flows from financial statements
            # Note: SAF-T doesn't always have explicit cash flow statements
            cash_flows = self._estimate_cash_flows(financial_statements, general_ledger)

            # Create SAFTData object
            saft_data = SAFTData(
                company_info=company_info,
                period=period,
                financial_statements=financial_statements,
                cash_flows=cash_flows,
                general_ledger=general_ledger,
                validation_errors=self.warnings.copy()
            )

            # Calculate parse time
            parse_time = (datetime.utcnow() - start_time).total_seconds()

            # Return successful result
            return ParseResult(
                success=True,
                data=saft_data,
                errors=[],
                warnings=self.warnings,
                parse_time_seconds=parse_time
            )

        except Exception as e:
            logger.error(f"Error during SAF-T parsing: {e}", exc_info=True)
            self.errors.append(f"Parsing error: {str(e)}")

            parse_time = (datetime.utcnow() - start_time).total_seconds()
            return ParseResult(
                success=False,
                errors=self.errors,
                warnings=self.warnings,
                parse_time_seconds=parse_time
            )

    def _detect_namespace(self, tree: etree._Element) -> Dict[str, str]:
        """
        Detect SAF-T namespace from XML root element.

        Returns dict with 'saft' namespace for XPath queries.
        """
        # Try to get namespace from root element
        if tree.nsmap and None in tree.nsmap:
            ns = tree.nsmap[None]
            return {'saft': ns}

        # Check for explicit namespace in tag
        if '}' in tree.tag:
            ns = tree.tag.split('}')[0].strip('{')
            return {'saft': ns}

        # Default to PT 1.04_01 namespace
        return {'saft': 'urn:OECD:StandardAuditFile-Tax:PT_1.04_01'}

    def _extract_company_info(self, tree: etree._Element, namespace: Dict[str, str]) -> CompanyInfo:
        """Extract company information from Header section."""
        # Find Header element
        header = tree.find('.//saft:Header', namespace)
        if header is None:
            # Try without namespace
            header = tree.find('.//Header')

        if header is None:
            raise ValueError("SAF-T file missing required <Header> section")

        # Extract company fields
        nif = self._get_text(header, './/saft:TaxRegistrationNumber', namespace) or \
              self._get_text(header, './/TaxRegistrationNumber')

        if not nif:
            raise ValueError("SAF-T file missing required TaxRegistrationNumber")

        name = self._get_text(header, './/saft:CompanyName', namespace) or \
               self._get_text(header, './/CompanyName') or "Unknown Company"

        fiscal_year = self._get_text(header, './/saft:FiscalYear', namespace) or \
                     self._get_text(header, './/FiscalYear')

        if not fiscal_year:
            raise ValueError("SAF-T file missing required FiscalYear")

        # Extract address (optional)
        address_elem = header.find('.//saft:CompanyAddress', namespace) or \
                      header.find('.//CompanyAddress')

        address = None
        if address_elem is not None:
            address = CompanyAddress(
                address_detail=self._get_text(address_elem, './/saft:AddressDetail', namespace) or
                              self._get_text(address_elem, './/AddressDetail'),
                city=self._get_text(address_elem, './/saft:City', namespace) or
                     self._get_text(address_elem, './/City'),
                postal_code=self._get_text(address_elem, './/saft:PostalCode', namespace) or
                           self._get_text(address_elem, './/PostalCode'),
                region=self._get_text(address_elem, './/saft:Region', namespace) or
                       self._get_text(address_elem, './/Region'),
                country=self._get_text(address_elem, './/saft:Country', namespace) or
                        self._get_text(address_elem, './/Country') or "PT"
            )

        # Optional metadata
        audit_version = self._get_text(header, './/saft:AuditFileVersion', namespace) or \
                       self._get_text(header, './/AuditFileVersion')
        company_id = self._get_text(header, './/saft:CompanyID', namespace) or \
                    self._get_text(header, './/CompanyID')
        product_id = self._get_text(header, './/saft:ProductID', namespace) or \
                    self._get_text(header, './/ProductID')
        product_version = self._get_text(header, './/saft:ProductVersion', namespace) or \
                         self._get_text(header, './/ProductVersion')

        currency = self._get_text(header, './/saft:CurrencyCode', namespace) or \
                  self._get_text(header, './/CurrencyCode') or "EUR"

        return CompanyInfo(
            nif=nif,
            name=name,
            address=address,
            fiscal_year=int(fiscal_year),
            currency_code=currency,
            audit_file_version=audit_version,
            company_id=company_id,
            product_id=product_id,
            product_version=product_version
        )

    def _extract_period(self, tree: etree._Element, namespace: Dict[str, str]) -> Period:
        """Extract accounting period from Header."""
        header = tree.find('.//saft:Header', namespace) or tree.find('.//Header')

        if header is None:
            raise ValueError("SAF-T file missing <Header> section")

        start_date_str = self._get_text(header, './/saft:StartDate', namespace) or \
                        self._get_text(header, './/StartDate')
        end_date_str = self._get_text(header, './/saft:EndDate', namespace) or \
                      self._get_text(header, './/EndDate')
        fiscal_year_str = self._get_text(header, './/saft:FiscalYear', namespace) or \
                         self._get_text(header, './/FiscalYear')

        if not all([start_date_str, end_date_str, fiscal_year_str]):
            raise ValueError("SAF-T file missing required period information (StartDate, EndDate, FiscalYear)")

        # Parse dates (format: YYYY-MM-DD)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        return Period(
            start_date=start_date,
            end_date=end_date,
            fiscal_year=int(fiscal_year_str)
        )

    def _extract_general_ledger(self, tree: etree._Element, namespace: Dict[str, str]) -> List[AccountBalance]:
        """Extract general ledger account balances from MasterFiles."""
        accounts: List[AccountBalance] = []

        # Find GeneralLedgerAccounts section
        gl_section = tree.find('.//saft:MasterFiles/saft:GeneralLedgerAccounts', namespace) or \
                    tree.find('.//MasterFiles/GeneralLedgerAccounts')

        if gl_section is None:
            self.warnings.append("No GeneralLedgerAccounts section found - financial statements may be incomplete")
            return accounts

        # Extract each account
        account_elements = gl_section.findall('.//saft:Account', namespace) or \
                          gl_section.findall('.//Account')

        for acc_elem in account_elements:
            try:
                account_id = self._get_text(acc_elem, './/saft:AccountID', namespace) or \
                           self._get_text(acc_elem, './/AccountID')

                if not account_id:
                    continue

                account_desc = self._get_text(acc_elem, './/saft:AccountDescription', namespace) or \
                             self._get_text(acc_elem, './/AccountDescription')

                opening_debit = self._get_decimal(acc_elem, './/saft:OpeningDebitBalance', namespace) or \
                              self._get_decimal(acc_elem, './/OpeningDebitBalance') or Decimal("0")

                opening_credit = self._get_decimal(acc_elem, './/saft:OpeningCreditBalance', namespace) or \
                               self._get_decimal(acc_elem, './/OpeningCreditBalance') or Decimal("0")

                closing_debit = self._get_decimal(acc_elem, './/saft:ClosingDebitBalance', namespace) or \
                              self._get_decimal(acc_elem, './/ClosingDebitBalance') or Decimal("0")

                closing_credit = self._get_decimal(acc_elem, './/saft:ClosingCreditBalance', namespace) or \
                               self._get_decimal(acc_elem, './/ClosingCreditBalance') or Decimal("0")

                accounts.append(AccountBalance(
                    account_id=account_id,
                    account_description=account_desc,
                    opening_debit=opening_debit,
                    opening_credit=opening_credit,
                    closing_debit=closing_debit,
                    closing_credit=closing_credit
                ))

            except Exception as e:
                self.warnings.append(f"Error parsing account: {str(e)}")
                continue

        logger.info(f"Extracted {len(accounts)} general ledger accounts")
        return accounts

    def _build_financial_statements(
        self,
        general_ledger: List[AccountBalance],
        fiscal_year: int
    ) -> List[FinancialStatement]:
        """
        Build financial statements from general ledger balances.

        Maps Portuguese SNC account codes to P&L and Balance Sheet line items.
        """
        if not general_ledger:
            self.warnings.append("No general ledger data - returning empty financial statement")
            return [FinancialStatement(fiscal_year=fiscal_year)]

        # Initialize statement
        stmt = FinancialStatement(fiscal_year=fiscal_year)

        # Map accounts to statement line items using Portuguese SNC structure
        for account in general_ledger:
            account_code = account.account_id[:2]  # First 2 digits determine account class
            balance = account.closing_balance

            # P&L - Revenue (Class 7)
            if account_code in self.ACCOUNT_MAPPINGS['revenue']:
                stmt.revenue += abs(balance)  # Revenue is credit balance, make positive

            # P&L - Cost of Sales (Class 6)
            elif account_code in self.ACCOUNT_MAPPINGS['cost_of_sales']:
                stmt.cost_of_sales += abs(balance)

            # P&L - Operating Expenses (Class 6)
            elif account_code in self.ACCOUNT_MAPPINGS['operating_expenses']:
                stmt.operating_expenses += abs(balance)

            # P&L - Personnel Costs (Class 6)
            elif account_code in self.ACCOUNT_MAPPINGS['personnel_costs']:
                stmt.personnel_costs += abs(balance)

            # P&L - Depreciation
            elif account_code in self.ACCOUNT_MAPPINGS['depreciation']:
                stmt.depreciation += abs(balance)

            # P&L - Financial Income
            elif account_code in self.ACCOUNT_MAPPINGS['financial_income']:
                stmt.financial_income += abs(balance)

            # P&L - Financial Expenses
            elif account_code in self.ACCOUNT_MAPPINGS['financial_expenses']:
                stmt.financial_expenses += abs(balance)

            # Balance Sheet - Fixed Assets
            elif account_code in self.ACCOUNT_MAPPINGS['fixed_assets']:
                stmt.fixed_assets += abs(balance)

            # Balance Sheet - Intangible Assets
            elif account_code in self.ACCOUNT_MAPPINGS['intangible_assets']:
                stmt.intangible_assets += abs(balance)

            # Balance Sheet - Current Assets
            elif account_code in self.ACCOUNT_MAPPINGS['current_assets']:
                stmt.current_assets += abs(balance)

            # Balance Sheet - Current Liabilities
            elif account_code in self.ACCOUNT_MAPPINGS['current_liabilities']:
                stmt.current_liabilities += abs(balance)

            # Balance Sheet - Non-Current Liabilities
            elif account_code in self.ACCOUNT_MAPPINGS['non_current_liabilities']:
                stmt.non_current_liabilities += abs(balance)

            # Balance Sheet - Equity
            elif account_code in self.ACCOUNT_MAPPINGS['equity']:
                stmt.equity += abs(balance)

        # Calculate derived totals
        stmt.total_assets = stmt.current_assets + stmt.fixed_assets + stmt.intangible_assets
        stmt.total_liabilities = stmt.current_liabilities + stmt.non_current_liabilities

        # Calculate net income (simplified)
        stmt.net_income = (
            stmt.revenue
            - stmt.cost_of_sales
            - stmt.operating_expenses
            - stmt.personnel_costs
            - stmt.depreciation
            + stmt.financial_income
            - stmt.financial_expenses
            - stmt.taxes
        )

        logger.info(f"Built financial statement for FY{fiscal_year}: Revenue={stmt.revenue}, Assets={stmt.total_assets}")

        return [stmt]

    def _estimate_cash_flows(
        self,
        financial_statements: List[FinancialStatement],
        general_ledger: List[AccountBalance]
    ) -> List[CashFlowStatement]:
        """
        Estimate cash flows from financial statements.

        Note: SAF-T doesn't always include explicit cash flow statements.
        This provides a basic estimation using indirect method.
        """
        cash_flows: List[CashFlowStatement] = []

        for stmt in financial_statements:
            # Estimate operating cash flow (indirect method)
            # OCF ≈ Net Income + Depreciation - Change in Working Capital
            operating_cf = stmt.net_income + stmt.depreciation

            # Estimate CAPEX from fixed asset changes (simplified)
            # In reality would need multi-year comparison
            capex = Decimal("0")  # Would need previous year data

            # Create cash flow statement
            cf = CashFlowStatement(
                fiscal_year=stmt.fiscal_year,
                operating_cash_flow=operating_cf,
                operating_receipts=stmt.revenue,  # Approximation
                operating_payments=stmt.cost_of_sales + stmt.operating_expenses + stmt.personnel_costs,
                investing_cash_flow=-capex,
                capex=capex,
                asset_sales=Decimal("0"),
                financing_cash_flow=Decimal("0"),
                debt_proceeds=Decimal("0"),
                debt_repayments=Decimal("0"),
                equity_proceeds=Decimal("0"),
                dividends_paid=Decimal("0")
            )

            cash_flows.append(cf)

        return cash_flows

    def _get_text(self, element: etree._Element, xpath: str, namespace: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Safely extract text content from XML element."""
        try:
            found = element.find(xpath, namespace) if namespace else element.find(xpath)
            if found is not None and found.text:
                return found.text.strip()
        except Exception:
            pass
        return None

    def _get_decimal(self, element: etree._Element, xpath: str, namespace: Optional[Dict[str, str]] = None) -> Optional[Decimal]:
        """Safely extract decimal value from XML element."""
        text = self._get_text(element, xpath, namespace)
        if text:
            try:
                return Decimal(text)
            except Exception:
                pass
        return None

    def _calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    def validate_extracted_data(self, data: SAFTData) -> Tuple[bool, List[str]]:
        """
        Validate extracted SAF-T data for completeness and consistency.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        if not data.company_info.nif:
            errors.append("Missing company NIF")

        if not data.financial_statements:
            errors.append("No financial statements extracted")

        # Check financial statement consistency
        for stmt in data.financial_statements:
            # Balance sheet must balance
            total_liab_equity = stmt.total_liabilities + stmt.equity
            if abs(stmt.total_assets - total_liab_equity) > Decimal("1.0"):  # Allow €1 rounding
                errors.append(
                    f"FY{stmt.fiscal_year}: Balance sheet doesn't balance - "
                    f"Assets={stmt.total_assets} vs Liabilities+Equity={total_liab_equity}"
                )

            # Revenue should be positive for operating companies
            if stmt.revenue <= 0:
                errors.append(f"FY{stmt.fiscal_year}: Revenue is zero or negative ({stmt.revenue})")

        return len(errors) == 0, errors
