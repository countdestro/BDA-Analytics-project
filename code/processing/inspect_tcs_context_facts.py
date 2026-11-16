import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

XBRL_DIR = BASE_DIR / "dataset" / "raw" / "xbrl" / "TCS"

FILE = list(
    XBRL_DIR.glob("TCS_2024-12-31_Consolidated*.xml")
)[0]

tree = ET.parse(FILE)
root = tree.getroot()

for element in root.iter():

    context_id = element.attrib.get("contextRef")

    if context_id in ["OneD", "FourD"]:

        concept = element.tag.split("}")[-1]

        if concept in [
            "RevenueFromOperations",
            "OtherIncome",
            "Expenses",
            "ProfitBeforeTax",
            "ProfitLossForPeriod"
        ]:

            print(
                f"Concept: {concept:<25} "
                f"Context: {context_id:<8} "
                f"Value: {element.text}"
            )