# Run all tests from project root. Sets PYTHONPATH so 'equipment_monitoring' is found.
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
$env:PYTHONPATH = Join-Path $scriptDir "src"
py -m pytest unit_tests integration_tests -v
