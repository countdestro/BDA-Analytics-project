
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from config import RAW_DIR

MANIFEST_FILE = RAW_DIR / "xbrl_download_manifest.csv"


def get_local_name(tag):
    return tag.split("}")[-1]


def inspect_contexts():

    manifest = pd.read_csv(MANIFEST_FILE)

    sample = manifest[
        (manifest["symbol"] == "HDFCBANK") &
        (manifest["download_status"].astype(str).str.upper() == "SUCCESS")
    ].iloc[0]

    xml_path = Path(sample["local_path"])

    root = ET.parse(xml_path).getroot()

    print("\nSCENARIO DETAILS:", xml_path.name)

    for context in root:

        if get_local_name(context.tag).lower() != "context":
            continue

        scenario = next(
            (
                child for child in context
                if get_local_name(child.tag).lower() == "scenario"
            ),
            None
        )

        if scenario is None:
            continue

        print(f"\nContext ID: {context.attrib.get('id')}")

        for dimension in scenario.iter():

            if dimension is scenario:
                continue

            print(
                "Dimension:",
                get_local_name(dimension.tag),
                "| Value:",
                dimension.text
            )


if __name__ == "__main__":
    inspect_contexts()
