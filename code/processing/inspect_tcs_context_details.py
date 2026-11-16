import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
XBRL_DIR = BASE_DIR / "dataset" / "raw" / "xbrl"

FILES = [
    XBRL_DIR / "TCS" / "TCS_2024-12-31_Consolidated_Non-cumulative_8f938747.xml",
    XBRL_DIR / "TCS" / "TCS_2024-12-31_Non-Consolidated_Non-cumulative_1dcb4872.xml",
]


def local_name(tag):
    return tag.split("}")[-1]


for xml_file in FILES:

    print("\n" + "=" * 100)
    print("FILE:", xml_file.name)
    print("=" * 100)

    if not xml_file.exists():
        print("File not found:", xml_file)
        continue

    root = ET.parse(xml_file).getroot()

    # Inspect the two contexts
    for element in root.iter():

        if (
            local_name(element.tag) == "context"
            and element.attrib.get("id") in ["OneD", "FourD"]
        ):
            print(f"\nCONTEXT: {element.attrib.get('id')}")
            print(
                ET.tostring(element, encoding="unicode")
            )

    # Inspect revenue facts
    for element in root.iter():

        if local_name(element.tag) == "RevenueFromOperations":

            print("\nREVENUE FACT")
            print("QName:", element.tag)
            print("Value:", element.text)
            print("Attributes:", element.attrib)