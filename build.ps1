$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente Python' }
}
& .venv/Scripts/python.exe -m pip install -r requirements-search.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias' }
& .venv/Scripts/python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Falha nos testes' }
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --clean --onefile --console --name PIVisionTagFinder --icon PYTHON/Advanced/extract.ico buscar_tags.py
if ($LASTEXITCODE -ne 0) { throw 'Falha no PyInstaller' }
Copy-Item tags.example.txt dist/tags.example.txt
Copy-Item BUSCA_TAGS.md dist/BUSCA_TAGS.md
& .venv/Scripts/python.exe tests/smoke_exe.py
if ($LASTEXITCODE -ne 0) { throw 'Falha no teste local do executavel' }
Write-Host 'Executavel: dist/PIVisionTagFinder.exe'
