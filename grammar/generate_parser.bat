@echo off
REM ANTLR Parser Generator Script
REM Run this script from the grammar/ directory

cd /d "%~dp0"

echo Generating ANTLR parser from SMEL.g4...
java -jar antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMEL.g4

if %ERRORLEVEL% == 0 (
    echo Done! Parser files generated.
) else (
    echo Error generating parser!
    exit /b 1
)
