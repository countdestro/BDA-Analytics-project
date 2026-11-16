import os
import sys

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("BDA-Stock-Analytics")
    .master("local[*]")
    .getOrCreate()
)

print("Spark version:", spark.version)

data = [
    ("RELIANCE", 1250),
    ("TCS", 980),
    ("INFY", 750)
]

df = spark.createDataFrame(data, ["symbol", "price"])

df.show()

spark.stop()