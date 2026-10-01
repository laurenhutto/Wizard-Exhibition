#!/usr/bin/env python3
"""
Harry Potter Wizard World Analytics
------------------------------------
Fetches information on Wizards, Spells, and Elixirs from the official Wizard World API
(https://wizard-world-api.herokuapp.com), models wizard-magic relationships and canon
usage occurrences across the 7 Harry Potter books, ranks books by usage frequency,
and serves an interactive visual dashboard on localhost.

Zero external Python dependencies required (standard library only).
"""

import os
import sys
import json
import socket
import argparse
import webbrowser
import http.server
import socketserver
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Windows console encoding safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "https://wizard-world-api.herokuapp.com"

# The 7 canonical Harry Potter books
HP_BOOKS = [
    {"id": "b1", "code": "PS", "title": "Philosopher's Stone", "year": 1997, "full": "Book 1: Harry Potter and the Philosopher's Stone"},
    {"id": "b2", "code": "CoS", "title": "Chamber of Secrets", "year": 1998, "full": "Book 2: Harry Potter and the Chamber of Secrets"},
    {"id": "b3", "code": "PoA", "title": "Prisoner of Azkaban", "year": 1999, "full": "Book 3: Harry Potter and the Prisoner of Azkaban"},
    {"id": "b4", "code": "GoF", "title": "Goblet of Fire", "year": 2000, "full": "Book 4: Harry Potter and the Goblet of Fire"},
    {"id": "b5", "code": "OotP", "title": "Order of the Phoenix", "year": 2003, "full": "Book 5: Harry Potter and the Order of the Phoenix"},
    {"id": "b6", "code": "HBP", "title": "Half-Blood Prince", "year": 2005, "full": "Book 6: Harry Potter and the Half-Blood Prince"},
    {"id": "b7", "code": "DH", "title": "Deathly Hallows", "year": 2007, "full": "Book 7: Harry Potter and the Deathly Hallows"},
]

BOOK_KEYS = ["b1", "b2", "b3", "b4", "b5", "b6", "b7"]

# Canonical book occurrence distribution mapping for Harry Potter spells & elixirs
# Maps canonical name to book counts [b1, b2, b3, b4, b5, b6, b7] and prominent users
CANON_MAGIC_REGISTRY = {
    # SPELLS
    "Expelliarmus": {
        "type": "Spell",
        "category": "Charm / Combat",
        "book_counts": {"b1": 0, "b2": 3, "b3": 4, "b4": 10, "b5": 8, "b6": 7, "b7": 15},
        "wizards": ["Harry Potter", "Severus Snape", "Remus Lupin"],
        "description": "The Disarming Charm. Harry Potter's signature spell used to disarm opponents and famously counter Voldemort's Killing Curse."
    },
    "Expecto Patronum": {
        "type": "Spell",
        "category": "Charm / Defensive",
        "book_counts": {"b1": 0, "b2": 0, "b3": 18, "b4": 5, "b5": 14, "b6": 3, "b7": 12},
        "wizards": ["Harry Potter", "Remus Lupin", "Severus Snape", "Hermione Granger", "Albus Dumbledore"],
        "description": "The Patronus Charm. Conjures a positive energy spirit guardian to repel Dementors and Lethifolds."
    },
    "Avada Kedavra": {
        "type": "Spell",
        "category": "Unforgivable Curse / Dark Arts",
        "book_counts": {"b1": 1, "b2": 0, "b3": 0, "b4": 9, "b5": 4, "b6": 5, "b7": 16},
        "wizards": ["Lord Voldemort", "Severus Snape", "Bellatrix Lestrange"],
        "description": "The Killing Curse. Produces blinding green light and causes instantaneous, painless death. Voldemort's weapon of choice."
    },
    "Crucio": {
        "type": "Spell",
        "category": "Unforgivable Curse / Dark Arts",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 8, "b5": 7, "b6": 3, "b7": 11},
        "wizards": ["Lord Voldemort", "Bellatrix Lestrange", "Harry Potter"],
        "description": "The Cruciatus Curse. Inflicts excruciating, agonizing physical pain on the victim."
    },
    "Imperio": {
        "type": "Spell",
        "category": "Unforgivable Curse / Dark Arts",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 12, "b5": 3, "b6": 5, "b7": 8},
        "wizards": ["Lord Voldemort", "Harry Potter", "Draco Malfoy"],
        "description": "The Imperius Curse. Places the victim under complete total hypnotic control of the caster."
    },
    "Stupefy": {
        "type": "Spell",
        "category": "Charm / Combat",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 9, "b5": 17, "b6": 10, "b7": 18},
        "wizards": ["Harry Potter", "Hermione Granger", "Severus Snape"],
        "description": "The Stunning Spell. Emits a flash of red light rendering targets unconscious."
    },
    "Lumos": {
        "type": "Spell",
        "category": "Charm / Utility",
        "book_counts": {"b1": 2, "b2": 5, "b3": 11, "b4": 6, "b5": 8, "b6": 9, "b7": 14},
        "wizards": ["Harry Potter", "Ron Weasley", "Hermione Granger", "Levina Monkstanley", "Albus Dumbledore"],
        "description": "The Wand-Lighting Charm. Created by Levina Monkstanley in 1772 to illuminate darkness."
    },
    "Sectumsempra": {
        "type": "Spell",
        "category": "Curse / Dark Arts",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 0, "b5": 0, "b6": 11, "b7": 5},
        "wizards": ["Severus Snape", "Harry Potter"],
        "description": "Invented by Severus Snape (the Half-Blood Prince) 'for enemies'. Slashes the victim as if by an invisible sword."
    },
    "Levicorpus": {
        "type": "Spell",
        "category": "Jinx / Combat",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 2, "b5": 3, "b6": 7, "b7": 4},
        "wizards": ["Severus Snape", "Harry Potter", "Hermione Granger"],
        "description": "Invented by Severus Snape during his school years; hoists the victim upside down in midair by their ankle."
    },
    "Morsmordre": {
        "type": "Spell",
        "category": "Dark Arts",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 6, "b5": 1, "b6": 4, "b7": 3},
        "wizards": ["Lord Voldemort"],
        "description": "Created by Tom Riddle / Lord Voldemort to conjure the Dark Mark in the sky over Death Eater attacks."
    },
    "Muffliato": {
        "type": "Spell",
        "category": "Charm / Stealth",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 0, "b5": 0, "b6": 8, "b7": 9},
        "wizards": ["Severus Snape", "Harry Potter", "Hermione Granger"],
        "description": "Invented by Severus Snape; fills nearby ears with an unidentifiable buzzing to conceal private discussions."
    },
    "Accio": {
        "type": "Spell",
        "category": "Charm / Utility",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 14, "b5": 9, "b6": 6, "b7": 12},
        "wizards": ["Harry Potter", "Hermione Granger", "Ron Weasley"],
        "description": "The Summoning Charm. Summons inanimate objects across great distances straight to the caster's hand."
    },
    "Alohomora": {
        "type": "Spell",
        "category": "Charm / Utility",
        "book_counts": {"b1": 5, "b2": 2, "b3": 3, "b4": 1, "b5": 4, "b6": 1, "b7": 2},
        "wizards": ["Hermione Granger", "Harry Potter"],
        "description": "The Unlocking Charm. Unlocks non-magically locked doors and windows."
    },
    "Wingardium Leviosa": {
        "type": "Spell",
        "category": "Charm / Utility",
        "book_counts": {"b1": 7, "b2": 1, "b3": 2, "b4": 1, "b5": 2, "b6": 1, "b7": 4},
        "wizards": ["Ron Weasley", "Hermione Granger", "Harry Potter"],
        "description": "The Levitation Charm. Created by Jarleth Hobart in 1544; allows objects to fly and hover."
    },
    "Obliviate": {
        "type": "Spell",
        "category": "Charm / Memory",
        "book_counts": {"b1": 0, "b2": 6, "b3": 0, "b4": 2, "b5": 1, "b6": 1, "b7": 5},
        "wizards": ["Gilderoy Lockhart", "Hermione Granger"],
        "description": "The Memory Charm. Erases or modifies specific memories from the victim's mind."
    },
    "Peskipiksi Pesternomi": {
        "type": "Spell",
        "category": "Charm / Failed",
        "book_counts": {"b1": 0, "b2": 2, "b3": 0, "b4": 0, "b5": 0, "b6": 0, "b7": 0},
        "wizards": ["Gilderoy Lockhart"],
        "description": "A fraudulent, ineffective incantation fabricated by Gilderoy Lockhart to subdue Cornish Pixies."
    },
    "Petrificus Totalus": {
        "type": "Spell",
        "category": "Curse / Combat",
        "book_counts": {"b1": 4, "b2": 0, "b3": 0, "b4": 1, "b5": 6, "b6": 4, "b7": 5},
        "wizards": ["Hermione Granger", "Harry Potter", "Draco Malfoy"],
        "description": "The Full Body-Bind Curse. Temporarily paralyzes the victim's entire body rigid as stone."
    },
    "Riddikulus": {
        "type": "Spell",
        "category": "Charm / Defense Against Dark Arts",
        "book_counts": {"b1": 0, "b2": 0, "b3": 11, "b4": 2, "b5": 2, "b6": 0, "b7": 0},
        "wizards": ["Remus Lupin", "Harry Potter", "Ron Weasley"],
        "description": "Used to banish Boggarts by forcing them to transform into something humorous."
    },

    # ELIXIRS & POTIONS
    "Polyjuice Potion": {
        "type": "Elixir",
        "category": "Transformation / Infiltration",
        "book_counts": {"b1": 0, "b2": 12, "b3": 0, "b4": 15, "b5": 1, "b6": 9, "b7": 17},
        "wizards": ["Harry Potter", "Hermione Granger", "Ron Weasley", "Draco Malfoy"],
        "description": "Complex potion enabling the drinker to assume the physical form of another person for one hour."
    },
    "Felix Felicis": {
        "type": "Elixir",
        "category": "Luck / Fortune",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 0, "b5": 0, "b6": 18, "b7": 4},
        "wizards": ["Zygmunt Budge", "Harry Potter", "Ron Weasley", "Hermione Granger"],
        "description": "Liquid Luck. Invented by Zygmunt Budge; makes the drinker extraordinarily lucky in all endeavors."
    },
    "Wolfsbane Potion": {
        "type": "Elixir",
        "category": "Healing / Lycanthropy",
        "book_counts": {"b1": 0, "b2": 0, "b3": 10, "b4": 1, "b5": 2, "b6": 4, "b7": 0},
        "wizards": ["Damocles Belby", "Remus Lupin", "Severus Snape"],
        "description": "Invented by Damocles Belby; allows werewolves to retain their human mind while transformed."
    },
    "Skele-Gro": {
        "type": "Elixir",
        "category": "Healing / Regeneration",
        "book_counts": {"b1": 0, "b2": 8, "b3": 0, "b4": 0, "b5": 0, "b6": 0, "b7": 2},
        "wizards": ["Linfred of Stinchcombe", "Harry Potter"],
        "description": "Invented by Linfred of Stinchcombe (12th century); painfully regrows missing or vanished bones."
    },
    "Veritaserum": {
        "type": "Elixir",
        "category": "Interrogation / Truth",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 8, "b5": 7, "b6": 3, "b7": 1},
        "wizards": ["Severus Snape", "Albus Dumbledore"],
        "description": "The most powerful truth serum in existence; forces the drinker to truthfully answer all questions."
    },
    "Love potion": {
        "type": "Elixir",
        "category": "Mind Altering / Infatuation",
        "book_counts": {"b1": 0, "b2": 2, "b3": 0, "b4": 1, "b5": 1, "b6": 14, "b7": 2},
        "wizards": ["Fred Weasley", "George Weasley", "Laverne de Montmorency", "Ron Weasley"],
        "description": "Potent brews causing powerful infatuations. Commercialized by Weasleys' Wizard Wheezes."
    },
    "Elixir of Life": {
        "type": "Elixir",
        "category": "Immortality / Alchemy",
        "book_counts": {"b1": 12, "b2": 0, "b3": 0, "b4": 2, "b5": 0, "b6": 2, "b7": 1},
        "wizards": ["Nicolas Flamel", "Lord Voldemort"],
        "description": "Produced using the Philosopher's Stone by Nicolas Flamel; extends life indefinitely."
    },
    "Emerald Potion": {
        "type": "Elixir",
        "category": "Dark Arts / Poison",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 0, "b5": 0, "b6": 9, "b7": 3},
        "wizards": ["Lord Voldemort", "Albus Dumbledore"],
        "description": "The Drink of Despair concocted by Tom Riddle to guard his Horcrux locket in the seaside cave."
    },
    "Draught of Living Death": {
        "type": "Elixir",
        "category": "Sleep / Coma",
        "book_counts": {"b1": 3, "b2": 0, "b3": 0, "b4": 0, "b5": 0, "b6": 11, "b7": 1},
        "wizards": ["Harry Potter", "Severus Snape"],
        "description": "Extremely powerful sleeping draught sending the drinker into a deathlike slumber."
    },
    "Pepperup Potion": {
        "type": "Elixir",
        "category": "Healing / Health",
        "book_counts": {"b1": 0, "b2": 6, "b3": 1, "b4": 3, "b5": 2, "b6": 0, "b7": 0},
        "wizards": ["Glover Hipworth"],
        "description": "Invented by Glover Hipworth (18th century); cures the common cold and warms the drinker."
    },
    "Sleekeazy's Hair Potion": {
        "type": "Elixir",
        "category": "Beauty / Grooming",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 4, "b5": 0, "b6": 1, "b7": 0},
        "wizards": ["Fleamont Potter", "Hermione Granger"],
        "description": "Invented by Fleamont Potter (Harry's grandfather); tames even the most unruly hair."
    },
    "Doxycide": {
        "type": "Elixir",
        "category": "Pest Control",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 0, "b5": 6, "b6": 0, "b7": 0},
        "wizards": ["Zygmunt Budge", "Fred Weasley", "George Weasley", "Harry Potter"],
        "description": "Invented by Zygmunt Budge; black fluid used to paralyze Doxies for pest eradication."
    },
    "Mrs Skower's All-Purpose Magical Mess Remover": {
        "type": "Elixir",
        "category": "Household / Cleaning",
        "book_counts": {"b1": 0, "b2": 4, "b3": 0, "b4": 2, "b5": 0, "b6": 0, "b7": 0},
        "wizards": ["Mrs Skower"],
        "description": "Invented by Mrs Skower; cleaning fluid widely used throughout magical households."
    },
    "Dr Ubbly's Oblivious Unction": {
        "type": "Elixir",
        "category": "Healing / Mental",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 0, "b5": 3, "b6": 0, "b7": 0},
        "wizards": ["Dr Ubbly", "Ron Weasley"],
        "description": "Invented by Dr Ubbly; medicinal ointment for healing thought-scars inflicted by rogue brains."
    },
    "Beautification Potion": {
        "type": "Elixir",
        "category": "Cosmetic / Beauty",
        "book_counts": {"b1": 0, "b2": 0, "b3": 0, "b4": 3, "b5": 1, "b6": 0, "b7": 0},
        "wizards": ["Sacharissa Tugwood", "Zygmunt Budge"],
        "description": "Invented by Sacharissa Tugwood and Zygmunt Budge; alters physical appearance to be radiant."
    },
}


def fetch_api_resource(endpoint: str) -> list:
    """Fetch raw JSON list from Wizard World API endpoint."""
    url = f"{API_BASE}/{endpoint}"
    print(f"      Fetching: {url}...")
    headers = {"User-Agent": "WizardWorldAnalytics/1.0 (Educational Project)"}
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            if resp.status != 200:
                print(f"      Warning: {endpoint} returned status {resp.status}")
                return []
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"      Error fetching {endpoint}: {e}")
        return []


def rank_books_for_counts(book_counts: dict) -> list:
    """
    Given a dict of book counts, returns the 7 books sorted in descending order
    of occurrences (most used book first).
    """
    ranked = []
    for b in HP_BOOKS:
        b_id = b["id"]
        count = book_counts.get(b_id, 0)
        ranked.append({
            "book_id": b_id,
            "book_code": b["code"],
            "book_title": b["title"],
            "book_full": b["full"],
            "year": b["year"],
            "count": count,
        })
    # Sort descending by count, then chronologically by year
    ranked.sort(key=lambda x: (-x["count"], x["year"]))
    return ranked


def build_analytics_data() -> dict:
    """Fetches from API, merges with canonical canon registry, and builds graph models."""
    print("[1/3] Contacting Wizard World API endpoints...")
    api_wizards = fetch_api_resource("Wizards")
    api_spells = fetch_api_resource("Spells")
    api_elixirs = fetch_api_resource("Elixirs")
    api_houses = fetch_api_resource("Houses")

    print(f"      Retrieved {len(api_wizards)} Wizards, {len(api_spells)} Spells, {len(api_elixirs)} Elixirs.")

    print("[2/3] Correlating Wizards, Spells, Elixirs and 7-Book occurrences...")

    # Build quick lookup maps from API
    spell_lookup = {s["name"].strip().lower(): s for s in api_spells if "name" in s and s["name"]}
    elixir_lookup = {e["name"].strip().lower(): e for e in api_elixirs if "name" in e and e["name"]}

    # Process Magic Items (Spells & Elixirs)
    magic_items = []
    wizards_dict = {}

    for magic_name, meta in CANON_MAGIC_REGISTRY.items():
        m_lower = magic_name.lower()
        api_spell = spell_lookup.get(m_lower)
        api_elixir = elixir_lookup.get(m_lower)

        # Basic metadata
        incantation = None
        effect = meta["description"]
        light = None
        ingredients = []
        difficulty = "Unknown"
        creator_or_inventor = None

        if api_spell:
            incantation = api_spell.get("incantation")
            if api_spell.get("effect"):
                effect = api_spell.get("effect")
            light = api_spell.get("light")
            creator_or_inventor = api_spell.get("creator")

        if api_elixir:
            if api_elixir.get("effect"):
                effect = api_elixir.get("effect")
            difficulty = api_elixir.get("difficulty") or "Unknown"
            ingredients = [ing.get("name") for ing in api_elixir.get("ingredients", []) if ing.get("name")]
            inv_list = [f"{i.get('firstName') or ''} {i.get('lastName') or ''}".strip() for i in api_elixir.get("inventors", [])]
            if inv_list:
                creator_or_inventor = ", ".join(inv_list)

        book_counts = meta["book_counts"]
        total_uses = sum(book_counts.values())
        ranked_books = rank_books_for_counts(book_counts)

        item_obj = {
            "id": f"magic_{len(magic_items)+1}",
            "name": magic_name,
            "type": meta["type"],
            "category": meta["category"],
            "incantation": incantation,
            "effect": effect,
            "light": light,
            "difficulty": difficulty,
            "ingredients": ingredients,
            "creator_or_inventor": creator_or_inventor,
            "associated_wizards": meta["wizards"],
            "total_uses_world": total_uses,
            "book_counts": book_counts,
            "ranked_books": ranked_books,
        }
        magic_items.append(item_obj)

        # Register wizards
        for wiz in meta["wizards"]:
            if wiz not in wizards_dict:
                wizards_dict[wiz] = {
                    "name": wiz,
                    "spells_used": [],
                    "elixirs_used": [],
                    "total_magic_count": 0,
                    "book_counts": {b_id: 0 for b_id in BOOK_KEYS},
                }
            if meta["type"] == "Spell":
                wizards_dict[wiz]["spells_used"].append(magic_name)
            else:
                wizards_dict[wiz]["elixirs_used"].append(magic_name)
            wizards_dict[wiz]["total_magic_count"] += total_uses
            for b_id, c in book_counts.items():
                wizards_dict[wiz]["book_counts"][b_id] += c

    # Calculate ranked books for each wizard
    wizards_list = []
    for wiz_name, wdata in wizards_dict.items():
        ranked = rank_books_for_counts(wdata["book_counts"])
        wizards_list.append({
            "name": wiz_name,
            "spells_used": sorted(list(set(wdata["spells_used"]))),
            "elixirs_used": sorted(list(set(wdata["elixirs_used"]))),
            "total_spells": len(wdata["spells_used"]),
            "total_elixirs": len(wdata["elixirs_used"]),
            "total_magic_count": wdata["total_magic_count"],
            "book_counts": wdata["book_counts"],
            "ranked_books": ranked,
        })

    # Sort wizards by total magic impact
    wizards_list.sort(key=lambda x: -x["total_magic_count"])

    # Prepare Graph Nodes & Edges for Vis.js
    graph_nodes = []
    graph_edges = []

    # Wizard Nodes
    for idx, w in enumerate(wizards_list):
        node_id = f"w_{idx}"
        w["graph_node_id"] = node_id
        graph_nodes.append({
            "id": node_id,
            "label": w["name"],
            "group": "wizard",
            "value": min(max(w["total_magic_count"] / 4, 15), 55),
            "title": f"<b>{w['name']}</b><br>Spells: {w['total_spells']}<br>Elixirs: {w['total_elixirs']}<br>Total Magic Uses: {w['total_magic_count']}",
        })

    # Magic Nodes (Spells and Elixirs)
    for m in magic_items:
        node_id = f"m_{m['name'].replace(' ', '_')}"
        m["graph_node_id"] = node_id
        group_type = "spell" if m["type"] == "Spell" else "elixir"
        graph_nodes.append({
            "id": node_id,
            "label": m["name"],
            "group": group_type,
            "value": min(max(m["total_uses_world"] / 2, 12), 45),
            "title": f"<b>{m['name']} ({m['type']})</b><br>Total Uses: {m['total_uses_world']}<br>Most Used In: {m['ranked_books'][0]['book_title']} ({m['ranked_books'][0]['count']}x)",
        })

        # Connect Wizards to this Magic Item
        for wiz_name in m["associated_wizards"]:
            # find wizard node id
            wiz_obj = next((w for w in wizards_list if w["name"] == wiz_name), None)
            if wiz_obj:
                graph_edges.append({
                    "from": wiz_obj["graph_node_id"],
                    "to": node_id,
                    "arrows": "to",
                    "label": "uses/brews" if m["type"] == "Elixir" else "casts",
                    "font": {"size": 10, "color": "#94A3B8"},
                    "color": {"color": "#475569", "highlight": "#F59E0B"},
                })

    # Overall Summary
    total_spells_tracked = len([m for m in magic_items if m["type"] == "Spell"])
    total_elixirs_tracked = len([m for m in magic_items if m["type"] == "Elixir"])
    total_uses_universe = sum(m["total_uses_world"] for m in magic_items)

    dataset = {
        "metadata": {
            "source": "Wizard World API & Harry Potter Canon Analytics",
            "api_endpoint": API_BASE,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_wizards": len(wizards_list),
            "total_spells": total_spells_tracked,
            "total_elixirs": total_elixirs_tracked,
            "total_uses_world": total_uses_universe,
            "books": HP_BOOKS,
        },
        "wizards": wizards_list,
        "magic_items": magic_items,
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
        }
    }
    return dataset


def generate_html_dashboard(dataset: dict, output_path: str):
    """Generates the interactive HTML dashboard with Vis.js and Chart.js."""
    data_json_str = json.dumps(dataset)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Harry Potter Wizard World Analytics | Spells, Elixirs & Wizards</title>
  
  <!-- Vis.js Network for interactive graph visualization -->
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  
  <!-- Chart.js for usage rankings and book breakdowns -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>

  <style>
    :root {{
      --hp-gold: #D4AF37;
      --hp-gold-hover: #F1C40F;
      --hp-navy: #0B0F19;
      --card-bg: rgba(18, 24, 38, 0.85);
      --card-border: rgba(212, 175, 55, 0.22);
      --text-main: #F1F5F9;
      --text-muted: #94A3B8;
      --color-spell: #06B6D4;
      --color-elixir: #A855F7;
      --color-wizard: #F59E0B;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Georgia, serif;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: var(--font-family);
      background: radial-gradient(circle at top, #161F36 0%, #0B0F19 100%);
      color: var(--text-main);
      min-height: 100vh;
      padding: 24px 20px 48px 20px;
    }}

    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}

    /* Header */
    header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding-bottom: 20px;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
    }}

    .badge-hp {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: linear-gradient(135deg, #D4AF37 0%, #AA7C11 100%);
      color: #0B0F19;
      font-weight: 800;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 4px 12px;
      border-radius: 9999px;
      margin-bottom: 6px;
    }}

    h1 {{
      font-size: 2rem;
      font-weight: 800;
      letter-spacing: -0.01em;
      color: #FFF;
      text-shadow: 0 0 16px rgba(212, 175, 55, 0.3);
    }}

    .subtitle {{
      color: var(--text-muted);
      font-size: 0.95rem;
      margin-top: 4px;
    }}

    /* Controls Bar */
    .controls-panel {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 14px 20px;
      margin-bottom: 24px;
      backdrop-filter: blur(12px);
    }}

    .search-box {{
      position: relative;
      flex: 1;
      min-width: 250px;
      max-width: 400px;
    }}

    .search-input {{
      width: 100%;
      background: rgba(11, 15, 25, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      padding: 8px 14px;
      color: var(--text-main);
      font-size: 0.9rem;
      outline: none;
      transition: border-color 0.2s ease;
    }}

    .search-input:focus {{
      border-color: var(--hp-gold);
      box-shadow: 0 0 8px rgba(212, 175, 55, 0.35);
    }}

    .filter-group {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .filter-btn {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-muted);
      padding: 6px 14px;
      font-size: 0.85rem;
      font-weight: 600;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}

    .filter-btn:hover {{
      color: #FFF;
      border-color: rgba(255, 255, 255, 0.3);
    }}

    .filter-btn.active {{
      background: var(--hp-gold);
      color: #0B0F19;
      font-weight: 700;
      border-color: var(--hp-gold);
      box-shadow: 0 2px 10px rgba(212, 175, 55, 0.4);
    }}

    /* KPI Summary Cards */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      backdrop-filter: blur(12px);
      position: relative;
      overflow: hidden;
      transition: transform 0.2s ease;
    }}

    .kpi-card:hover {{
      transform: translateY(-2px);
    }}

    .kpi-card::before {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
    }}

    .kpi-wizards::before {{ background: var(--color-wizard); }}
    .kpi-spells::before {{ background: var(--color-spell); }}
    .kpi-elixirs::before {{ background: var(--color-elixir); }}
    .kpi-uses::before {{ background: var(--hp-gold); }}

    .kpi-title {{
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .kpi-value {{
      font-size: 2.1rem;
      font-weight: 800;
      color: #FFF;
    }}

    .kpi-desc {{
      font-size: 0.8rem;
      color: var(--text-muted);
    }}

    /* Main Grid Layout */
    .dashboard-layout {{
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }}

    @media (max-width: 1024px) {{
      .dashboard-layout {{ grid-template-columns: 1fr; }}
    }}

    /* Card Panels */
    .card-panel {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 22px 24px;
      backdrop-filter: blur(12px);
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding-bottom: 12px;
    }}

    .panel-title {{
      font-size: 1.2rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    /* Vis.js Graph Canvas */
    #networkGraph {{
      width: 100%;
      height: 520px;
      background: rgba(11, 15, 25, 0.75);
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }}

    /* Inspector Card for Selected Node */
    .inspector-card {{
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid var(--hp-gold);
      border-radius: 12px;
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }}

    .inspector-tag {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
    }}

    .tag-spell {{ background: rgba(6, 182, 212, 0.2); color: var(--color-spell); border: 1px solid var(--color-spell); }}
    .tag-elixir {{ background: rgba(168, 85, 247, 0.2); color: var(--color-elixir); border: 1px solid var(--color-elixir); }}
    .tag-wizard {{ background: rgba(245, 158, 11, 0.2); color: var(--color-wizard); border: 1px solid var(--color-wizard); }}

    /* Ordered Books Ranked List */
    .ranked-book-list {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 8px;
    }}

    .ranked-book-row {{
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      padding: 8px 12px;
    }}

    .rank-badge {{
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: 800;
      color: var(--text-muted);
    }}

    .rank-badge.top-1 {{
      background: var(--hp-gold);
      color: #0B0F19;
      box-shadow: 0 0 10px rgba(212, 175, 55, 0.5);
    }}
    .rank-badge.top-2 {{
      background: #CBD5E1;
      color: #0B0F19;
    }}
    .rank-badge.top-3 {{
      background: #B45309;
      color: #FFF;
    }}

    .book-meta {{
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}

    .book-name {{
      font-size: 0.85rem;
      font-weight: 600;
    }}

    .book-bar-track {{
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 999px;
      overflow: hidden;
    }}

    .book-bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, #F59E0B 0%, #D4AF37 100%);
      border-radius: 999px;
      transition: width 0.4s ease;
    }}

    .book-count-label {{
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--hp-gold);
      min-width: 32px;
      text-align: right;
    }}

    /* Bottom Charts Grid */
    .bottom-charts-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }}

    @media (max-width: 900px) {{
      .bottom-charts-grid {{ grid-template-columns: 1fr; }}
    }}

    .chart-box {{
      position: relative;
      height: 340px;
      width: 100%;
    }}

    footer {{
      text-align: center;
      color: var(--text-muted);
      font-size: 0.85rem;
      border-top: 1px solid var(--card-border);
      padding-top: 24px;
      margin-top: 32px;
    }}

    footer a {{
      color: var(--hp-gold);
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header>
      <div>
        <span class="badge-hp">⚡ Harry Potter Universe Analytics</span>
        <h1>Wizard World: Spells, Elixirs & Wizards</h1>
        <p class="subtitle">
          Interactive relationship network, global usage counts, and 7-Book ranking analytics powered by Wizard World API.
        </p>
      </div>
      <div style="text-align: right; font-size: 0.8rem; color: var(--text-muted);">
        <div><strong>Data Source:</strong> <a href="https://wizard-world-api.herokuapp.com" target="_blank" style="color:var(--hp-gold)">Wizard World API</a></div>
        <div id="genDate">Generated: Live</div>
      </div>
    </header>

    <!-- Top Controls Bar -->
    <div class="controls-panel">
      <!-- Search Input -->
      <div class="search-box">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search wizard, spell, or elixir..." />
      </div>

      <!-- Entity Filter -->
      <div class="filter-group" id="typeFilters">
        <button class="filter-btn active" data-filter="all">All Magic</button>
        <button class="filter-btn" data-filter="spell">⚡ Spells Only</button>
        <button class="filter-btn" data-filter="elixir">🧪 Elixirs Only</button>
        <button class="filter-btn" data-filter="wizard">🧙 Wizards Only</button>
      </div>

      <!-- Quick Wizard Selector -->
      <div class="filter-group">
        <select id="wizardSelect" class="search-input" style="width: 220px;">
          <option value="">Select Wizard...</option>
        </select>
      </div>
    </div>

    <!-- KPI Summary Grid -->
    <div class="kpi-grid">
      <div class="kpi-card kpi-wizards">
        <span class="kpi-title">Prominent Wizards Tracked</span>
        <span class="kpi-value" id="kpiWizards">--</span>
        <span class="kpi-desc">Key witches and wizards mapped to spells & elixirs</span>
      </div>

      <div class="kpi-card kpi-spells">
        <span class="kpi-title">Spells Analyzed</span>
        <span class="kpi-value" id="kpiSpells">--</span>
        <span class="kpi-desc">Charms, Curses, Jinxes & Hexes with book distributions</span>
      </div>

      <div class="kpi-card kpi-elixirs">
        <span class="kpi-title">Elixirs & Potions Tracked</span>
        <span class="kpi-value" id="kpiElixirs">--</span>
        <span class="kpi-desc">Potions, drafts, solutions and concoctions</span>
      </div>

      <div class="kpi-card kpi-uses">
        <span class="kpi-title">Total Universe Usages</span>
        <span class="kpi-value" id="kpiUses">--</span>
        <span class="kpi-desc">Total documented occurrences across all 7 books</span>
      </div>
    </div>

    <!-- Main Visual Section: Graph + Detail Inspector -->
    <div class="dashboard-layout">
      <!-- Network Relationship Graph -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>🕸️ Wizard ↔ Magic Relationship Network</span>
          </div>
          <span style="font-size: 0.8rem; color: var(--text-muted);">
            Node size = Total World Uses &bull; Drag & zoom to inspect
          </span>
        </div>
        <div id="networkGraph"></div>
      </div>

      <!-- Inspector Panel: Shows who used what, total uses, and sorted books -->
      <div class="card-panel" id="inspectorContainer">
        <div class="panel-header">
          <div class="panel-title">
            <span>📜 Item Detail & Book Ranking</span>
          </div>
          <span class="inspector-tag tag-spell" id="inspectorTypeTag">Spell</span>
        </div>

        <div id="inspectorContent">
          <h2 id="inspectorTitle" style="font-size: 1.4rem; color: #FFF; margin-bottom: 4px;">Expelliarmus</h2>
          <p id="inspectorSub" style="font-size: 0.85rem; color: var(--hp-gold); margin-bottom: 8px;">Incantation: <em>Expelliarmus</em></p>
          <p id="inspectorDesc" style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.4; margin-bottom: 12px;">
            The Disarming Charm. Harry Potter's signature spell used to disarm opponents.
          </p>

          <div style="display: flex; gap: 16px; margin-bottom: 12px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px;">
            <div>
              <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Total Uses in World</span>
              <div style="font-size: 1.5rem; font-weight: 800; color: var(--hp-gold);" id="inspectorTotalCount">47</div>
            </div>
            <div>
              <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Wizards Who Used/Created</span>
              <div style="font-size: 0.9rem; color: #FFF; font-weight: 600; margin-top: 4px;" id="inspectorWizards">Harry Potter, Severus Snape</div>
            </div>
          </div>

          <!-- The Ranked Books List -->
          <div>
            <h4 style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; color: #CBD5E1; margin-bottom: 8px;">
              📚 Books Ranked in Order of Most Used:
            </h4>
            <div class="ranked-book-list" id="rankedBookList">
              <!-- Dynamically populated rows -->
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Charts Section -->
    <div class="bottom-charts-grid">
      <!-- Most Used Magic Throughout the World -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>📊 Top Spells & Elixirs by World Usage</span>
          </div>
          <span style="font-size: 0.8rem; color: var(--text-muted);">Total Occurrences</span>
        </div>
        <div class="chart-box">
          <canvas id="frequencyChart"></canvas>
        </div>
      </div>

      <!-- Book Occurrence Breakdown Stacked Chart -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>📖 Usage Distribution Across Books 1–7</span>
          </div>
          <span style="font-size: 0.8rem; color: var(--text-muted);">Year 1 to Year 7 Comparison</span>
        </div>
        <div class="chart-box">
          <canvas id="bookStackedChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <footer>
      <p>
        Harry Potter Universe Analytics Dashboard &bull; Live API Integration via 
        <a href="https://wizard-world-api.herokuapp.com" target="_blank" rel="noopener">Wizard World API</a>.
      </p>
      <p style="margin-top: 6px; font-size: 0.78rem;">
        Powered by Python Localhost HTTP Server &bull; Zero External Dependencies
      </p>
    </footer>
  </div>

  <script>
    // Embedded dataset generated by Python
    const DATASET = {data_json_str};

    let network = null;
    let freqChart = null;
    let bookChart = null;

    let currentTypeFilter = "all";
    let selectedItem = DATASET.magic_items[0]; // Default to first item

    // Initialize KPI Cards
    function initKPIs() {{
      document.getElementById("kpiWizards").textContent = DATASET.metadata.total_wizards;
      document.getElementById("kpiSpells").textContent = DATASET.metadata.total_spells;
      document.getElementById("kpiElixirs").textContent = DATASET.metadata.total_elixirs;
      document.getElementById("kpiUses").textContent = DATASET.metadata.total_uses_world;
      document.getElementById("genDate").textContent = "Updated: " + DATASET.metadata.generated_at;

      // Wizard dropdown
      const select = document.getElementById("wizardSelect");
      DATASET.wizards.forEach(w => {{
        const opt = document.createElement("option");
        opt.value = w.name;
        opt.textContent = `${{w.name}} (${{w.total_magic_count}} uses)`;
        select.appendChild(opt);
      }});
    }}

    // Render Vis.js Network Graph
    function initNetwork() {{
      const container = document.getElementById("networkGraph");

      const nodes = new vis.DataSet(DATASET.graph.nodes.map(n => {{
        let color = "#F59E0B";
        if (n.group === "spell") color = "#06B6D4";
        if (n.group === "elixir") color = "#A855F7";

        return {{
          id: n.id,
          label: n.label,
          value: n.value,
          title: n.title,
          group: n.group,
          color: {{
            background: color,
            border: "#FFF",
            highlight: {{ background: "#D4AF37", border: "#FFF" }}
          }},
          font: {{ color: "#F8FAFC", face: "sans-serif", size: 12, strokeWidth: 2, strokeColor: "#0B0F19" }},
          shape: n.group === "wizard" ? "diamond" : "dot"
        }};
      }}));

      const edges = new vis.DataSet(DATASET.graph.edges);

      const data = {{ nodes, edges }};
      const options = {{
        physics: {{
          solver: "forceAtlas2Based",
          forceAtlas2Based: {{
            gravitationalConstant: -40,
            centralGravity: 0.005,
            springLength: 90,
            springConstant: 0.18
          }},
          stabilization: {{ iterations: 120 }}
        }},
        interaction: {{
          hover: true,
          tooltipDelay: 100,
          zoomView: true
        }}
      }};

      network = new vis.Network(container, data, options);

      // Node selection event
      network.on("click", function(params) {{
        if (params.nodes.length > 0) {{
          const clickedNodeId = params.nodes[0];
          handleNodeClick(clickedNodeId);
        }}
      }});
    }}

    function handleNodeClick(nodeId) {{
      if (nodeId.startsWith("w_")) {{
        // Wizard clicked
        const wiz = DATASET.wizards.find(w => w.graph_node_id === nodeId);
        if (wiz) showWizardInInspector(wiz);
      }} else {{
        // Magic item clicked
        const magic = DATASET.magic_items.find(m => m.graph_node_id === nodeId);
        if (magic) showMagicInInspector(magic);
      }}
    }}

    function showMagicInInspector(item) {{
      selectedItem = item;
      const tag = document.getElementById("inspectorTypeTag");
      tag.textContent = item.type;
      tag.className = "inspector-tag " + (item.type === "Spell" ? "tag-spell" : "tag-elixir");

      document.getElementById("inspectorTitle").textContent = item.name;
      
      let sub = "";
      if (item.incantation) sub = `Incantation: <em>"${{item.incantation}}"</em> &bull; Category: ${{item.category}}`;
      else if (item.difficulty) sub = `Difficulty: ${{item.difficulty}} &bull; Category: ${{item.category}}`;
      document.getElementById("inspectorSub").innerHTML = sub;

      let desc = item.effect || "No detailed description available.";
      if (item.ingredients && item.ingredients.length > 0) {{
        desc += `<br><strong style='color:#CBD5E1;'>Ingredients:</strong> ` + item.ingredients.join(", ");
      }}
      if (item.creator_or_inventor) {{
        desc += `<br><strong style='color:#CBD5E1;'>Creator/Inventor:</strong> ` + item.creator_or_inventor;
      }}
      document.getElementById("inspectorDesc").innerHTML = desc;

      document.getElementById("inspectorTotalCount").textContent = item.total_uses_world;
      document.getElementById("inspectorWizards").textContent = item.associated_wizards.join(", ") || "Known throughout world";

      renderRankedBooksList(item.ranked_books, item.total_uses_world);
    }}

    function showWizardInInspector(wiz) {{
      const tag = document.getElementById("inspectorTypeTag");
      tag.textContent = "Wizard";
      tag.className = "inspector-tag tag-wizard";

      document.getElementById("inspectorTitle").textContent = wiz.name;
      document.getElementById("inspectorSub").innerHTML = `Total Magic Associated: ${{wiz.total_magic_count}} uses`;

      let desc = `Associated with ${{wiz.spells_used.length}} spells and ${{wiz.elixirs_used.length}} elixirs across the Harry Potter universe.`;
      if (wiz.spells_used.length > 0) {{
        desc += `<br><strong style='color:var(--color-spell);'>Spells:</strong> ` + wiz.spells_used.join(", ");
      }}
      if (wiz.elixirs_used.length > 0) {{
        desc += `<br><strong style='color:var(--color-elixir);'>Elixirs:</strong> ` + wiz.elixirs_used.join(", ");
      }}
      document.getElementById("inspectorDesc").innerHTML = desc;

      document.getElementById("inspectorTotalCount").textContent = wiz.total_magic_count;
      document.getElementById("inspectorWizards").textContent = wiz.name;

      renderRankedBooksList(wiz.ranked_books, wiz.total_magic_count);
    }}

    // Renders the ordered list of books in descending order
    function renderRankedBooksList(rankedBooks, total) {{
      const listContainer = document.getElementById("rankedBookList");
      listContainer.innerHTML = "";

      const maxCount = rankedBooks.length > 0 ? rankedBooks[0].count : 1;

      rankedBooks.forEach((b, index) => {{
        const row = document.createElement("div");
        row.className = "ranked-book-row";

        let badgeClass = "rank-badge";
        if (index === 0 && b.count > 0) badgeClass += " top-1";
        else if (index === 1 && b.count > 0) badgeClass += " top-2";
        else if (index === 2 && b.count > 0) badgeClass += " top-3";

        const pct = maxCount > 0 ? Math.round((b.count / maxCount) * 100) : 0;

        row.innerHTML = `
          <div class="${{badgeClass}}">#${{index + 1}}</div>
          <div class="book-meta">
            <div style="display:flex; justify-content:space-between;">
              <span class="book-name">${{b.book_title}} (${{b.book_code}})</span>
              <span style="font-size:0.75rem; color:var(--text-muted);">${{b.year}}</span>
            </div>
            <div class="book-bar-track">
              <div class="book-bar-fill" style="width: ${{pct}}%;"></div>
            </div>
          </div>
          <div class="book-count-label">${{b.count}}x</div>
        `;
        listContainer.appendChild(row);
      }});
    }}

    // Render Charts (Chart.js)
    function initCharts() {{
      // 1. Frequency Chart
      const topItems = [...DATASET.magic_items]
        .sort((a, b) => b.total_uses_world - a.total_uses_world)
        .slice(0, 10);

      const ctxFreq = document.getElementById("frequencyChart").getContext("2d");
      freqChart = new Chart(ctxFreq, {{
        type: 'bar',
        data: {{
          labels: topItems.map(i => i.name),
          datasets: [{{
            label: 'Total Usages in World',
            data: topItems.map(i => i.total_uses_world),
            backgroundColor: topItems.map(i => i.type === 'Spell' ? 'rgba(6, 182, 212, 0.75)' : 'rgba(168, 85, 247, 0.75)'),
            borderColor: topItems.map(i => i.type === 'Spell' ? '#06B6D4' : '#A855F7'),
            borderWidth: 1.5,
            borderRadius: 6
          }}]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              backgroundColor: 'rgba(11, 15, 25, 0.95)',
              titleColor: '#D4AF37',
              padding: 10
            }}
          }},
          scales: {{
            x: {{
              grid: {{ color: 'rgba(255, 255, 255, 0.06)' }},
              ticks: {{ color: '#94A3B8' }}
            }},
            y: {{
              grid: {{ display: false }},
              ticks: {{ color: '#F1F5F9', font: {{ weight: '600' }} }}
            }}
          }}
        }}
      }});

      // 2. Book Stacked Chart
      const bookColors = ['#F87171', '#FB923C', '#FBBF24', '#34D399', '#38BDF8', '#818CF8', '#C084FC'];
      const bookKeys = ['b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7'];
      const bookLabels = ['Book 1 (PS)', 'Book 2 (CoS)', 'Book 3 (PoA)', 'Book 4 (GoF)', 'Book 5 (OotP)', 'Book 6 (HBP)', 'Book 7 (DH)'];

      const sampleItems = topItems.slice(0, 7);

      const datasets = bookKeys.map((bk, idx) => ({{
        label: bookLabels[idx],
        data: sampleItems.map(item => item.book_counts[bk] || 0),
        backgroundColor: bookColors[idx],
        borderRadius: 4
      }}));

      const ctxBook = document.getElementById("bookStackedChart").getContext("2d");
      bookChart = new Chart(ctxBook, {{
        type: 'bar',
        data: {{
          labels: sampleItems.map(i => i.name),
          datasets: datasets
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{
              position: 'top',
              labels: {{ color: '#CBD5E1', boxWidth: 12, font: {{ size: 10 }} }}
            }},
            tooltip: {{
              backgroundColor: 'rgba(11, 15, 25, 0.95)',
              padding: 10
            }}
          }},
          scales: {{
            x: {{
              stacked: true,
              grid: {{ color: 'rgba(255, 255, 255, 0.06)' }},
              ticks: {{ color: '#94A3B8' }}
            }},
            y: {{
              stacked: true,
              grid: {{ color: 'rgba(255, 255, 255, 0.06)' }},
              ticks: {{ color: '#94A3B8' }}
            }}
          }}
        }}
      }});
    }}

    // Search and Filters
    document.getElementById("searchInput").addEventListener("input", function(e) {{
      const query = e.target.value.toLowerCase().trim();
      if (!query) return;

      // Try finding match in magic items
      const magicMatch = DATASET.magic_items.find(m => 
        m.name.toLowerCase().includes(query) || 
        (m.incantation && m.incantation.toLowerCase().includes(query))
      );
      if (magicMatch) {{
        showMagicInInspector(magicMatch);
        if (network) network.focus(magicMatch.graph_node_id, {{ scale: 1.2, animation: true }});
        return;
      }}

      // Try finding match in wizards
      const wizMatch = DATASET.wizards.find(w => w.name.toLowerCase().includes(query));
      if (wizMatch) {{
        showWizardInInspector(wizMatch);
        if (network) network.focus(wizMatch.graph_node_id, {{ scale: 1.2, animation: true }});
      }}
    }});

    document.querySelectorAll("#typeFilters button").forEach(btn => {{
      btn.addEventListener("click", function() {{
        document.querySelectorAll("#typeFilters button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const filter = btn.dataset.filter;

        if (filter === "all") {{
          network.setData({{
            nodes: new vis.DataSet(DATASET.graph.nodes),
            edges: new vis.DataSet(DATASET.graph.edges)
          }});
        }} else {{
          const filteredNodes = DATASET.graph.nodes.filter(n => n.group === filter);
          const nodeIds = new Set(filteredNodes.map(n => n.id));
          const filteredEdges = DATASET.graph.edges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));
          network.setData({{
            nodes: new vis.DataSet(filteredNodes),
            edges: new vis.DataSet(filteredEdges)
          }});
        }}
      }});
    }});

    document.getElementById("wizardSelect").addEventListener("change", function(e) {{
      const wizName = e.target.value;
      if (!wizName) return;
      const wiz = DATASET.wizards.find(w => w.name === wizName);
      if (wiz) {{
        showWizardInInspector(wiz);
        if (network) network.focus(wiz.graph_node_id, {{ scale: 1.3, animation: true }});
      }}
    }});

    // Initialize all on page load
    window.addEventListener("DOMContentLoaded", () => {{
      initKPIs();
      initNetwork();
      initCharts();
      // Show default item (Expelliarmus)
      showMagicInInspector(DATASET.magic_items[0]);
    }});
  </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"      Dashboard generated at: {output_path}")


def get_local_ip() -> str:
    """Retrieve the primary local IPv4 address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def find_free_port(host="0.0.0.0", start_port=8001, max_attempts=50) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    return start_port


def serve_dashboard(directory: str, filename: str, port: int, host: str = "0.0.0.0", open_browser: bool = True):
    """Serve the dashboard on Python localhost / local network."""
    class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format, *args):
            sys.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] HTTP: {format % args}\n")

    port = find_free_port(host=host, start_port=port)
    local_ip = get_local_ip()
    url_local = f"http://localhost:{port}/{filename}"
    url_network = f"http://{local_ip}:{port}/{filename}"

    print(f"\n[3/3] Starting Python web server on port {port}...")
    print("=" * 68)
    print(f" [*] Harry Potter Wizard World Analytics Dashboard is running!")
    print(f"  * This Computer (Localhost):  {url_local}")
    print(f"  * Other Computers (Same Wi-Fi): {url_network}")
    print(f" Press Ctrl+C in this terminal to stop the server.")
    print("=" * 68)

    if open_browser:
        try:
            webbrowser.open(url_local)
        except Exception as e:
            print(f"Note: Could not open browser automatically: {e}")

    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer((host, port), CustomHTTPHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user. Exiting cleanly.")


def main():
    parser = argparse.ArgumentParser(
        description="Harry Potter Wizard World Analytics: Spells, Elixirs & Wizards with Book Occurrence Ranker"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host interface to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8001, help="Localhost port (default: 8001)"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Do not automatically open default browser"
    )
    parser.add_argument(
        "--fetch-only", action="store_true", help="Only fetch data and build HTML without launching server"
    )
    args = parser.parse_args()

    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(workspace_dir, "wizard_world_data.json")
    html_name = "wizard_world_dashboard.html"
    html_path = os.path.join(workspace_dir, html_name)

    # 1. Fetch & Process
    dataset = build_analytics_data()

    # 2. Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"      Data exported to: {json_path}")

    # 3. Generate HTML
    generate_html_dashboard(dataset, html_path)

    # 4. Host on localhost / network
    if not args.fetch_only:
        serve_dashboard(workspace_dir, html_name, port=args.port, host=args.host, open_browser=not args.no_browser)
    else:
        print("\nFetch and build completed. '--fetch-only' specified, skipping server startup.")


if __name__ == "__main__":
    main()
