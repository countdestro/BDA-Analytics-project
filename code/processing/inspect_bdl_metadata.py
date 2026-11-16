import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
XBRL_DIR = BASE_DIR / "dataset" / "raw" / "xbrl" / "BDL"

files = list(XBRL_DIR.glob("BDL_2022-09-30*.xml"))

if not files:
    raise FileNotFoundError("BDL September 2022 XML not found")

root = ET.parse(files[0]).getroot()

target_concepts = {
    "ReportingQuarter",
    "DateOfStartOfReportingPeriod",
    "DateOfEndOfReportingPeriod"
}

for element in root.iter():

    concept = element.tag.split("}")[-1]

    if concept in target_concepts:
        print(
            f"{concept:<40} "
            f"Context: {element.attrib.get('contextRef')} "
            f"Value: {element.text}"
        )