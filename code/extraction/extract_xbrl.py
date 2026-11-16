
import sys
import csv
import json
import re
import logging
import xml.etree.ElementTree as ET

from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import datetime, date


# --------------------------------------------------
# 1. PROJECT PATHS AND CONFIGURATION
# --------------------------------------------------

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from config import XBRL_DIR, PROCESSED_DIR


FACTS_OUTPUT = PROCESSED_DIR / "raw_financial_facts_v3.csv"
CONTEXT_OUTPUT = PROCESSED_DIR / "xbrl_context_audit.csv"
ERROR_OUTPUT = PROCESSED_DIR / "xbrl_extraction_errors.csv"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

XBRLI_NS = "http://www.xbrl.org/2003/instance"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

NS = {
    "xbrli": XBRLI_NS
}


# --------------------------------------------------
# 2. HELPER FUNCTIONS
# --------------------------------------------------

def get_local_name(tag):
    """Extract the local concept name from an XML QName."""

    if "}" in tag:
        return tag.split("}", 1)[1]

    return tag


def get_namespace(tag):
    """Extract the namespace from an XML QName."""

    if tag.startswith("{"):
        return tag[1:].split("}", 1)[0]

    return ""


def parse_decimal(value):
    """Convert numeric text to Decimal without losing precision."""

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    try:
        return Decimal(value)

    except InvalidOperation:
        return None


def get_text(element):
    """Safely retrieve XML element text."""

    if element is None or element.text is None:
        return None

    return element.text.strip()


def parse_filename_metadata(filename):
    """Extract filing information from the XML filename."""

    name = filename.lower()

    metadata = {
        "reporting_date": None,
        "reporting_basis": "Unknown",
        "filing_type": "Unknown"
    }

    date_match = re.search(
        r"_(\d{4}-\d{2}-\d{2})_",
        filename
    )

    if date_match:
        metadata["reporting_date"] = date_match.group(1)

    # IMPORTANT: Check non-consolidated first.

    if "non-consolidated" in name:
        metadata["reporting_basis"] = "Standalone"

    elif "consolidated" in name:
        metadata["reporting_basis"] = "Consolidated"

    # Check non-cumulative before cumulative.

    if "non-cumulative" in name:
        metadata["filing_type"] = "Non-cumulative"

    elif "cumulative" in name:
        metadata["filing_type"] = "Cumulative"

    return metadata


# --------------------------------------------------
# 3. EXTRACT XBRL CONTEXTS
# --------------------------------------------------

def extract_contexts(root):
    """Extract context information from an XBRL document."""

    contexts = {}

    for context in root.findall("xbrli:context", NS):

        context_id = context.attrib.get("id")

        if not context_id:
            continue

        entity = context.find("xbrli:entity", NS)

        identifier = None
        scheme = None

        if entity is not None:

            identifier_element = entity.find(
                "xbrli:identifier",
                NS
            )

            if identifier_element is not None:

                identifier = get_text(identifier_element)

                scheme = identifier_element.attrib.get(
                    "scheme"
                )

        period = context.find("xbrli:period", NS)

        context_start = None
        context_end = None
        context_instant = None

        if period is not None:

            context_start = get_text(
                period.find("xbrli:startDate", NS)
            )

            context_end = get_text(
                period.find("xbrli:endDate", NS)
            )

            context_instant = get_text(
                period.find("xbrli:instant", NS)
            )

        dimensions = []

        for member in context.iter():

            local_name = get_local_name(member.tag)

            if local_name == "explicitMember":

                dimensions.append({
                    "type": "explicit",
                    "dimension": member.attrib.get("dimension"),
                    "member": get_text(member)
                })

            elif local_name == "typedMember":

                typed_value = "".join(
                    member.itertext()
                ).strip()

                dimensions.append({
                    "type": "typed",
                    "dimension": member.attrib.get("dimension"),
                    "member": typed_value
                })

        contexts[context_id] = {
            "context_id": context_id,
            "entity_identifier": identifier,
            "entity_scheme": scheme,
            "context_start_date": context_start,
            "context_end_date": context_end,
            "context_instant_date": context_instant,
            "dimensions": dimensions
        }

    return contexts


# --------------------------------------------------
# 4. EXTRACT XBRL UNITS
# --------------------------------------------------

def extract_units(root):
    """Extract unit definitions."""

    units = {}

    for unit in root.findall("xbrli:unit", NS):

        unit_id = unit.attrib.get("id")

        if not unit_id:
            continue

        measures = []

        for measure in unit.findall(".//xbrli:measure", NS):

            if measure.text:
                measures.append(measure.text.strip())

        units[unit_id] = " * ".join(measures)

    return units


# --------------------------------------------------
# 5. EXTRACT FINANCIAL PERIOD METADATA
# --------------------------------------------------

METADATA_CONCEPTS = {
    "DateOfStartOfReportingPeriod",
    "DateOfEndOfReportingPeriod",
    "ReportingQuarter",
    "NatureOfReportingStandaloneConsolidated",
    "ResultType",
    "LevelOfRoundingUsedInFinancialStatements"
}


def extract_context_metadata(root):
    """
    Associate reporting metadata facts with their context IDs.

    This is important because the reporting-period metadata
    may differ from the dates in the XBRL context itself.
    """

    metadata = {}

    for element in root.iter():

        context_id = element.attrib.get("contextRef")

        if not context_id:
            continue

        concept = get_local_name(element.tag)

        if concept not in METADATA_CONCEPTS:
            continue

        value = get_text(element)

        if value is None:
            continue

        metadata.setdefault(context_id, {})

        metadata[context_id].setdefault(
            concept,
            []
        )

        metadata[context_id][concept].append(value)

    return metadata


def choose_metadata_value(values):
    """
    Return a unique metadata value.

    Conflicting values are retained as JSON rather than
    silently selecting one.
    """

    if not values:
        return None, False

    unique_values = list(dict.fromkeys(values))

    if len(unique_values) == 1:
        return unique_values[0], False

    return json.dumps(unique_values), True


# --------------------------------------------------
# 6. CLASSIFY REPORTING PERIODS
# --------------------------------------------------

def classify_period(start_date, end_date, instant_date=None):
    """
    Classify the reporting duration using metadata dates.

    Classification is based on the number of calendar
    months covered, not context IDs such as OneD/FourD.
    """

    if instant_date:
        return "Instant"

    if not start_date or not end_date:
        return "Unknown"

    try:

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        if end < start:
            return "Invalid"

        months = (
            (end.year - start.year) * 12
            + end.month - start.month
            + 1
        )

        if months == 3:
            return "Quarterly"

        elif months == 6:
            return "Half-year cumulative"

        elif months == 9:
            return "Nine-month cumulative"

        elif months == 12:
            return "Annual"

        else:
            return "Other duration"

    except ValueError:
        return "Unknown"


# --------------------------------------------------
# 7. EXTRACT ALL FINANCIAL FACTS
# --------------------------------------------------

def extract_facts(root, contexts, units, context_metadata,
                  filename_metadata, source_file):

    facts = []
    context_audit = []

    # First prepare context-level metadata.

    for context_id, context in contexts.items():

        metadata = context_metadata.get(
            context_id,
            {}
        )

        start_value, start_conflict = choose_metadata_value(
            metadata.get("DateOfStartOfReportingPeriod", [])
        )

        end_value, end_conflict = choose_metadata_value(
            metadata.get("DateOfEndOfReportingPeriod", [])
        )

        quarter_value, quarter_conflict = choose_metadata_value(
            metadata.get("ReportingQuarter", [])
        )

        nature_value, nature_conflict = choose_metadata_value(
            metadata.get("NatureOfReportingStandaloneConsolidated", [])
        )

        result_type, result_conflict = choose_metadata_value(
            metadata.get("ResultType", [])
        )

        rounding_value, rounding_conflict = choose_metadata_value(
            metadata.get("LevelOfRoundingUsedInFinancialStatements", [])
        )

        # Prefer reporting-period metadata dates.
        # Fall back to the actual XBRL context dates.

        if start_value and not start_conflict:
            reporting_start = start_value
            period_date_source = "Reporting metadata"

        else:
            reporting_start = context["context_start_date"]
            period_date_source = "XBRL context fallback"

        if end_value and not end_conflict:
            reporting_end = end_value

        else:
            reporting_end = context["context_end_date"]

        if not reporting_start and not reporting_end:
            period_date_source = "Unavailable"

        instant_date = context["context_instant_date"]

        period_type = classify_period(
            reporting_start,
            reporting_end,
            instant_date
        )

        context_audit.append({

            "symbol": source_file.parent.name,

            "source_file": source_file.name,

            "context_id": context_id,

            "entity_identifier": context["entity_identifier"],

            "context_start_date": context["context_start_date"],

            "context_end_date": context["context_end_date"],

            "context_instant_date": instant_date,

            "reporting_start_date": reporting_start,

            "reporting_end_date": reporting_end,

            "period_date_source": period_date_source,

            "period_type": period_type,

            "reporting_quarter": quarter_value,

            "reporting_nature": nature_value,

            "result_type": result_type,

            "rounding_level": rounding_value,

            "metadata_conflict": any([
                start_conflict,
                end_conflict,
                quarter_conflict,
                nature_conflict,
                result_conflict,
                rounding_conflict
            ]),

            "dimensions": json.dumps(
                context["dimensions"],
                ensure_ascii=False
            )

        })

    # Build quick context lookup.

    context_lookup = {
        row["context_id"]: row
        for row in context_audit
    }

    # Extract every element associated with a context.

    for element in root.iter():

        context_id = element.attrib.get("contextRef")

        if not context_id:
            continue

        concept_qname = element.tag

        concept = get_local_name(concept_qname)

        namespace = get_namespace(concept_qname)

        context = contexts.get(context_id, {})

        audit = context_lookup.get(context_id, {})

        unit_ref = element.attrib.get("unitRef")

        raw_value = get_text(element)

        numeric_value = parse_decimal(raw_value)

        is_nil = (
            element.attrib.get(f"{{{XSI_NS}}}nil", "false").lower()
            in {"true", "1"}
        )

        fact = {

            "symbol": source_file.parent.name,

            "source_file": source_file.name,

            "reporting_date": filename_metadata["reporting_date"],

            "reporting_basis": filename_metadata["reporting_basis"],

            "filing_type": filename_metadata["filing_type"],

            "concept": concept,

            "concept_qname": concept_qname,

            "concept_namespace": namespace,

            "value": raw_value,

            "numeric_value": (
                str(numeric_value)
                if numeric_value is not None
                else None
            ),

            "is_numeric": numeric_value is not None,

            "context_ref": context_id,

            "context_id": context_id,

            "entity_identifier": context.get("entity_identifier"),

            "entity_scheme": context.get("entity_scheme"),

            "context_start_date": context.get("context_start_date"),

            "context_end_date": context.get("context_end_date"),

            "context_instant_date": context.get("context_instant_date"),

            "reporting_start_date": audit.get("reporting_start_date"),

            "reporting_end_date": audit.get("reporting_end_date"),

            "period_date_source": audit.get("period_date_source"),

            "period_type": audit.get("period_type"),

            "reporting_quarter": audit.get("reporting_quarter"),

            "unit_ref": unit_ref,

            "unit": units.get(unit_ref),

            "dimensions": json.dumps(
                context.get("dimensions", []),
                ensure_ascii=False
            ),

            "decimals": element.attrib.get("decimals"),

            "precision": element.attrib.get("precision"),

            "scale": element.attrib.get("scale"),

            "sign": element.attrib.get("sign"),

            "is_nil": is_nil,

            "element_id": element.attrib.get("id")

        }

        facts.append(fact)

    return facts, context_audit


# --------------------------------------------------
# 8. PROCESS ONE XBRL FILE
# --------------------------------------------------

def process_xbrl_file(file_path):

    logger.info("Processing %s", file_path.name)

    tree = ET.parse(file_path)

    root = tree.getroot()

    filename_metadata = parse_filename_metadata(
        file_path.name
    )

    contexts = extract_contexts(root)

    units = extract_units(root)

    context_metadata = extract_context_metadata(root)

    facts, context_audit = extract_facts(
        root,
        contexts,
        units,
        context_metadata,
        filename_metadata,
        file_path
    )

    return facts, context_audit


# --------------------------------------------------
# 9. MAIN EXTRACTION PIPELINE
# --------------------------------------------------

def main():

    logger.info("Starting automated XBRL extraction")

    xbrl_files = list(
        XBRL_DIR.rglob("*.xml")
    )

    logger.info(
        "Total XML files discovered: %s",
        len(xbrl_files)
    )

    all_facts = []

    all_contexts = []

    errors = []

    successful_files = 0

    for index, file_path in enumerate(xbrl_files, start=1):

        try:

            facts, contexts = process_xbrl_file(
                file_path
            )

            all_facts.extend(facts)

            all_contexts.extend(contexts)

            successful_files += 1

            logger.info(
                "[%s/%s] Successfully extracted %s facts",
                index,
                len(xbrl_files),
                len(facts)
            )

        except Exception as error:

            logger.exception(
                "Failed to process %s",
                file_path.name
            )

            errors.append({

                "source_file": file_path.name,

                "file_path": str(file_path),

                "error": str(error)

            })

    # --------------------------------------------------
    # 10. SAVE FINANCIAL FACTS
    # --------------------------------------------------

    if all_facts:

        with open(
            FACTS_OUTPUT,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=list(all_facts[0].keys())
            )

            writer.writeheader()

            writer.writerows(all_facts)

    # --------------------------------------------------
    # 11. SAVE CONTEXT AUDIT
    # --------------------------------------------------

    if all_contexts:

        with open(
            CONTEXT_OUTPUT,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=list(all_contexts[0].keys())
            )

            writer.writeheader()

            writer.writerows(all_contexts)

    # --------------------------------------------------
    # 12. SAVE ERRORS
    # --------------------------------------------------

    if errors:

        with open(
            ERROR_OUTPUT,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "source_file",
                    "file_path",
                    "error"
                ]
            )

            writer.writeheader()

            writer.writerows(errors)

    # --------------------------------------------------
    # 13. FINAL SUMMARY
    # --------------------------------------------------

    logger.info("=" * 55)

    logger.info("XBRL EXTRACTION COMPLETED")

    logger.info("Total XML files: %s", len(xbrl_files))

    logger.info("Successful files: %s", successful_files)

    logger.info("Failed files: %s", len(errors))

    logger.info("Total extracted facts: %s", len(all_facts))

    logger.info("Total extracted contexts: %s", len(all_contexts))

    logger.info("Facts output: %s", FACTS_OUTPUT)

    logger.info("Context audit: %s", CONTEXT_OUTPUT)

    if errors:
        logger.warning("Error report: %s", ERROR_OUTPUT)

    logger.info("=" * 55)


# --------------------------------------------------
# 14. EXECUTION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    main()
