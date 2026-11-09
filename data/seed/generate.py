"""Bulk synthetic agency: ~400 clients, ~900 policies, ~300 claims. Same output every run."""

from __future__ import annotations

import random
from datetime import date, timedelta

from faker import Faker

from data.docs import generate_pdfs

SEED = 4242
PRODUCTS = {"personal": ["HO-3", "Auto", "Umbrella"], "commercial": ["BOP", "GL", "Auto", "WC", "Umbrella"]}
CARRIERS = [("CAR-01", "Granite Mutual"), ("CAR-02", "Lakeshore Specialty"), ("CAR-03", "Summit P&C")]


def generate(n_clients: int = 400, as_of: date = date(2026, 11, 1)):
    rng, fake = random.Random(SEED), Faker()
    Faker.seed(SEED)
    clients, policies, claims = [], [], []
    for i in range(n_clients):
        kind = "commercial" if rng.random() < 0.35 else "personal"
        cid = f"C-{5000 + i}"
        name = fake.company() if kind == "commercial" else fake.name()
        clients.append((cid, name, kind))
        for j, product in enumerate(rng.sample(PRODUCTS[kind], k=rng.randint(1, 3))):
            pid = f"POL-{5000 + i}-{j}"
            eff = as_of - timedelta(days=rng.randint(0, 364))
            premium = round(rng.uniform(600, 4000) * (6 if kind == "commercial" else 1), 2)
            policies.append((pid, cid, kind, product, premium, eff, eff + timedelta(days=365),
                             rng.choice(CARRIERS)[0]))
            generate_pdfs.policy_pdf(client_id=cid, policy_id=pid, sections={
                "Policy Declarations": f"Client {cid} Policy {pid}\nEffective Date: {eff}\nPremium: ${premium:,.2f}",
                "Coverage Summary": f"This {kind} policy provides coverage for {product}.",}, ugly=rng.random() < 0.1)
            
            for k in range(rng.choices([0, 1, 2], weights=[75, 20, 5])[0]):
                claims.append((f"CLM-{pid}-{k}", pid, eff + timedelta(days=rng.randint(1, 300)),
                               round(rng.uniform(0, 40000), 2), rng.choice(["open", "closed"]),
                               fake.sentence(nb_words=6)))
    return clients, policies, claims