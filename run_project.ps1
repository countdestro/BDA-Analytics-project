param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("etl", "dashboard")]
    [string]$Task
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$streamlit = Join-Path $projectRoot ".venv\Scripts\streamlit.exe"

if ($Task -eq "dashboard") {
    & $streamlit run code/dashboard/app.py
    exit $LASTEXITCODE
}

$shortPython = (cmd /c 'for %I in (".venv\Scripts\python.exe") do @echo %~sI').Trim()
$shortProject = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $shortPython))
$bundledHadoop = Join-Path $projectRoot ".hadoop-native\hadoop-3.5.0"
if (-not (Test-Path (Join-Path $bundledHadoop "bin\winutils.exe"))) {
    throw "Bundled Hadoop Windows utilities are missing: $bundledHadoop"
}
$env:TEMP = Join-Path $shortProject ".spark-tmp"
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP
$env:SPARK_HOME = Join-Path $shortProject ".venv\Lib\site-packages\pyspark"
$env:PYSPARK_PYTHON = $shortPython
$env:PYSPARK_DRIVER_PYTHON = $shortPython
$env:HADOOP_HOME = Join-Path $shortProject ".hadoop-native\hadoop-3.5.0"
$env:PATH = "$env:HADOOP_HOME\bin;$env:PATH"
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
& $python code/processing/nse_spark_analysis.py
exit $LASTEXITCODE
