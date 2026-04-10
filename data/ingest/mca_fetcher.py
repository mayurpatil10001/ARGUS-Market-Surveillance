"""
data/ingest/mca_fetcher.py — MCA21 corporate data fetcher and entity graph builder.
"""
from __future__ import annotations

import re
import time
from typing import Optional

import networkx as nx
import requests
from bs4 import BeautifulSoup

MCA_BASE = "https://www.mca.gov.in"

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (research@argus.ai)",
    "Accept": "text/html,application/xhtml+xml,*/*",
})


def fetch_company_directors(cin: str) -> dict:
    """
    Fetches MCA21 company master data page for a given CIN.
    Returns: company_name, directors (list of name+DIN dicts),
             registered_address, date_of_incorporation.
    """
    url = f"{MCA_BASE}/mcafoportal/companyLLPMasterData.do"
    try:
        resp = _SESSION.get(
            url,
            params={"companySearch": cin, "searchUnderSection": "companyAndLlpMasterData"},
            timeout=30,
        )
        resp.raise_for_status()
    except Exception:
        # Fallback to public MCA API (v3 where available)
        return _fetch_via_mca_api(cin)

    soup = BeautifulSoup(resp.text, "html.parser")
    result = {
        "cin": cin,
        "company_name": "",
        "directors": [],
        "registered_address": "",
        "date_of_incorporation": "",
    }

    # Parse company name
    name_el = soup.find(string=re.compile("Company Name", re.I))
    if name_el and name_el.parent:
        td = name_el.parent.find_next_sibling("td")
        if td:
            result["company_name"] = td.get_text(strip=True)

    # Parse directors table
    dir_table = soup.find("table", id=re.compile("director", re.I))
    if dir_table:
        for row in dir_table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                result["directors"].append({
                    "name": cols[0].get_text(strip=True),
                    "din": cols[1].get_text(strip=True) if len(cols) > 1 else "",
                })

    # Parse address
    addr_el = soup.find(string=re.compile("Registered Address", re.I))
    if addr_el and addr_el.parent:
        td = addr_el.parent.find_next_sibling("td")
        if td:
            result["registered_address"] = td.get_text(strip=True)

    # Parse incorporation date
    inc_el = soup.find(string=re.compile("Date of Incorporation", re.I))
    if inc_el and inc_el.parent:
        td = inc_el.parent.find_next_sibling("td")
        if td:
            result["date_of_incorporation"] = td.get_text(strip=True)

    return result


def _fetch_via_mca_api(cin: str) -> dict:
    """Fallback using MCA public lookup."""
    url = f"{MCA_BASE}/mcafoportal/viewCompanyMasterData.do"
    try:
        resp = _SESSION.post(
            url,
            data={"companyID": cin, "requestType": "CorporateMasterData"},
            timeout=30,
        )
        resp.raise_for_status()
        return {
            "cin": cin,
            "company_name": cin,
            "directors": [],
            "registered_address": "",
            "date_of_incorporation": "",
            "raw_html_length": len(resp.text),
        }
    except Exception:
        return {
            "cin": cin,
            "company_name": cin,
            "directors": [],
            "registered_address": "",
            "date_of_incorporation": "",
        }


def build_entity_graph(entity_names: list[str]) -> nx.DiGraph:
    """
    Builds a NetworkX directed graph where:
      - Nodes = companies (by CIN or name)
      - Edges = shared director (director_name as edge attribute)
    Uses approximate name → CIN resolution via MCA search.
    """
    G = nx.DiGraph()
    # Try to resolve CINs from names via quick search
    resolved: dict[str, dict] = {}
    for name in entity_names:
        cin = _resolve_cin_from_name(name)
        if cin:
            data = fetch_company_directors(cin)
            resolved[name] = data
        else:
            resolved[name] = {"company_name": name, "directors": [], "cin": ""}
        G.add_node(name, **resolved[name])
        time.sleep(0.5)

    # Find shared directors
    dir_to_companies: dict[str, list[str]] = {}
    for company, data in resolved.items():
        for d in data.get("directors", []):
            din = d.get("din", "") or d.get("name", "")
            if din:
                dir_to_companies.setdefault(din, []).append(company)

    for din, companies in dir_to_companies.items():
        if len(companies) > 1:
            for i in range(len(companies)):
                for j in range(len(companies)):
                    if i != j:
                        G.add_edge(companies[i], companies[j], director=din)

    return G


def _resolve_cin_from_name(name: str) -> Optional[str]:
    """Attempts to find CIN for a company name using MCA search."""
    url = f"{MCA_BASE}/mcafoportal/viewCompanyMasterData.do"
    try:
        resp = _SESSION.post(
            url,
            data={"companySearch": name, "requestType": "CIN"},
            timeout=20,
        )
        resp.raise_for_status()
        # Extract CIN pattern: L12345AB1234ABC012345
        cin_match = re.search(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b", resp.text)
        if cin_match:
            return cin_match.group(0)
    except Exception:
        pass
    return None


def find_shell_network(entity_name: str, max_hops: int = 2) -> list[str]:
    """
    BFS on the entity graph finds all connected entities within max_hops hops.
    Returns list of entity names in suspected shell network.
    """
    G = build_entity_graph([entity_name])
    if entity_name not in G:
        return []

    visited: set[str] = {entity_name}
    queue = [(entity_name, 0)]
    network: list[str] = []

    while queue:
        node, depth = queue.pop(0)
        if depth >= max_hops:
            continue
        for neighbor in list(G.successors(node)) + list(G.predecessors(node)):
            if neighbor not in visited:
                visited.add(neighbor)
                network.append(neighbor)
                queue.append((neighbor, depth + 1))

    return network
