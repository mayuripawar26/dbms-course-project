"""
data/synthetic/generate_synthetic_data.py

Phase 7 Synthetic Banking Dataset Generator
Generates strictly fictional customer profiles, accounts, and transactions for testing:
1. Potential Money-Mule Activity (Rapid Inflow Fan-In -> Fast Pass-Through Drain)
2. Reported Unauthorized UPI Transactions (Velocity Burst / Fraud Alert)
3. Expired KYC and Subsequent Account Activity (Regulatory Non-Compliance)
4. Cross-Border Transaction Risk & Disproportionate Volume (Apex Global Consultancy)
5. Circular Fund Transfers (Round-Tripping / Layering Cycle: A -> B -> C -> A)
6. Loan-Document Inconsistencies & Rapid Fund Diversion

All records are explicitly synthetic and fictional. No real customer or transaction data is used.
"""

import json
from pathlib import Path
from datetime import datetime


def generate_synthetic_dataset() -> dict:
    customers = [
        # Preserved Scenario 1: Money Mule
        {
            "customer_id": "CUST_SYNTH_101",
            "full_name": "Arjun Sharma (Fictional)",
            "customer_type": "INDIVIDUAL",
            "occupation": "Student / Freelancer",
            "declared_annual_income_inr": 250000,
            "kyc_status": "VERIFIED_SIMPLIFIED",
            "cdd_tier": "SIMPLIFIED_DUE_DILIGENCE",
            "risk_rating": "HIGH",
            "pep_status": False,
            "onboarding_date": "2025-01-15",
            "flagged_scenario": "SCENARIO_1_RAPID_DISPERSAL_MULE"
        },
        # Preserved Scenario 2: Unauthorized UPI Fraud / Velocity Anomaly
        {
            "customer_id": "CUST_SYNTH_102",
            "full_name": "Priya Verma (Fictional)",
            "customer_type": "INDIVIDUAL",
            "occupation": "Retail Executive",
            "declared_annual_income_inr": 720000,
            "kyc_status": "VERIFIED_STANDARD",
            "cdd_tier": "STANDARD_DUE_DILIGENCE",
            "risk_rating": "MEDIUM",
            "pep_status": False,
            "onboarding_date": "2023-04-10",
            "flagged_scenario": "SCENARIO_2_UNAUTHORIZED_UPI_BURST"
        },
        # Preserved Scenario 3: Dormant Account Takeover
        {
            "customer_id": "CUST_SYNTH_103",
            "full_name": "Ramesh Chandra (Fictional)",
            "customer_type": "INDIVIDUAL_SENIOR",
            "occupation": "Retired Government Officer",
            "declared_annual_income_inr": 480000,
            "kyc_status": "VERIFIED_STANDARD",
            "cdd_tier": "STANDARD_DUE_DILIGENCE",
            "risk_rating": "LOW",
            "pep_status": False,
            "onboarding_date": "2018-09-20",
            "flagged_scenario": "SCENARIO_3_POTENTIAL_ACCOUNT_TAKEOVER"
        },
        # Preserved Scenario 4: Apex Global Consultancy (Cross-Border / Shell / Disproportionate Volume)
        {
            "customer_id": "CUST_SYNTH_104",
            "full_name": "Apex Global Consultancy (Fictional Entity)",
            "customer_type": "CORPORATE_SHELL_SUSPECT",
            "occupation": "Consulting Services",
            "declared_annual_income_inr": 1200000,
            "kyc_status": "EXPIRED_NON_COMPLIANT",
            "cdd_tier": "ENHANCED_DUE_DILIGENCE_REQUIRED",
            "risk_rating": "CRITICAL",
            "pep_status": True,
            "onboarding_date": "2022-11-05",
            "flagged_scenario": "SCENARIO_4_CDD_KYC_GAP_DISPROPORTIONATE_TURNOVER"
        },
        # New Scenario 5: Expired KYC with Ongoing Active High-Value Transactions
        {
            "customer_id": "CUST_SYNTH_105",
            "full_name": "Rajesh Gupta (Fictional)",
            "customer_type": "INDIVIDUAL_BUSINESS",
            "occupation": "Wholesale Trader",
            "declared_annual_income_inr": 1500000,
            "kyc_status": "EXPIRED_NON_COMPLIANT",
            "cdd_tier": "STANDARD_DUE_DILIGENCE",
            "risk_rating": "HIGH",
            "pep_status": False,
            "onboarding_date": "2020-03-12",
            "flagged_scenario": "SCENARIO_5_EXPIRED_KYC_ACTIVE_TRADING"
        },
        # New Scenario 6: Circular Fund Transfers (Layering / Round-Tripping)
        {
            "customer_id": "CUST_SYNTH_106",
            "full_name": "Vikas Trading Syndicate (Fictional Entity)",
            "customer_type": "CORPORATE_ENTREPRENEURIAL",
            "occupation": "Commodities Intermediary",
            "declared_annual_income_inr": 5000000,
            "kyc_status": "VERIFIED_STANDARD",
            "cdd_tier": "STANDARD_DUE_DILIGENCE",
            "risk_rating": "CRITICAL",
            "pep_status": False,
            "onboarding_date": "2024-02-18",
            "flagged_scenario": "SCENARIO_6_CIRCULAR_ROUTING"
        },
        # New Scenario 7: Loan-Document Inconsistencies & Rapid Fund Diversion
        {
            "customer_id": "CUST_SYNTH_107",
            "full_name": "Sunita Enterprises (Fictional Entity)",
            "customer_type": "MSME_BORROWER",
            "occupation": "Textile Manufacturing",
            "declared_annual_income_inr": 3600000,
            "kyc_status": "VERIFIED_STANDARD",
            "cdd_tier": "STANDARD_DUE_DILIGENCE",
            "risk_rating": "HIGH",
            "pep_status": False,
            "onboarding_date": "2023-08-22",
            "flagged_scenario": "SCENARIO_7_LOAN_DOCUMENT_INCONSISTENCY"
        }
    ]

    accounts = [
        # Preserved Accounts
        {
            "account_number": "ACC_SYNTH_300101",
            "customer_id": "CUST_SYNTH_101",
            "account_type": "SAVINGS",
            "status": "ACTIVE",
            "currency": "INR",
            "opened_on": "2025-01-15",
            "branch": "Bengaluru Central (Fictional)",
            "current_balance_inr": 1250.00
        },
        {
            "account_number": "ACC_SYNTH_300201",
            "customer_id": "CUST_SYNTH_102",
            "account_type": "SAVINGS",
            "status": "ACTIVE",
            "currency": "INR",
            "opened_on": "2023-04-10",
            "branch": "Mumbai Nariman Point (Fictional)",
            "current_balance_inr": 34800.00
        },
        {
            "account_number": "ACC_SYNTH_300301",
            "customer_id": "CUST_SYNTH_103",
            "account_type": "SAVINGS_PENSION",
            "status": "DORMANT_REACTIVATED",
            "currency": "INR",
            "opened_on": "2018-09-20",
            "branch": "New Delhi Connaught Place (Fictional)",
            "current_balance_inr": 15200.00
        },
        {
            "account_number": "ACC_SYNTH_300401",
            "customer_id": "CUST_SYNTH_104",
            "account_type": "CURRENT_BUSINESS",
            "status": "RESTRICTED_KYC_DUE",
            "currency": "INR",
            "opened_on": "2022-11-05",
            "branch": "Chennai Anna Salai (Fictional)",
            "current_balance_inr": 7820000.00
        },
        # New Account for CUST_SYNTH_105 (Expired KYC)
        {
            "account_number": "ACC_SYNTH_300501",
            "customer_id": "CUST_SYNTH_105",
            "account_type": "CURRENT_COMMERCIAL",
            "status": "ACTIVE_KYC_OVERDUE",
            "currency": "INR",
            "opened_on": "2020-03-12",
            "branch": "Kolkata BBD Bagh (Fictional)",
            "current_balance_inr": 1850000.00
        },
        # New Accounts for CUST_SYNTH_106 (Circular Routing Cycle)
        {
            "account_number": "ACC_SYNTH_300601",
            "customer_id": "CUST_SYNTH_106",
            "account_type": "CURRENT_BUSINESS",
            "status": "ACTIVE",
            "currency": "INR",
            "opened_on": "2024-02-18",
            "branch": "Ahmedabad Ashram Road (Fictional)",
            "current_balance_inr": 490000.00
        },
        {
            "account_number": "ACC_SYNTH_300602",
            "customer_id": "CUST_SYNTH_106",
            "account_type": "CURRENT_SETTLEMENT",
            "status": "ACTIVE",
            "currency": "INR",
            "opened_on": "2024-02-19",
            "branch": "Surat Ring Road (Fictional)",
            "current_balance_inr": 5000.00
        },
        {
            "account_number": "ACC_SYNTH_300603",
            "customer_id": "CUST_SYNTH_106",
            "account_type": "CURRENT_HOLDING",
            "status": "ACTIVE",
            "currency": "INR",
            "opened_on": "2024-02-20",
            "branch": "Vadodara Alkapuri (Fictional)",
            "current_balance_inr": 5000.00
        },
        # New Account for CUST_SYNTH_107 (Loan Divergence)
        {
            "account_number": "ACC_SYNTH_300701",
            "customer_id": "CUST_SYNTH_107",
            "account_type": "LOAN_CURRENT_CC",
            "status": "ACTIVE",
            "currency": "INR",
            "opened_on": "2023-08-22",
            "branch": "Pune Shivaji Nagar (Fictional)",
            "current_balance_inr": 200000.00
        }
    ]

    transactions = [
        # SCENARIO 1: Rapid Inflow -> Fast Outflow (Layering / Mule signal)
        {
            "tx_id": "TX_SYNTH_1001",
            "sender_account": "ACC_EXTERNAL_PARTY_A",
            "receiver_account": "ACC_SYNTH_300101",
            "amount_inr": 49500.00,
            "currency": "INR",
            "timestamp": "2026-09-10T10:15:00Z",
            "channel": "IMPS",
            "type": "INFLOW_TRANSFER",
            "risk_indicator": "IND_STRUCTURING_SUB_THRESHOLD",
            "scenario": "SCENARIO_1_RAPID_DISPERSAL_MULE"
        },
        {
            "tx_id": "TX_SYNTH_1002",
            "sender_account": "ACC_EXTERNAL_PARTY_B",
            "receiver_account": "ACC_SYNTH_300101",
            "amount_inr": 48900.00,
            "currency": "INR",
            "timestamp": "2026-09-10T10:25:00Z",
            "channel": "UPI",
            "type": "INFLOW_TRANSFER",
            "risk_indicator": "IND_STRUCTURING_SUB_THRESHOLD",
            "scenario": "SCENARIO_1_RAPID_DISPERSAL_MULE"
        },
        {
            "tx_id": "TX_SYNTH_1003",
            "sender_account": "ACC_EXTERNAL_PARTY_C",
            "receiver_account": "ACC_SYNTH_300101",
            "amount_inr": 49200.00,
            "currency": "INR",
            "timestamp": "2026-09-10T10:40:00Z",
            "channel": "IMPS",
            "type": "INFLOW_TRANSFER",
            "risk_indicator": "IND_STRUCTURING_SUB_THRESHOLD",
            "scenario": "SCENARIO_1_RAPID_DISPERSAL_MULE"
        },
        {
            "tx_id": "TX_SYNTH_1004",
            "sender_account": "ACC_EXTERNAL_PARTY_D",
            "receiver_account": "ACC_SYNTH_300101",
            "amount_inr": 49000.00,
            "currency": "INR",
            "timestamp": "2026-09-10T11:00:00Z",
            "channel": "IMPS",
            "type": "INFLOW_TRANSFER",
            "risk_indicator": "IND_STRUCTURING_SUB_THRESHOLD",
            "scenario": "SCENARIO_1_RAPID_DISPERSAL_MULE"
        },
        {
            "tx_id": "TX_SYNTH_1005",
            "sender_account": "ACC_SYNTH_300101",
            "receiver_account": "ACC_EXTERNAL_OFFSHORE_MULE_EXIT",
            "amount_inr": 195000.00,
            "currency": "INR",
            "timestamp": "2026-09-10T11:20:00Z",
            "channel": "NEFT",
            "type": "RAPID_OUTFLOW_DRAIN",
            "risk_indicator": "IND_PASS_THROUGH_RAPID_DRAIN",
            "scenario": "SCENARIO_1_RAPID_DISPERSAL_MULE"
        },

        # SCENARIO 2: Reported Unauthorized UPI Transactions
        {
            "tx_id": "TX_SYNTH_2001",
            "sender_account": "ACC_SYNTH_300201",
            "receiver_account": "ACC_GAMING_MERCHANT_VIRTUAL",
            "amount_inr": 2000.00,
            "currency": "INR",
            "timestamp": "2026-09-12T02:05:10Z",
            "channel": "UPI",
            "type": "HIGH_FREQUENCY_BURST",
            "risk_indicator": "IND_OFF_HOURS_BURST",
            "scenario": "SCENARIO_2_UNAUTHORIZED_UPI_BURST"
        },
        {
            "tx_id": "TX_SYNTH_2002",
            "sender_account": "ACC_SYNTH_300201",
            "receiver_account": "ACC_GAMING_MERCHANT_VIRTUAL",
            "amount_inr": 2000.00,
            "currency": "INR",
            "timestamp": "2026-09-12T02:07:30Z",
            "channel": "UPI",
            "type": "HIGH_FREQUENCY_BURST",
            "risk_indicator": "IND_VELOCITY_FREQUENCY_SPIKE",
            "scenario": "SCENARIO_2_UNAUTHORIZED_UPI_BURST"
        },
        {
            "tx_id": "TX_SYNTH_2003",
            "sender_account": "ACC_SYNTH_300201",
            "receiver_account": "ACC_GAMING_MERCHANT_VIRTUAL",
            "amount_inr": 2000.00,
            "currency": "INR",
            "timestamp": "2026-09-12T02:09:45Z",
            "channel": "UPI",
            "type": "HIGH_FREQUENCY_BURST",
            "risk_indicator": "IND_VELOCITY_FREQUENCY_SPIKE",
            "scenario": "SCENARIO_2_UNAUTHORIZED_UPI_BURST"
        },

        # SCENARIO 3: Potential Account Takeover (Dormant account sudden RTGS drain)
        {
            "tx_id": "TX_SYNTH_3001",
            "sender_account": "ACC_SYNTH_300301",
            "receiver_account": "ACC_UNKNOWN_BENEFICIARY_X",
            "amount_inr": 985000.00,
            "currency": "INR",
            "timestamp": "2026-09-14T14:32:00Z",
            "channel": "RTGS",
            "type": "UNCHARACTERISTIC_HIGH_VALUE_DRAIN",
            "risk_indicator": "IND_DORMANT_SUDDEN_HIGH_VALUE_DRAIN",
            "scenario": "SCENARIO_3_POTENTIAL_ACCOUNT_TAKEOVER"
        },

        # SCENARIO 4: CDD / KYC Gaps & Cross-Border Shell Transfer (Preserved Apex Scenario)
        {
            "tx_id": "TX_SYNTH_4001",
            "sender_account": "ACC_OVERSEAS_SHELL_JURISDICTION",
            "receiver_account": "ACC_SYNTH_300401",
            "amount_inr": 8500000.00,
            "currency": "INR",
            "timestamp": "2026-09-15T16:00:00Z",
            "channel": "SWIFT_CROSS_BORDER",
            "type": "CROSS_BORDER_INFLOW",
            "risk_indicator": "IND_CDD_INCOME_DISPROPORTIONATE",
            "scenario": "SCENARIO_4_CDD_KYC_GAP_DISPROPORTIONATE_TURNOVER"
        },

        # SCENARIO 5: Expired KYC with Ongoing Active High-Value Transactions
        {
            "tx_id": "TX_SYNTH_5001",
            "sender_account": "ACC_COMMERCIAL_CLIENT_X",
            "receiver_account": "ACC_SYNTH_300501",
            "amount_inr": 950000.00,
            "currency": "INR",
            "timestamp": "2026-09-16T11:10:00Z",
            "channel": "RTGS",
            "type": "COMMERCIAL_INFLOW",
            "risk_indicator": "IND_KYC_EXPIRED_ACTIVE_TRANSACTIONS",
            "scenario": "SCENARIO_5_EXPIRED_KYC_ACTIVE_TRADING"
        },
        {
            "tx_id": "TX_SYNTH_5002",
            "sender_account": "ACC_COMMERCIAL_CLIENT_Y",
            "receiver_account": "ACC_SYNTH_300501",
            "amount_inr": 900000.00,
            "currency": "INR",
            "timestamp": "2026-09-16T14:45:00Z",
            "channel": "NEFT",
            "type": "COMMERCIAL_INFLOW",
            "risk_indicator": "IND_KYC_EXPIRED_ACTIVE_TRANSACTIONS",
            "scenario": "SCENARIO_5_EXPIRED_KYC_ACTIVE_TRADING"
        },

        # SCENARIO 6: Circular Fund Transfers (A -> B -> C -> A)
        {
            "tx_id": "TX_SYNTH_6001",
            "sender_account": "ACC_SYNTH_300601",
            "receiver_account": "ACC_SYNTH_300602",
            "amount_inr": 500000.00,
            "currency": "INR",
            "timestamp": "2026-09-17T09:30:00Z",
            "channel": "RTGS",
            "type": "CIRCULAR_HOP_1",
            "risk_indicator": "IND_CIRCULAR_ROUTING_DETECTED",
            "scenario": "SCENARIO_6_CIRCULAR_ROUTING"
        },
        {
            "tx_id": "TX_SYNTH_6002",
            "sender_account": "ACC_SYNTH_300602",
            "receiver_account": "ACC_SYNTH_300603",
            "amount_inr": 495000.00,
            "currency": "INR",
            "timestamp": "2026-09-17T10:15:00Z",
            "channel": "RTGS",
            "type": "CIRCULAR_HOP_2",
            "risk_indicator": "IND_CIRCULAR_ROUTING_DETECTED",
            "scenario": "SCENARIO_6_CIRCULAR_ROUTING"
        },
        {
            "tx_id": "TX_SYNTH_6003",
            "sender_account": "ACC_SYNTH_300603",
            "receiver_account": "ACC_SYNTH_300601",
            "amount_inr": 490000.00,
            "currency": "INR",
            "timestamp": "2026-09-17T11:00:00Z",
            "channel": "RTGS",
            "type": "CIRCULAR_HOP_3_RETURN",
            "risk_indicator": "IND_CIRCULAR_ROUTING_DETECTED",
            "scenario": "SCENARIO_6_CIRCULAR_ROUTING"
        },

        # SCENARIO 7: Loan-Document Inconsistencies & Rapid Fund Diversion
        {
            "tx_id": "TX_SYNTH_7001",
            "sender_account": "ACC_BANK_LOAN_DISBURSEMENT",
            "receiver_account": "ACC_SYNTH_300701",
            "amount_inr": 2500000.00,
            "currency": "INR",
            "timestamp": "2026-09-18T10:00:00Z",
            "channel": "INTERNAL_TRANSFER",
            "type": "LOAN_DISBURSEMENT_CREDIT",
            "risk_indicator": "IND_LOAN_INCONSISTENCY_CHECK",
            "scenario": "SCENARIO_7_LOAN_DOCUMENT_INCONSISTENCY"
        },
        {
            "tx_id": "TX_SYNTH_7002",
            "sender_account": "ACC_SYNTH_300701",
            "receiver_account": "ACC_PROMOTER_PERSONAL_SAVINGS",
            "amount_inr": 2300000.00,
            "currency": "INR",
            "timestamp": "2026-09-18T15:30:00Z",
            "channel": "RTGS",
            "type": "UNAUTHORIZED_LOAN_PROCEEDS_DIVERSION",
            "risk_indicator": "IND_LOAN_PROCEEDS_RAPID_DIVERSION",
            "scenario": "SCENARIO_7_LOAN_DOCUMENT_INCONSISTENCY"
        }
    ]

    scenarios = [
        {
            "scenario_id": "SCENARIO_1_RAPID_DISPERSAL_MULE",
            "name": "Pass-Through / Rapid Dispersal Pattern (Money Mule)",
            "typology": "Mule Account / Layering",
            "description": "Multiple incoming sub-threshold transactions rapidly followed by a near-total outflow drain to an external party.",
            "regulatory_hooks": [
                "FATF Recommendation 10 & 20 (Customer Due Diligence & Suspicious Transaction Reporting)",
                "RBI KYC Master Direction, Chapter VI (Monitoring of Transactions)"
            ],
            "severity": "HIGH",
            "status": "INVESTIGATION_SIGNAL"
        },
        {
            "scenario_id": "SCENARIO_2_UNAUTHORIZED_UPI_BURST",
            "name": "Reported Unauthorized UPI Transactions",
            "typology": "Automated Micro-Dispersal / Carding / Scripted Velocity",
            "description": "Rapid succession of micro-transfers during non-business hours deviating from historical retail behavior.",
            "regulatory_hooks": [
                "RBI Cyber Security Framework (Real-time Fraud Monitoring)",
                "RBI Master Direction - Digital Payment Security Controls"
            ],
            "severity": "HIGH",
            "status": "INVESTIGATION_SIGNAL"
        },
        {
            "scenario_id": "SCENARIO_3_POTENTIAL_ACCOUNT_TAKEOVER",
            "name": "Dormant Account High-Value Drain",
            "typology": "Account Takeover (ATO) / Credential Compromise",
            "description": "Sudden reactivation of a long-dormant senior retail account with immediate maximum limit transfer to newly added beneficiary.",
            "regulatory_hooks": [
                "RBI Operational Guidelines (Dormant Accounts Operations)",
                "RBI Cyber Security Framework (Two-Factor Authentication & Velocity Throttling)"
            ],
            "severity": "CRITICAL",
            "status": "INVESTIGATION_SIGNAL"
        },
        {
            "scenario_id": "SCENARIO_4_CDD_KYC_GAP_DISPROPORTIONATE_TURNOVER",
            "name": "Customer Due Diligence Gaps & Excessive Turnover (Apex Scenario)",
            "typology": "PEP Non-Compliance / Shell Company Cross-Border Transfer",
            "description": "Expired KYC status customer transacting 7x declared annual turnover via high-risk overseas channel.",
            "regulatory_hooks": [
                "RBI KYC Master Direction Section 35 & 38 (Enhanced Due Diligence & Politically Exposed Persons)",
                "FATF Recommendation 12 (PEPs) & 19 (Higher-risk countries)"
            ],
            "severity": "CRITICAL",
            "status": "INVESTIGATION_SIGNAL"
        },
        {
            "scenario_id": "SCENARIO_5_EXPIRED_KYC_ACTIVE_TRADING",
            "name": "Expired KYC with Ongoing Active Commercial Transfers",
            "typology": "Regulatory Non-Compliance / Dormancy Failure",
            "description": "Customer operating active high-value commercial credits without periodic KYC update or enhanced due diligence.",
            "regulatory_hooks": [
                "RBI KYC Master Direction Section 38 (Periodic Updation of KYC)",
                "PML (Maintenance of Records) Rules, 2005"
            ],
            "severity": "HIGH",
            "status": "INVESTIGATION_SIGNAL"
        },
        {
            "scenario_id": "SCENARIO_6_CIRCULAR_ROUTING",
            "name": "Circular Fund Transfers (Layering & Round-Tripping)",
            "typology": "Circular Transactions / Artificial Turnover Inflation",
            "description": "Funds transferred across multiple accounts (A -> B -> C -> A) within hours returning to the originating account minus transaction fees.",
            "regulatory_hooks": [
                "FATF Recommendation 20 (Suspicious Transaction Reporting)",
                "RBI Master Direction on Monitoring of Accounts"
            ],
            "severity": "CRITICAL",
            "status": "INVESTIGATION_SIGNAL"
        },
        {
            "scenario_id": "SCENARIO_7_LOAN_DOCUMENT_INCONSISTENCY",
            "name": "Loan-Document Inconsistencies & Fund Diversion",
            "typology": "Credit Facility Misuse / Diversion of Working Capital",
            "description": "Disbursed business loan funds diverted immediately to personal accounts of promoters, conflicting with stated business utilization and credit reporting.",
            "regulatory_hooks": [
                "RBI Master Direction on Credit Information Companies (CICs)",
                "RBI Supervisory Guidelines on Large Credit and Diversion of Funds"
            ],
            "severity": "HIGH",
            "status": "INVESTIGATION_SIGNAL"
        }
    ]

    return {
        "customers": customers,
        "accounts": accounts,
        "transactions": transactions,
        "scenarios": scenarios
    }


def save_synthetic_data(project_root: Path):
    synth_dir = project_root / "data" / "synthetic"
    synth_dir.mkdir(parents=True, exist_ok=True)

    data = generate_synthetic_dataset()

    for key in ["customers", "accounts", "transactions", "scenarios"]:
        file_path = synth_dir / f"{key}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data[key], f, indent=2, ensure_ascii=False)
        print(f"[+] Saved synthetic {key}: {file_path} ({len(data[key])} records)")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    save_synthetic_data(root)
