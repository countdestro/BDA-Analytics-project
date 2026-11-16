import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

FILE = (
    BASE_DIR
    / "dataset"
    / "raw"
    / "xbrl"
    / "BDL"
    / "BDL_2022-09-30_Non-Consolidated_Non-cumulative_2cb9ec5e.xml"
)

tree = ET.parse(FILE)
root = tree.getroot()

ns = {
    "xbrli": "http://www.xbrl.org/2003/instance"
}

for context in root.findall("xbrli:context", ns):

    context_id = context.attrib.get("id")

    if context_id in ["OneD", "FourD"]:

        print(f"\nContext ID: {context_id}")

        period = context.find("xbrli:period", ns)

        for element in period:
            print(element.tag.split("}")[-1], element.text)