import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

XBRL_DIR = BASE_DIR / "dataset" / "raw" / "xbrl" / "TCS"

files = list(
    XBRL_DIR.glob("TCS_2024-12-31_Consolidated*.xml")
)

if not files:
    raise FileNotFoundError("TCS filing not found")

root = ET.parse(files[0]).getroot()

target_concepts = {
    "ReportingQuarter",
    "DateOfStartOfReportingPeriod",
    "DateOfEndOfReportingPeriod",
    "NatureOfReportingStandaloneConsolidated",
    "ResultType",
    "LevelOfRoundingUsedInFinancialStatements"
}

for element in root.iter():

    concept = element.tag.split("}")[-1]

    if concept in target_concepts:
        print(
            f"{concept:<55} "
            f"Context: {element.attrib.get('contextRef')} "
            f"Value: {element.text}"
        )