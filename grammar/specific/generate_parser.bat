@echo off
REM ANTLR Parser Generator Script for SMEL_Specific.g4
REM Run this script from the grammar/specific/ directory

cd /d "%~dp0"

echo Generating ANTLR parser from SMEL_Specific.g4...
java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMEL_Specific.g4

if %ERRORLEVEL% == 0 (
    echo Done! SMEL_Specific parser files generated in current directory.
    echo Files created:
    echo   - SMEL_SpecificLexer.py
    echo   - SMEL_SpecificParser.py
    echo   - SMEL_SpecificListener.py
    echo   - SMEL_SpecificVisitor.py
) else (
    echo Error generating parser!
    exit /b 1
)
