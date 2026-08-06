@echo off
setlocal

echo.
echo === Bhagavad Gita: build site and PDF ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found in PATH.
    pause
    exit /b 1
)

for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)"') do set "QUARTO_PYTHON=%%P"

where quarto >nul 2>nul
if errorlevel 1 (
    echo ERROR: Quarto was not found in PATH.
    pause
    exit /b 1
)

echo [1/6] Generating site sources...
python tools\0_generate_site.py
if errorlevel 1 (
    echo ERROR in tools\0_generate_site.py
    pause
    exit /b 1
)

echo.
echo [2/6] Adding chapter titles...
python tools\1_add_chapter_titles.py
if errorlevel 1 (
    echo ERROR in tools\1_add_chapter_titles.py
    pause
    exit /b 1
)

echo.
echo [3/6] Rendering website...
quarto render
if errorlevel 1 (
    echo ERROR during quarto render
    pause
    exit /b 1
)

echo.
echo [4/7] Generating PDF sources...
python tools\2_generate_pdf_book.py
if errorlevel 1 (
    echo ERROR in tools\2_generate_pdf_book.py
    pause
    exit /b 1
)

echo.
echo [5/7] Rendering English PDF...
quarto render pdf_book.qmd --to pdf
if errorlevel 1 (
    echo ERROR during English PDF render.
    echo.
    echo If this is the first time you render PDF with Quarto, run:
    echo quarto install tinytex
    echo.
    pause
    exit /b 1
)

echo.
echo [6/7] Rendering Italian PDF...
quarto render pdf_book_it.qmd --to pdf
if errorlevel 1 (
    echo ERROR during Italian PDF render.
    echo.
    echo If this is the first time you render PDF with Quarto, run:
    echo quarto install tinytex
    echo.
    pause
    exit /b 1
)

echo.
echo [7/7] Checking PDFs in docs...
if not exist docs (
    echo ERROR: docs folder does not exist.
    pause
    exit /b 1
)

if not exist docs\bhagavad-gita-en.pdf (
    echo ERROR: English PDF was not written to docs.
    pause
    exit /b 1
)

if not exist docs\bhagavad-gita-it.pdf (
    echo ERROR: Italian PDF was not written to docs.
    pause
    exit /b 1
)

if exist docs\bhagavad-gita.pdf del /Q docs\bhagavad-gita.pdf

echo.
echo Done.
echo Website: docs\
echo PDFs: bhagavad-gita-en.pdf and bhagavad-gita-it.pdf
echo PDFs for website: docs\bhagavad-gita-en.pdf and docs\bhagavad-gita-it.pdf
echo.
pause
