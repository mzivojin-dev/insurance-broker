"""Policy PDFs for the clients in `python -m data.seed --small`, the ones the eval cases cite.

Layout rules, so client_service.ingest.chunk_policy splits these at the right places:
- a heading is a line of letters only, no digits or punctuation ("Perils Insured Against")
- every body line has a digit or punctuation in it, so it never reads as a heading
"""

from pathlib import Path

from data.docs.generate_pdfs import policy_pdf

HO3 = {
    "Perils Insured Against": (
        "We insure against sudden and accidental direct physical loss to the dwelling,\n"
        "including water damage from a burst pipe, a frozen pipe, or an appliance that suddenly fails.\n"
        "Water that leaks slowly over weeks or months (seepage) is not covered."
    ),
    "Exclusions": (
        "We do not cover loss caused by flood, surface water, waves, or overflow of a body of water,\n"
        "whether driven by wind or not. Flood insurance is sold separately (e.g. through the NFIP).\n"
        "We do not cover earth movement, wear and tear, mold from long-term leaks, or pests."
    ),
    "Deductibles": (
        "All-peril deductible: $1,000 per occurrence.\n"
        "Wind and hail deductible: 2% of Coverage A."
    ),
    "Loss Settlement": (
        "Covered dwelling losses are paid at replacement cost, without deduction for depreciation,\n"
        "once repairs are complete. Personal property is paid at actual cash value."
    ),
}

POLICIES = [
    # (client_id, policy_id, file name, sections). The declarations carry the policy number,
    # which is how ingest ties a file to its policies row.
    ("C-1042", "POL-1042", "HO3-2026", {
        "Policy Declarations": (
            "Policy Number: POL-1042. Named Insured: Dana Whitfield.\n"
            "Form: HO-3 Special Form. Policy period: 2026-03-01 to 2027-03-01.\n"
            "Coverage A, Dwelling: $420,000. Coverage C, Personal Property: $210,000."
        ),
        **HO3,
    }),
    ("C-1042", "POL-1043", "AUTO-2026", {
        "Policy Declarations": (
            "Policy Number: POL-1043. Named Insured: Dana Whitfield.\n"
            "Personal Auto. Policy period: 2026-06-15 to 2026-12-15."
        ),
        "Liability Coverage": "Bodily injury: $100,000 per person / $300,000 per accident.",
        "Collision Coverage": "Collision deductible: $500. Comprehensive deductible: $250.",
    }),
    ("C-2001", "POL-2001", "HO3-2026", {
        "Policy Declarations": (
            "Policy Number: POL-2001. Named Insured: Marcus Lee.\n"
            "Form: HO-3 Special Form. Policy period: 2026-01-10 to 2027-01-10."
        ),
        **HO3,
    }),
    ("C-3001", "POL-3001", "BOP-2026", {
        "Policy Declarations": (
            "Policy Number: POL-3001. Named Insured: Rise & Shine Bakery LLC.\n"
            "Businessowners Policy (BOP). Policy period: 2026-01-01 to 2026-12-01."
        ),
        "Property Coverage": (
            "Building: $650,000. Business personal property: $180,000.\n"
            "Spoilage of refrigerated goods after a power outage: $15,000 sublimit."
        ),
        "Business Income": "Lost income after a covered loss is paid for up to 12 months.",
        "Additional Insured": (
            "Endorsement BP 04 02: the landlord, Elm Street Holdings, is an additional insured,\n"
            "but only for liability arising from the bakery's use of the leased premises."
        ),
    }),
    ("C-3002", "POL-3002", "GL-2026", {
        "Policy Declarations": (
            "Policy Number: POL-3002. Named Insured: Northside Plumbing Inc.\n"
            "Commercial General Liability (CGL). Policy period: 2025-11-20 to 2026-11-20."
        ),
        "Limits of Insurance": (
            "Each occurrence: $1,000,000. General aggregate: $2,000,000.\n"
            "Products-completed operations aggregate: $2,000,000."
        ),
        "Exclusions": (
            "Excludes pollution, professional services, and damage to your own work (CG 22 94)."
        ),
    }),
    ("C-3002", "POL-3003", "AUTO-2026", {
        "Policy Declarations": (
            "Policy Number: POL-3003. Named Insured: Northside Plumbing Inc.\n"
            "Business Auto, symbol 1 (any auto). Policy period: 2026-02-01 to 2027-02-01."
        ),
        "Liability Coverage": "Combined single limit: $1,000,000.",
    }),
]


def write_small_policies() -> list[Path]:
    return [policy_pdf(cid, pid, sections, filename=name) for cid, pid, name, sections in POLICIES]
