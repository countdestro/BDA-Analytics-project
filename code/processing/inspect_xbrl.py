
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd

# Make the code folder available for imports
CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from config import RAW_DIR, PROCESSED_DIR
from logger import get_logger

logger = get_logger(__name__)

MANIFEST_FILE = RAW_DIR / "xbrl_download_manifest.csv"
REPORT_FILE = PROCESSED_DIR / "xbrl_structure_report.csv"


def get_local_name(tag):
    """Remove the XML namespace from a tag."""
    return tag.split("}")[-1]


def inspect_xbrl():

    manifest = pd.read_csv(MANIFEST_FILE)

    # Inspect successfully downloaded files only
    successful = manifest[
        manifest["download_status"].astype(str).str.upper() == "SUCCESS"
    ].copy()

    logger.info("Successful XML downloads in manifest: %d", len(successful))

    # Select one XML file per company
    samples = successful.drop_duplicates(subset=["symbol"])

    report = []

    for _, record in samples.iterrows():

        symbol = record["symbol"]
        xml_path = Path(record["local_path"])

        if not xml_path.exists():
            logger.warning("File not found for %s: %s", symbol, xml_path)
            continue

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Identify XML namespace
            namespace = ""
            if root.tag.startswith("{"):
                namespace = root.tag.split("}")[0][1:]

            contexts = [
                element for element in root.iter()
                if get_local_name(element.tag).lower() == "context"
            ]

            units = [
                element for element in root.iter()
                if get_local_name(element.tag).lower() == "unit"
            ]

            facts = [
                element for element in root
                if element.attrib.get("contextRef")
            ]

            fact_names = [
                get_local_name(element.tag)
                for element in facts[:15]
            ]

            report.append({
                "symbol": symbol,
                "file": xml_path.name,
                "root_tag": get_local_name(root.tag),
                "namespace": namespace,
                "context_count": len(contexts),
                "unit_count": len(units),
                "top_level_fact_count": len(facts),
                "sample_fact_names": ", ".join(fact_names)
            })

            logger.info(
                "%s | Root: %s | Contexts: %d | Units: %d | Facts: %d",
                symbol,
                get_local_name(root.tag),
                len(contexts),
                len(units),
                len(facts)
            )

        except ET.ParseError as error:
            logger.error("XML parsing failed for %s: %s", symbol, error)

        except Exception:
            logger.exception("Unexpected error inspecting %s", symbol)

    if report:
        report_df = pd.DataFrame(report)
        report_df.to_csv(REPORT_FILE, index=False)

        logger.info("Structure report saved: %s", REPORT_FILE)

        print("\nXBRL STRUCTURE REPORT")
        print(report_df.to_string(index=False))


if __name__ == "__main__":
    inspect_xbrl()
