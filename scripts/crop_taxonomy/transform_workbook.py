#!/usr/bin/env python3
"""Transform the Ministry crop workbook into deterministic relational CSV files.

This module deliberately uses only the Python standard library.  An XLSX file is
a ZIP archive of XML documents, and avoiding a spreadsheet runtime keeps the
same command usable in the migration/seed container.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
CATEGORY_CODES = {
    "cropcategory-80402": "cereal",
    "cropcategory-70907": "spices-condiments-medicinal-aromatic",
    "cropcategory-41332": "industrial-crops",
    "cropcategory-70202": "food-legume",
    "cropcategory-56119": "fruit-and-vegetables",
    "cropcategory-86036": "oil-seeds",
    "cropcategory-20413": "stimulant-crops",
    "cropcategory-77910": "roots-and-tubers",
}

REQUIRED_SHEETS = {
    "crop-category",
    "crop-type-crop-catalog",
    "crop-variety--seed-catalog",
}

# These are projections used for common API filters.  The raw values are also
# retained in g2p_crop_variety_characteristic.
CORE_CHARACTERISTICS = {
    "altitude": ("RANGE", "m"),
    "rainfall": ("RANGE", "mm"),
    "rainFall": ("RANGE", "mm"),
    "daysToMaturity": ("RANGE", "day"),
    "yieldResearchField": ("RANGE", "qt/ha"),
    "yieldFarmersField": ("RANGE", "qt/ha"),
    "seedRate": ("RANGE", "kg/ha"),
}

CHARACTERISTIC_CODE_OVERRIDES = {
    "rainFall": "rainfall",
    "1000SeedWeight": "seed_weight_1000",
    "100SeedWeight": "seed_weight_100",
    "1000KernelWeight": "kernel_weight_1000",
}

OUTPUT_FIELDS = {
    "crop_categories.csv": [
        "category_code",
        "source_id",
        "display_name",
        "display_name_amh",
        "image_url",
        "description",
        "status",
    ],
    "crop_types.csv": [
        "type_code",
        "source_id",
        "category_code",
        "display_name",
        "display_name_amh",
        "scientific_name",
        "centre",
        "image_url",
        "description",
        "source_reported_variety_count",
        "status",
    ],
    "crop_varieties.csv": [
        "variety_code",
        "type_code",
        "display_name",
        "display_name_amh",
        "status",
    ],
    "crop_variety_source_records.csv": [
        "source_record_code",
        "variety_code",
        "source_row_number",
        "centre",
        "release_year_raw",
        "release_year",
        "source_url",
        "altitude_min_m",
        "altitude_max_m",
        "rainfall_min_mm",
        "rainfall_max_mm",
        "days_to_maturity_min",
        "days_to_maturity_max",
        "yield_research_min_qt_ha",
        "yield_research_max_qt_ha",
        "yield_farmer_min_qt_ha",
        "yield_farmer_max_qt_ha",
        "seed_rate_kg_ha",
        "adaptation_area",
        "planting_date_text",
        "crop_pest_reaction",
    ],
    "crop_characteristic_definitions.csv": [
        "characteristic_code",
        "source_header",
        "display_name",
        "value_type",
        "default_unit_code",
        "applicable_category_code",
        "description",
    ],
    "crop_variety_characteristics.csv": [
        "source_record_code",
        "characteristic_code",
        "raw_value",
        "value_text",
        "value_numeric",
        "value_boolean",
        "value_min",
        "value_max",
        "unit_code",
    ],
}


class TransformError(RuntimeError):
    """Raised when source data cannot be transformed safely."""


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    rows: list[int] = field(default_factory=list)


@dataclass
class Transformation:
    categories: list[dict]
    crop_types: list[dict]
    varieties: list[dict]
    source_records: list[dict]
    characteristic_definitions: list[dict]
    characteristics: list[dict]
    report: dict

    @property
    def has_errors(self) -> bool:
        return any(item["severity"] == "ERROR" for item in self.report["findings"])


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference.upper())
    if not letters:
        raise TransformError(f"Invalid XLSX cell reference: {reference}")
    result = 0
    for char in letters.group(0):
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1


def read_xlsx(path: Path) -> dict[str, list[dict[str, str]]]:
    """Return sheet rows as dictionaries while preserving spreadsheet row numbers."""
    try:
        archive = ZipFile(path)
    except (FileNotFoundError, BadZipFile) as exc:
        raise TransformError(f"Cannot read XLSX workbook {path}: {exc}") from exc

    with archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = ["".join(node.text or "" for node in item.iter(MAIN_NS + "t")) for item in root]

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        sheets: dict[str, list[dict[str, str]]] = {}
        sheet_nodes = workbook.find(MAIN_NS + "sheets")
        if sheet_nodes is None:
            raise TransformError("XLSX workbook does not contain a sheets element")
        for sheet in sheet_nodes:
            name = sheet.attrib["name"]
            target = targets[sheet.attrib[REL_NS + "id"]]
            part = _resolve_workbook_part(target)
            root = ET.fromstring(archive.read(part))
            parsed_rows: list[tuple[int, dict[int, str]]] = []
            for row in root.findall(".//" + MAIN_NS + "row"):
                values: dict[int, str] = {}
                for cell in row.findall(MAIN_NS + "c"):
                    index = _column_index(cell.attrib["r"])
                    value_node = cell.find(MAIN_NS + "v")
                    value = "" if value_node is None else value_node.text or ""
                    if cell.attrib.get("t") == "s" and value:
                        value = shared_strings[int(value)]
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(node.text or "" for node in cell.iter(MAIN_NS + "t"))
                    values[index] = value.strip()
                parsed_rows.append((int(row.attrib["r"]), values))
            if not parsed_rows:
                sheets[name] = []
                continue
            _, header_cells = parsed_rows[0]
            max_column = max(header_cells, default=-1)
            headers = [header_cells.get(index, "") for index in range(max_column + 1)]
            records = []
            for row_number, cells in parsed_rows[1:]:
                record = {header: cells.get(index, "") for index, header in enumerate(headers) if header}
                if any(record.values()):
                    record["__row_number__"] = str(row_number)
                    records.append(record)
            sheets[name] = records
        return sheets


def _resolve_workbook_part(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    parts: list[str] = []
    for part in PurePosixPath("xl", target).parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def normalize_space(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def normalized_key(value: str) -> str:
    return unicodedata.normalize("NFKC", normalize_space(value)).casefold()


def has_ethiopic(value: str) -> bool:
    return any("\u1200" <= char <= "\u137f" for char in value)


def split_localized_name(value: str) -> tuple[str, str]:
    """Split English/source text from Ethiopic-script text without translating it."""
    value = unicodedata.normalize("NFKC", normalize_space(value))
    amharic_groups = re.findall(r"\([^)]*[\u1200-\u137f][^)]*\)", value)
    english = re.sub(r"\([^)]*[\u1200-\u137f][^)]*\)", " ", value)
    remaining_amharic = "".join(
        char if ("\u1200" <= char <= "\u137f" or char.isspace()) else " " for char in english
    )
    english = "".join(" " if "\u1200" <= char <= "\u137f" else char for char in english)
    group_text = " ".join(re.sub(r"[^\u1200-\u137f\s]", " ", group) for group in amharic_groups)
    amharic = normalize_space(f"{group_text} {remaining_amharic}")
    return normalize_space(english), amharic


def slug(value: str) -> str:
    value, _ = split_localized_name(value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    if not value:
        raise TransformError("Cannot create a code from an empty/non-Latin name")
    return value


def characteristic_code(header: str) -> str:
    if header in CHARACTERISTIC_CODE_OVERRIDES:
        return CHARACTERISTIC_CODE_OVERRIDES[header]
    code = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", header)
    code = re.sub(r"[^A-Za-z0-9]+", "_", code).strip("_").lower()
    if code and code[0].isdigit():
        code = "value_" + code
    if not code:
        raise TransformError(f"Cannot create characteristic code for header {header!r}")
    return code


def display_name_for_header(header: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", header)
    return normalize_space(re.sub(r"[_-]+", " ", spaced)).capitalize()


def parse_decimal_range(raw: str) -> tuple[Decimal | None, Decimal | None]:
    """Parse a conservative single number or numeric range; never guess from prose."""
    value = normalize_space(raw).replace(",", "")
    if not value or value in {"-", "–", "—"}:
        return None, None
    value = re.sub(r"(?i)m\.?\s*a\.?\s*s\.?\s*l\.?", " ", value)
    value = re.sub(
        r"(?i)(?:meters?|metres?|mm|days?|qt\s*/?\s*ha|q\s*/?\s*ha|kg\s*/?\s*ha|kg\s+ha-?1)",
        " ",
        value,
    )
    value = value.strip(" .()")
    match = re.fullmatch(
        r"(?P<operator><=|>=|<|>)?\s*(?P<first>-?\d+(?:\.\d+)?)\s*(?:(?:-|–|—|to)\s*(?P<second>-?\d+(?:\.\d+)?))?",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None
    try:
        first = Decimal(match.group("first"))
        second = Decimal(match.group("second") or match.group("first"))
    except InvalidOperation:
        return None, None
    if first < 0 or second < first:
        return None, None
    operator = match.group("operator")
    if operator in {">", ">="} and not match.group("second"):
        return first, None
    if operator in {"<", "<="} and not match.group("second"):
        return None, first
    return first, second


def parse_release_year(raw: str) -> int | None:
    value = normalize_space(raw)
    if not re.fullmatch(r"\d{4}", value):
        return None
    year = int(value)
    return year if 1800 <= year <= 2200 else None


def decimal_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value.normalize(), "f")


def integer_text(value: Decimal | None) -> str:
    """Return a value only when it fits an integer database projection."""
    if value is None or value != value.to_integral_value():
        return ""
    return str(int(value))


def _record_id(row: dict, variety_code: str) -> str:
    url = row.get("url", "")
    query_id = parse_qs(urlparse(url).query).get("id", [])
    if query_id and re.fullmatch(r"[A-Za-z0-9_-]+", query_id[0]):
        return "moa-variety-" + query_id[0]
    identity = "|".join(
        (
            variety_code,
            normalized_key(row.get("centre", "")),
            normalize_space(row.get("year", "")),
        )
    )
    return "workbook-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def _finding(severity: str, code: str, message: str, rows: Iterable[int] = ()) -> Finding:
    return Finding(severity, code, message, sorted(set(rows))[:25])


def transform_workbook(path: Path) -> Transformation:
    sheets = read_xlsx(path)
    missing_sheets = REQUIRED_SHEETS - sheets.keys()
    if missing_sheets:
        raise TransformError(f"Workbook is missing sheets: {', '.join(sorted(missing_sheets))}")

    category_rows = sheets["crop-category"]
    type_rows = sheets["crop-type-crop-catalog"]
    variety_rows = sheets["crop-variety--seed-catalog"]
    findings: list[Finding] = []

    category_names_by_id: dict[str, str] = {}
    for row in type_rows + variety_rows:
        source_id = normalize_space(row.get("cropCategoryId", ""))
        source_name = normalize_space(row.get("cropCategoryName", ""))
        if source_id and source_name:
            previous = category_names_by_id.setdefault(source_id, source_name)
            if normalized_key(previous) != normalized_key(source_name):
                findings.append(
                    _finding(
                        "ERROR",
                        "CATEGORY_ID_NAME_CONFLICT",
                        f"{source_id} maps to both {previous!r} and {source_name!r}",
                    )
                )

    category_source_by_name = {
        normalized_key(name): source_id for source_id, name in category_names_by_id.items()
    }
    categories = []
    for row in category_rows:
        english, amharic = split_localized_name(row.get("name", ""))
        source_id = category_source_by_name.get(normalized_key(row.get("name", "")), "")
        category_code = CATEGORY_CODES.get(source_id, "")
        if not source_id or not category_code:
            findings.append(_finding("ERROR", "UNKNOWN_CATEGORY", f"Cannot map category {row.get('name')!r}"))
            continue
        categories.append(
            {
                "category_code": category_code,
                "source_id": source_id,
                "display_name": english,
                "display_name_amh": amharic,
                "image_url": row.get("imageUrl", ""),
                "description": row.get("description", ""),
                "status": "ACTIVE",
            }
        )
    categories.sort(key=lambda item: item["category_code"])
    category_code_by_id = {item["source_id"]: item["category_code"] for item in categories}

    type_source_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in variety_rows:
        key = (
            normalize_space(row.get("cropCategoryId", "")),
            normalized_key(row.get("cropTypeName", "")),
        )
        if row.get("cropTypeId"):
            type_source_ids[key].add(normalize_space(row["cropTypeId"]))

    crop_types = []
    type_code_by_key: dict[tuple[str, str], str] = {}
    seen_type_codes: dict[str, tuple[str, str]] = {}
    for row in type_rows:
        category_id = normalize_space(row.get("cropCategoryId", ""))
        type_name = normalize_space(row.get("name", ""))
        key = (category_id, normalized_key(type_name))
        type_code = slug(type_name)
        if type_code in seen_type_codes and seen_type_codes[type_code] != key:
            findings.append(
                _finding(
                    "ERROR", "TYPE_CODE_COLLISION", f"Type code {type_code!r} is shared by multiple types"
                )
            )
            type_code = f"{category_code_by_id.get(category_id, 'unknown')}-{type_code}"
        seen_type_codes[type_code] = key
        type_code_by_key[key] = type_code
        source_ids = sorted(type_source_ids.get(key, set()))
        if len(source_ids) > 1:
            findings.append(
                _finding(
                    "ERROR", "TYPE_SOURCE_ID_CONFLICT", f"{type_name!r} has multiple source IDs: {source_ids}"
                )
            )
        if not source_ids:
            rows = [
                int(item["__row_number__"])
                for item in variety_rows
                if (
                    normalize_space(item.get("cropCategoryId", "")),
                    normalized_key(item.get("cropTypeName", "")),
                )
                == key
            ]
            findings.append(
                _finding(
                    "WARNING",
                    "MISSING_TYPE_SOURCE_ID",
                    f"{type_name!r} has no source cropTypeId; relationship resolved by category and name",
                    rows,
                )
            )
        english, amharic = split_localized_name(type_name)
        count_raw = normalize_space(row.get("varietiesCount", ""))
        crop_types.append(
            {
                "type_code": type_code,
                "source_id": source_ids[0] if source_ids else "",
                "category_code": category_code_by_id.get(category_id, ""),
                "display_name": english,
                "display_name_amh": amharic,
                "scientific_name": row.get("scientificName", ""),
                "centre": row.get("centre", ""),
                "image_url": row.get("imageUrl", ""),
                "description": row.get("description", ""),
                "source_reported_variety_count": count_raw,
                "status": "ACTIVE",
            }
        )
    crop_types.sort(key=lambda item: item["type_code"])

    attribute_headers = (
        [
            header
            for header in variety_rows[0]
            if header
            not in {
                "__row_number__",
                "cropCategoryName",
                "cropCategoryId",
                "cropTypeName",
                "cropTypeId",
                "cropTypeVariety",
                "centre",
                "year",
                "url",
            }
        ]
        if variety_rows
        else []
    )
    code_headers: dict[str, list[str]] = defaultdict(list)
    for header in attribute_headers:
        code_headers[characteristic_code(header)].append(header)
    for code, headers in code_headers.items():
        if len(headers) > 1 and set(headers) != {"rainfall", "rainFall"}:
            findings.append(_finding("ERROR", "CHARACTERISTIC_CODE_COLLISION", f"{headers} map to {code!r}"))

    occurrence_categories: dict[str, set[str]] = defaultdict(set)
    for row in variety_rows:
        category_code = category_code_by_id.get(normalize_space(row.get("cropCategoryId", "")), "")
        for header in attribute_headers:
            if normalize_space(row.get(header, "")):
                occurrence_categories[characteristic_code(header)].add(category_code)

    definitions = []
    for code, headers in sorted(code_headers.items()):
        core = next((CORE_CHARACTERISTICS[h] for h in headers if h in CORE_CHARACTERISTICS), None)
        categories_for_value = occurrence_categories[code] - {""}
        definitions.append(
            {
                "characteristic_code": code,
                "source_header": "|".join(sorted(headers)),
                "display_name": display_name_for_header(headers[0]),
                "value_type": core[0] if core else "TEXT",
                "default_unit_code": core[1] if core else "",
                "applicable_category_code": next(iter(categories_for_value))
                if len(categories_for_value) == 1
                else "",
                "description": "Raw workbook attribute; typed common fields are also projected onto the source record."
                if core
                else "Raw workbook attribute.",
            }
        )

    varieties_by_key: dict[tuple[str, str], dict] = {}
    variety_rows_by_key: dict[tuple[str, str], list[int]] = defaultdict(list)
    variety_key_by_code: dict[str, tuple[str, str]] = {}
    source_records = []
    characteristics = []
    source_record_codes: set[str] = set()
    parse_stats = Counter()
    invalid_year_rows: list[int] = []
    fractional_maturity_rows: list[int] = []
    unresolved_type_rows: list[int] = []
    for row in variety_rows:
        row_number = int(row["__row_number__"])
        type_key = (
            normalize_space(row.get("cropCategoryId", "")),
            normalized_key(row.get("cropTypeName", "")),
        )
        type_code = type_code_by_key.get(type_key)
        if not type_code:
            unresolved_type_rows.append(row_number)
            continue
        variety_name = normalize_space(row.get("cropTypeVariety", ""))
        variety_key = (type_code, normalized_key(variety_name))
        variety_rows_by_key[variety_key].append(row_number)
        if variety_key not in varieties_by_key:
            english, amharic = split_localized_name(variety_name)
            variety_code = f"{type_code}-{slug(variety_name)}"
            if variety_code in variety_key_by_code and variety_key_by_code[variety_code] != variety_key:
                findings.append(
                    _finding(
                        "ERROR",
                        "VARIETY_CODE_COLLISION",
                        f"Distinct variety names map to {variety_code!r}",
                        [row_number],
                    )
                )
                variety_code += "-" + hashlib.sha256(variety_name.encode("utf-8")).hexdigest()[:8]
            variety_key_by_code[variety_code] = variety_key
            varieties_by_key[variety_key] = {
                "variety_code": variety_code,
                "type_code": type_code,
                "display_name": english,
                "display_name_amh": amharic,
                "status": "ACTIVE",
            }
        variety = varieties_by_key[variety_key]
        source_record_code = _record_id(row, variety["variety_code"])
        if source_record_code in source_record_codes:
            findings.append(
                _finding(
                    "ERROR",
                    "SOURCE_RECORD_CODE_COLLISION",
                    f"Duplicate source record code {source_record_code}",
                    [row_number],
                )
            )
            source_record_code += "-row-" + str(row_number)
        source_record_codes.add(source_record_code)

        parsed: dict[str, tuple[Decimal | None, Decimal | None]] = {}
        for header in CORE_CHARACTERISTICS:
            raw = row.get(header, "")
            if raw:
                parsed[header] = parse_decimal_range(raw)
                parse_stats[f"{header}.present"] += 1
                successfully_parsed = any(value is not None for value in parsed[header])
                parse_stats[f"{header}.parsed" if successfully_parsed else f"{header}.unparsed"] += 1
        year = parse_release_year(row.get("year", ""))
        if row.get("year") and year is None:
            invalid_year_rows.append(row_number)
        seed_min, seed_max = parsed.get("seedRate", (None, None))
        seed_rate = seed_min if seed_min is not None and seed_min == seed_max else None
        maturity_min, maturity_max = parsed.get("daysToMaturity", (None, None))
        if any(
            value is not None and value != value.to_integral_value() for value in (maturity_min, maturity_max)
        ):
            fractional_maturity_rows.append(row_number)
        source_records.append(
            {
                "source_record_code": source_record_code,
                "variety_code": variety["variety_code"],
                "source_row_number": row_number,
                "centre": row.get("centre", ""),
                "release_year_raw": row.get("year", ""),
                "release_year": year or "",
                "source_url": row.get("url", ""),
                "altitude_min_m": decimal_text(parsed.get("altitude", (None, None))[0]),
                "altitude_max_m": decimal_text(parsed.get("altitude", (None, None))[1]),
                "rainfall_min_mm": decimal_text(
                    parsed.get("rainfall", parsed.get("rainFall", (None, None)))[0]
                ),
                "rainfall_max_mm": decimal_text(
                    parsed.get("rainfall", parsed.get("rainFall", (None, None)))[1]
                ),
                "days_to_maturity_min": integer_text(maturity_min),
                "days_to_maturity_max": integer_text(maturity_max),
                "yield_research_min_qt_ha": decimal_text(parsed.get("yieldResearchField", (None, None))[0]),
                "yield_research_max_qt_ha": decimal_text(parsed.get("yieldResearchField", (None, None))[1]),
                "yield_farmer_min_qt_ha": decimal_text(parsed.get("yieldFarmersField", (None, None))[0]),
                "yield_farmer_max_qt_ha": decimal_text(parsed.get("yieldFarmersField", (None, None))[1]),
                "seed_rate_kg_ha": decimal_text(seed_rate),
                "adaptation_area": row.get("adaptationArea", ""),
                "planting_date_text": row.get("plantingDate", ""),
                "crop_pest_reaction": row.get("cropPestReaction", ""),
            }
        )
        values_by_code: dict[str, tuple[str, str]] = {}
        for header in attribute_headers:
            raw = normalize_space(row.get(header, ""))
            if not raw:
                continue
            code = characteristic_code(header)
            if code in values_by_code and values_by_code[code][1] != raw:
                findings.append(
                    _finding(
                        "ERROR",
                        "CHARACTERISTIC_VALUE_CONFLICT",
                        f"Row {row_number} supplies conflicting {values_by_code[code][0]} and {header} values for {code}",
                        [row_number],
                    )
                )
                continue
            values_by_code[code] = (header, raw)
        for code, (header, raw) in sorted(values_by_code.items()):
            value_min, value_max = parsed.get(header, (None, None))
            core = CORE_CHARACTERISTICS.get(header)
            characteristics.append(
                {
                    "source_record_code": source_record_code,
                    "characteristic_code": code,
                    "raw_value": raw,
                    "value_text": "" if core else raw,
                    "value_numeric": "",
                    "value_boolean": "",
                    "value_min": decimal_text(value_min),
                    "value_max": decimal_text(value_max),
                    "unit_code": core[1] if core else "",
                }
            )

    if unresolved_type_rows:
        findings.append(
            _finding(
                "ERROR",
                "UNRESOLVED_VARIETY_TYPE",
                "Variety rows could not be joined to a crop type",
                unresolved_type_rows,
            )
        )
    if invalid_year_rows:
        findings.append(
            _finding(
                "WARNING",
                "INVALID_RELEASE_YEAR",
                f"{len(invalid_year_rows)} release years were retained as raw text but not normalized",
                invalid_year_rows,
            )
        )
    if fractional_maturity_rows:
        findings.append(
            _finding(
                "WARNING",
                "FRACTIONAL_MATURITY_NOT_PROJECTED",
                f"{len(fractional_maturity_rows)} fractional maturity values remain in characteristics but were not copied to integer filter columns",
                fractional_maturity_rows,
            )
        )

    for key, rows in variety_rows_by_key.items():
        if len(rows) > 1:
            variety = varieties_by_key[key]
            findings.append(
                _finding(
                    "WARNING",
                    "MULTIPLE_VARIETY_SOURCE_RECORDS",
                    f"{variety['display_name']!r} is one variety concept with {len(rows)} source records",
                    rows,
                )
            )

    # Count distinct concepts by their explicit type_code (not by parsing their code).
    actual_counts = Counter(item["type_code"] for item in varieties_by_key.values())
    for crop_type in crop_types:
        raw = crop_type["source_reported_variety_count"]
        if raw.isdigit() and int(raw) != actual_counts[crop_type["type_code"]]:
            findings.append(
                _finding(
                    "WARNING",
                    "VARIETY_COUNT_MISMATCH",
                    f"{crop_type['display_name']}: workbook reports {raw}, but {actual_counts[crop_type['type_code']]} distinct varieties are present",
                )
            )

    insecure_urls = sum(
        1
        for item in categories + crop_types + source_records
        if item.get("image_url", item.get("source_url", "")).startswith("http://")
    )
    if insecure_urls:
        findings.append(
            _finding(
                "WARNING",
                "INSECURE_SOURCE_URL",
                f"{insecure_urls} source URLs use HTTP; values were preserved without rewriting",
            )
        )

    varieties = sorted(varieties_by_key.values(), key=lambda item: item["variety_code"])
    source_records.sort(key=lambda item: (int(item["source_row_number"]), item["source_record_code"]))
    characteristics.sort(key=lambda item: (item["source_record_code"], item["characteristic_code"]))
    finding_dicts = [
        finding.__dict__
        for finding in sorted(findings, key=lambda item: (item.severity, item.code, item.message))
    ]
    report = {
        "format_version": 1,
        "source_file": path.name,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "counts": {
            "source_categories": len(category_rows),
            "source_crop_types": len(type_rows),
            "source_variety_records": len(variety_rows),
            "categories": len(categories),
            "crop_types": len(crop_types),
            "varieties": len(varieties),
            "source_records": len(source_records),
            "characteristic_definitions": len(definitions),
            "characteristic_values": len(characteristics),
            "errors": sum(item["severity"] == "ERROR" for item in finding_dicts),
            "warnings": sum(item["severity"] == "WARNING" for item in finding_dicts),
        },
        "range_parse_statistics": dict(sorted(parse_stats.items())),
        "findings": finding_dicts,
    }
    return Transformation(
        categories, crop_types, varieties, source_records, definitions, characteristics, report
    )


def write_outputs(result: Transformation, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets = {
        "crop_categories.csv": result.categories,
        "crop_types.csv": result.crop_types,
        "crop_varieties.csv": result.varieties,
        "crop_variety_source_records.csv": result.source_records,
        "crop_characteristic_definitions.csv": result.characteristic_definitions,
        "crop_variety_characteristics.csv": result.characteristics,
    }
    for filename, rows in datasets.items():
        with (output_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS[filename], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    (output_dir / "validation_report.json").write_text(
        json.dumps(result.report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, help="Path to the source .xlsx workbook")
    parser.add_argument("--output-dir", type=Path, help="Write normalized CSVs and validation_report.json")
    parser.add_argument(
        "--strict", action="store_true", help="Also return a failure exit code when warnings exist"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = transform_workbook(args.workbook)
        if args.output_dir:
            write_outputs(result, args.output_dir)
        print(json.dumps(result.report, ensure_ascii=False, indent=2, sort_keys=True))
    except TransformError as exc:
        print(f"crop taxonomy transformation failed: {exc}", file=sys.stderr)
        return 2
    if result.has_errors:
        return 1
    if args.strict and result.report["counts"]["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
