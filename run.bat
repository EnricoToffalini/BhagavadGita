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
echo [4/6] Generating PDF source...
python tools\2_generate_pdf_book.py
if errorlevel 1 (
    echo ERROR in tools\2_generate_pdf_book.py
    pause
    exit /b 1
)

echo.
echo [5/6] Rendering PDF...
quarto render pdf_book.qmd --to pdf
if errorlevel 1 (
    echo ERROR during PDF render.
    echo.
    echo If this is the first time you render PDF with Quarto, run:
    echo quarto install tinytex
    echo.
    pause
    exit /b 1
)

echo.
echo [6/6] Copying PDF into _site...
if not exist _site (
    echo ERROR: _site folder does not exist.
    pause
    exit /b 1
)

copy /Y bhagavad-gita.pdf _site\bhagavad-gita.pdf
if errorlevel 1 (
    echo ERROR while copying PDF into _site.
    pause
    exit /b 1
)

echo.
echo Done.
echo Website: _site\
echo PDF: bhagavad-gita.pdf
echo PDF for website: _site\bhagavad-gita.pdf
echo.
pause