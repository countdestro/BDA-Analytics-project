
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from config import RAW_DIR

MANIFEST_FILE = RAW_DIR / "xbrl_download_manifest.csv"


def get_local_name(tag):
    return tag.split("}")[-1]


def inspect_facts():

    import pandas as pd

    manifest = pd.read_csv(MANIFEST_FILE)

    sample = manifest[
        (manifest["symbol"] == "HDFCBANK") &
        (manifest["download_status"].astype(str).str.upper() == "SUCCESS")
    ].iloc[0]

    xml_path = Path(sample["local_path"])

    tree = ET.parse(xml_path)
    root = tree.getroot()

    print("\nFILE:", xml_path.name)
    print("\nFINANCIAL FACTS:\n")

    count = 0

    for element in root.iter():

        if element.attrib.get("contextRef"):

            name = get_local_name(element.tag)
            value = element.text.strip() if element.text else ""

            context = element.attrib.get("contextRef")
            unit = element.attrib.get("unitRef", "N/A")

            print(
                f"Concept: {name} | "
                f"Value: {value} | "
                f"Context: {context} | "
                f"Unit: {unit}"
            )

            count += 1

            if count >= 50:
                break


if __name__ == "__main__":
    inspect_facts()
