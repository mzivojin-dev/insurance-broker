"""Chunking and policy mapping for client_service.ingest. No Voyage key or database needed."""

from client_service.ingest import Chunk, chunk_policy, policy_id_for
from data.docs.generate_pdfs import policy_pdf
from data.docs.small_policies import POLICIES


def _ho3(tmp_path, monkeypatch):
    monkeypatch.setattr("data.docs.generate_pdfs.OUT", tmp_path)
    cid, pid, name, sections = POLICIES[0]          # C-1042, POL-1042, HO3-2026
    return policy_pdf(cid, pid, sections, filename=name), sections


def test_one_chunk_per_section_with_citable_source(tmp_path, monkeypatch):
    path, sections = _ho3(tmp_path, monkeypatch)
    chunks = chunk_policy(str(path), "policies/C-1042/HO3-2026.pdf")
    assert [c.heading for c in chunks] == list(sections)
    burst = next(c for c in chunks if c.heading == "Perils Insured Against")
    assert burst.source_doc == "policies/C-1042/HO3-2026.pdf#Perils Insured Against"
    assert "burst pipe" in burst.content


def test_long_sections_are_split(tmp_path, monkeypatch):
    path, _ = _ho3(tmp_path, monkeypatch)
    chunks = chunk_policy(str(path), "x.pdf", max_chars=80)
    assert len([c for c in chunks if c.heading == "Exclusions"]) > 1


def test_policy_number_must_belong_to_the_folder_client():
    chunks = [Chunk("x#Policy Declarations", "Policy Declarations", "Policy Number: POL-1042.")]
    owned = {"POL-1042": "C-1042"}
    assert policy_id_for(chunks, "C-1042", owned) == "POL-1042"
    assert policy_id_for(chunks, "C-2001", owned) is None      # filed under the wrong client
    assert policy_id_for(chunks, "C-1042", {}) is None         # policy not in the database
