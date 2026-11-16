import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

XBRL_DIR = BASE_DIR / "dataset" / "raw" / "xbrl" / "TCS"

files = list(XBRL_DIR.glob("TCS_2024-12-31_Consolidated*.xml"))

if not files:
    raise FileNotFoundError("TCS December 2024 consolidated XML not found")

FILE = files[0]

print("Inspecting:", FILE.name)

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