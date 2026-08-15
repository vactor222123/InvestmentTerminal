$ErrorActionPreference = "Stop"

$ExpectedPythonMajorMinor = "3.13"

$ActualPythonMajorMinor = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$ActualPythonFull = python -c "import platform; print(platform.python_version())"

if ($ActualPythonMajorMinor -ne $ExpectedPythonMajorMinor) {
    throw "Dependency locks must be compiled with Python $ExpectedPythonMajorMinor.x; found $ActualPythonFull"
}

python -m pip install --upgrade --requirement requirements-compiler.txt

python -m piptools compile `
    --generate-hashes `
    --resolver=backtracking `
    --output-file=requirements.lock `
    requirements.in

python -m piptools compile `
    --generate-hashes `
    --resolver=backtracking `
    --output-file=requirements-dev.lock `
    requirements-dev.in

Write-Host "Generated requirements.lock and requirements-dev.lock with Python $ActualPythonFull."
