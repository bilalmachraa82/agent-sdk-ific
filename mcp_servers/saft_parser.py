#!/usr/bin/env python3
"""
SAF-T Parser MCP Server
Processes Portuguese SAF-T (Standard Audit File for Tax) XML files locally
Ensures data privacy by processing sensitive financial data without external API calls
"""

import asyncio
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional
import hashlib

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

class SAFTParser:
    """Parser for Portuguese SAF-T XML files"""

    def __init__(self):
        self.namespaces = {
            'saft': 'urn:OECD:StandardAuditFile-Tax:PT_1.04_01',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }

    def parse_header(self, root: ET.Element) -> Dict[str, Any]:
        """Extract header information from SAF-T"""
        header = root.find('.//saft:Header', self.namespaces)
        if not header:
            return {}

        return {
            'audit_file_version': self._get_text(header, 'saft:AuditFileVersion'),
            'company_id': self._get_text(header, 'saft:CompanyID'),
            'tax_registration_number': self._get_text(header, 'saft:TaxRegistrationNumber'),
            'tax_accounting_basis': self._get_text(header, 'saft:TaxAccountingBasis'),
            'company_name': self._get_text(header, 'saft:CompanyName'),
            'fiscal_year': self._get_text(header, 'saft:FiscalYear'),
            'start_date': self._get_text(header, 'saft:StartDate'),
            'end_date': self._get_text(header, 'saft:EndDate'),
            'currency_code': self._get_text(header, 'saft:CurrencyCode'),
            'date_created': self._get_text(header, 'saft:DateCreated'),
            'product_company_tax_id': self._get_text(header, 'saft:ProductCompanyTaxID'),
            'product_id': self._get_text(header, 'saft:ProductID'),
            'product_version': self._get_text(header, 'saft:ProductVersion')
        }

    def parse_customers(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract customer information"""
        customers = []
        for customer in root.findall('.//saft:Customer', self.namespaces):
            customers.append({
                'customer_id': self._get_text(customer, 'saft:CustomerID'),
                'account_id': self._get_text(customer, 'saft:AccountID'),
                'customer_tax_id': self._get_text(customer, 'saft:CustomerTaxID'),
                'company_name': self._get_text(customer, 'saft:CompanyName'),
                'contact': self._get_text(customer, 'saft:Contact'),
                'billing_address': self._parse_address(customer.find('saft:BillingAddress', self.namespaces)),
                'ship_to_address': self._parse_address(customer.find('saft:ShipToAddress', self.namespaces)),
                'telephone': self._get_text(customer, 'saft:Telephone'),
                'fax': self._get_text(customer, 'saft:Fax'),
                'email': self._get_text(customer, 'saft:Email'),
                'website': self._get_text(customer, 'saft:Website'),
                'self_billing_indicator': self._get_text(customer, 'saft:SelfBillingIndicator')
            })
        return customers

    def parse_suppliers(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract supplier information"""
        suppliers = []
        for supplier in root.findall('.//saft:Supplier', self.namespaces):
            suppliers.append({
                'supplier_id': self._get_text(supplier, 'saft:SupplierID'),
                'account_id': self._get_text(supplier, 'saft:AccountID'),
                'supplier_tax_id': self._get_text(supplier, 'saft:SupplierTaxID'),
                'company_name': self._get_text(supplier, 'saft:CompanyName'),
                'contact': self._get_text(supplier, 'saft:Contact'),
                'billing_address': self._parse_address(supplier.find('saft:BillingAddress', self.namespaces)),
                'ship_from_address': self._parse_address(supplier.find('saft:ShipFromAddress', self.namespaces)),
                'telephone': self._get_text(supplier, 'saft:Telephone'),
                'fax': self._get_text(supplier, 'saft:Fax'),
                'email': self._get_text(supplier, 'saft:Email'),
                'website': self._get_text(supplier, 'saft:Website'),
                'self_billing_indicator': self._get_text(supplier, 'saft:SelfBillingIndicator')
            })
        return suppliers

    def parse_products(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract product information"""
        products = []
        for product in root.findall('.//saft:Product', self.namespaces):
            products.append({
                'product_type': self._get_text(product, 'saft:ProductType'),
                'product_code': self._get_text(product, 'saft:ProductCode'),
                'product_group': self._get_text(product, 'saft:ProductGroup'),
                'product_description': self._get_text(product, 'saft:ProductDescription'),
                'product_number_code': self._get_text(product, 'saft:ProductNumberCode')
            })
        return products

    def parse_general_ledger_entries(self, root: ET.Element) -> Dict[str, Any]:
        """Extract general ledger entries and calculate totals"""
        gl_entries = root.find('.//saft:GeneralLedgerEntries', self.namespaces)
        if not gl_entries:
            return {}

        entries = []
        total_debit = Decimal('0')
        total_credit = Decimal('0')

        for journal in gl_entries.findall('saft:Journal', self.namespaces):
            journal_id = self._get_text(journal, 'saft:JournalID')
            description = self._get_text(journal, 'saft:Description')

            for transaction in journal.findall('saft:Transaction', self.namespaces):
                trans_id = self._get_text(transaction, 'saft:TransactionID')
                period = self._get_text(transaction, 'saft:Period')
                trans_date = self._get_text(transaction, 'saft:TransactionDate')
                source_id = self._get_text(transaction, 'saft:SourceID')
                description = self._get_text(transaction, 'saft:Description')
                doc_archival = self._get_text(transaction, 'saft:DocArchivalNumber')
                trans_type = self._get_text(transaction, 'saft:TransactionType')

                for line in transaction.findall('saft:Lines/saft:DebitLine', self.namespaces):
                    amount = Decimal(self._get_text(line, 'saft:DebitAmount') or '0')
                    total_debit += amount
                    entries.append({
                        'journal_id': journal_id,
                        'transaction_id': trans_id,
                        'period': period,
                        'transaction_date': trans_date,
                        'record_id': self._get_text(line, 'saft:RecordID'),
                        'account_id': self._get_text(line, 'saft:AccountID'),
                        'source_document_id': self._get_text(line, 'saft:SourceDocumentID'),
                        'description': self._get_text(line, 'saft:Description'),
                        'debit_amount': float(amount),
                        'credit_amount': 0.0
                    })

                for line in transaction.findall('saft:Lines/saft:CreditLine', self.namespaces):
                    amount = Decimal(self._get_text(line, 'saft:CreditAmount') or '0')
                    total_credit += amount
                    entries.append({
                        'journal_id': journal_id,
                        'transaction_id': trans_id,
                        'period': period,
                        'transaction_date': trans_date,
                        'record_id': self._get_text(line, 'saft:RecordID'),
                        'account_id': self._get_text(line, 'saft:AccountID'),
                        'source_document_id': self._get_text(line, 'saft:SourceDocumentID'),
                        'description': self._get_text(line, 'saft:Description'),
                        'debit_amount': 0.0,
                        'credit_amount': float(amount)
                    })

        return {
            'number_of_entries': self._get_text(gl_entries, 'saft:NumberOfEntries'),
            'total_debit': float(total_debit),
            'total_credit': float(total_credit),
            'entries': entries
        }

    def parse_source_documents(self, root: ET.Element) -> Dict[str, Any]:
        """Extract sales invoices and calculate revenue"""
        source_docs = root.find('.//saft:SourceDocuments', self.namespaces)
        if not source_docs:
            return {}

        sales_invoices = []
        total_net = Decimal('0')
        total_gross = Decimal('0')
        total_tax = Decimal('0')

        sales = source_docs.find('saft:SalesInvoices', self.namespaces)
        if sales:
            for invoice in sales.findall('saft:Invoice', self.namespaces):
                invoice_no = self._get_text(invoice, 'saft:InvoiceNo')
                invoice_status = self._get_text(invoice, 'saft:InvoiceStatus')
                invoice_date = self._get_text(invoice, 'saft:InvoiceDate')
                invoice_type = self._get_text(invoice, 'saft:InvoiceType')
                customer_id = self._get_text(invoice, 'saft:CustomerID')

                doc_totals = invoice.find('saft:DocumentTotals', self.namespaces)
                if doc_totals:
                    net_total = Decimal(self._get_text(doc_totals, 'saft:NetTotal') or '0')
                    gross_total = Decimal(self._get_text(doc_totals, 'saft:GrossTotal') or '0')
                    tax_payable = Decimal(self._get_text(doc_totals, 'saft:TaxPayable') or '0')

                    total_net += net_total
                    total_gross += gross_total
                    total_tax += tax_payable

                    sales_invoices.append({
                        'invoice_no': invoice_no,
                        'invoice_status': invoice_status,
                        'invoice_date': invoice_date,
                        'invoice_type': invoice_type,
                        'customer_id': customer_id,
                        'net_total': float(net_total),
                        'gross_total': float(gross_total),
                        'tax_payable': float(tax_payable)
                    })

        return {
            'number_of_sales_invoices': self._get_text(sales, 'saft:NumberOfEntries') if sales else '0',
            'total_net_sales': float(total_net),
            'total_gross_sales': float(total_gross),
            'total_tax_payable': float(total_tax),
            'sales_invoices': sales_invoices
        }

    def _parse_address(self, address: Optional[ET.Element]) -> Optional[Dict[str, str]]:
        """Parse address element"""
        if address is None:
            return None
        return {
            'address_detail': self._get_text(address, 'saft:AddressDetail'),
            'city': self._get_text(address, 'saft:City'),
            'postal_code': self._get_text(address, 'saft:PostalCode'),
            'region': self._get_text(address, 'saft:Region'),
            'country': self._get_text(address, 'saft:Country')
        }

    def _get_text(self, element: Optional[ET.Element], path: str) -> Optional[str]:
        """Safely extract text from XML element"""
        if element is None:
            return None
        child = element.find(path, self.namespaces)
        return child.text if child is not None else None

    def calculate_financial_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate key financial metrics from parsed data"""
        gl_entries = data.get('general_ledger_entries', {})
        source_docs = data.get('source_documents', {})

        # Revenue metrics
        total_revenue = source_docs.get('total_net_sales', 0)

        # Cost metrics (from GL entries - accounts starting with 6)
        total_costs = sum(
            entry['debit_amount']
            for entry in gl_entries.get('entries', [])
            if entry.get('account_id', '').startswith('6')
        )

        # Asset metrics (accounts starting with 2, 3, 4)
        total_assets = sum(
            entry['debit_amount'] - entry['credit_amount']
            for entry in gl_entries.get('entries', [])
            if any(entry.get('account_id', '').startswith(prefix) for prefix in ['2', '3', '4'])
        )

        # Calculate derived metrics
        gross_margin = total_revenue - total_costs if total_revenue else 0
        gross_margin_percentage = (gross_margin / total_revenue * 100) if total_revenue else 0

        return {
            'total_revenue': total_revenue,
            'total_costs': total_costs,
            'gross_margin': gross_margin,
            'gross_margin_percentage': gross_margin_percentage,
            'total_assets': total_assets,
            'number_of_customers': len(data.get('customers', [])),
            'number_of_suppliers': len(data.get('suppliers', [])),
            'number_of_products': len(data.get('products', [])),
            'number_of_invoices': source_docs.get('number_of_sales_invoices', 0)
        }

    def anonymize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize sensitive data for external processing"""
        anonymized = json.loads(json.dumps(data))  # Deep copy

        # Hash sensitive IDs
        if 'header' in anonymized:
            if 'tax_registration_number' in anonymized['header']:
                anonymized['header']['tax_registration_number'] = hashlib.sha256(
                    anonymized['header']['tax_registration_number'].encode()
                ).hexdigest()[:8]

        # Anonymize customer data
        for customer in anonymized.get('customers', []):
            if 'customer_tax_id' in customer:
                customer['customer_tax_id'] = hashlib.sha256(
                    customer['customer_tax_id'].encode()
                ).hexdigest()[:8]
            if 'email' in customer:
                customer['email'] = '***@***.com'

        # Anonymize supplier data
        for supplier in anonymized.get('suppliers', []):
            if 'supplier_tax_id' in supplier:
                supplier['supplier_tax_id'] = hashlib.sha256(
                    supplier['supplier_tax_id'].encode()
                ).hexdigest()[:8]
            if 'email' in supplier:
                supplier['email'] = '***@***.com'

        return anonymized

# MCP Server implementation
server = Server("saft-parser")
parser = SAFTParser()

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="parse_saft",
            description="Parse a SAF-T XML file and extract financial data",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the SAF-T XML file"
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Include detailed entries (default: false)",
                        "default": False
                    },
                    "anonymize": {
                        "type": "boolean",
                        "description": "Anonymize sensitive data (default: true)",
                        "default": True
                    }
                },
                "required": ["file_path"]
            }
        ),
        types.Tool(
            name="calculate_metrics",
            description="Calculate financial metrics from SAF-T data",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the SAF-T XML file"
                    }
                },
                "required": ["file_path"]
            }
        ),
        types.Tool(
            name="validate_saft",
            description="Validate SAF-T file structure and compliance",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the SAF-T XML file"
                    }
                },
                "required": ["file_path"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Execute tool calls"""

    if name == "parse_saft":
        file_path = Path(arguments["file_path"])
        include_details = arguments.get("include_details", False)
        anonymize = arguments.get("anonymize", True)

        if not file_path.exists():
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"File not found: {file_path}"})
            )]

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Parse all sections
            result = {
                "header": parser.parse_header(root),
                "customers": parser.parse_customers(root),
                "suppliers": parser.parse_suppliers(root),
                "products": parser.parse_products(root),
                "general_ledger_entries": parser.parse_general_ledger_entries(root),
                "source_documents": parser.parse_source_documents(root)
            }

            # Calculate financial metrics
            result["financial_metrics"] = parser.calculate_financial_metrics(result)

            # Remove detailed entries if not requested
            if not include_details:
                if "general_ledger_entries" in result:
                    result["general_ledger_entries"].pop("entries", None)
                if "source_documents" in result:
                    result["source_documents"].pop("sales_invoices", None)

            # Anonymize if requested
            if anonymize:
                result = parser.anonymize_sensitive_data(result)

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2, default=str)
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to parse SAF-T: {str(e)}"})
            )]

    elif name == "calculate_metrics":
        file_path = Path(arguments["file_path"])

        if not file_path.exists():
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"File not found: {file_path}"})
            )]

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Parse necessary sections for metrics
            data = {
                "general_ledger_entries": parser.parse_general_ledger_entries(root),
                "source_documents": parser.parse_source_documents(root),
                "customers": parser.parse_customers(root),
                "suppliers": parser.parse_suppliers(root),
                "products": parser.parse_products(root)
            }

            metrics = parser.calculate_financial_metrics(data)

            return [types.TextContent(
                type="text",
                text=json.dumps(metrics, indent=2)
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to calculate metrics: {str(e)}"})
            )]

    elif name == "validate_saft":
        file_path = Path(arguments["file_path"])

        if not file_path.exists():
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"File not found: {file_path}"})
            )]

        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Check for required elements
            required_elements = [
                ('.//saft:Header', 'Header section is missing'),
                ('.//saft:Header/saft:TaxRegistrationNumber', 'Tax Registration Number is missing'),
                ('.//saft:Header/saft:CompanyName', 'Company Name is missing'),
                ('.//saft:Header/saft:FiscalYear', 'Fiscal Year is missing'),
                ('.//saft:MasterFiles', 'MasterFiles section is missing')
            ]

            for xpath, error_msg in required_elements:
                if root.find(xpath, parser.namespaces) is None:
                    validation_results["valid"] = False
                    validation_results["errors"].append(error_msg)

            # Check for data consistency
            header = root.find('.//saft:Header', parser.namespaces)
            if header:
                start_date = parser._get_text(header, 'saft:StartDate')
                end_date = parser._get_text(header, 'saft:EndDate')

                if start_date and end_date:
                    start = datetime.fromisoformat(start_date)
                    end = datetime.fromisoformat(end_date)

                    if start >= end:
                        validation_results["errors"].append("Start date must be before end date")
                        validation_results["valid"] = False

            # Check general ledger balance
            gl_entries = parser.parse_general_ledger_entries(root)
            if gl_entries:
                total_debit = gl_entries.get('total_debit', 0)
                total_credit = gl_entries.get('total_credit', 0)

                if abs(total_debit - total_credit) > 0.01:
                    validation_results["warnings"].append(
                        f"General ledger is not balanced. Debit: {total_debit}, Credit: {total_credit}"
                    )

            return [types.TextContent(
                type="text",
                text=json.dumps(validation_results, indent=2)
            )]

        except ET.ParseError as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"XML parsing error: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps(validation_results, indent=2)
            )]
        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Validation error: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps(validation_results, indent=2)
            )]

    else:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())