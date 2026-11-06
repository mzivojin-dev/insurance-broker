import json
from pathlib import Path

from faker import Faker
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

fake = Faker("en_CA")
env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")))

def money(low, high):
    return round(fake.random_int(low, high), 2)

def make_submission(i: int) -> dict:
    return {
        "submission_id": f"SUB-2026-{i:04d}",
        "named_insured": fake.company(),
        "dba": fake.company_suffix(),
        "fein": f"{fake.random_int(10, 99)}-{fake.random_int(1000000, 9999999)}",
        "effective_date": fake.date_between(start_date="+1d", end_date="+90d").isoformat(),
        "business_description": fake.catch_phrase(),
        "years_in_business": fake.random_int(1, 40),
        "locations": [{
            "location_id": "LOC-1",
            "address": fake.street_address(),
            "city": fake.city(),
            "province": "ON",
            "year_built": fake.random_int(1970, 2024),
            "construction": fake.random_element(["Masonry", "Frame", "Steel"]),
            "occupancy": "Warehouse / office",
            "building_tiv": money(250_000, 5_000_000),
            "contents_tiv": money(50_000, 1_000_000),
            "deductible": money(1_000, 25_000),
        }],
        "payroll": money(250_000, 4_000_000),
        "revenue": money(500_000, 12_000_000),
        "employees": fake.random_int(2, 250),
        "prior_carrier": fake.company(),
        "losses": [] if fake.boolean(chance_of_getting_true=30) else [{
            "policy_year": str(fake.random_int(2022, 2025)),
            "claim_date": fake.date_between(start_date="-3y", end_date="today").isoformat(),
            "claim_number": f"CLM-{fake.random_int(10000, 99999)}",
            "status": fake.random_element(["Closed", "Open"]),
            "paid": money(0, 150_000),
            "reserve": money(0, 75_000),
            "description": fake.sentence(nb_words=8),
        }],
    }

def render_pdf(submission: dict, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    template = env.get_template("commercial_application.html")
    html = template.render(**submission)
    pdf_path = out_dir / f"{submission['submission_id']}.pdf"
    with pdf_path.open("wb") as pdf_file:
        result = pisa.CreatePDF(html, dest=pdf_file)
    if result.err:
        raise RuntimeError(f"Failed to render PDF {pdf_path}: {result.err} error(s)")
    (out_dir / f"{submission['submission_id']}.json").write_text(
        json.dumps(submission, indent=2)
    )

for i in range(1, 101):
    render_pdf(make_submission(i), Path("data/docs/synthetic_submissions"))