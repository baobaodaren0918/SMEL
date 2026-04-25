@echo off
REM ANTLR Parser Generator Script for SMILE_Specific.g4
REM Run this script from the grammar/specific/ directory

cd /d "%~dp0"

echo Generating ANTLR parser from SMILE_Specific.g4...
java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMILE_Specific.g4

if %ERRORLEVEL% == 0 (
    echo Done! SMILE_Specific parser files generated in current directory.
    echo Files created:
    echo   - SMILE_SpecificLexer.py
    echo   - SMILE_SpecificParser.py
    echo   - SMILE_SpecificListener.py
    echo   - SMILE_SpecificVisitor.py
) else (
    echo Error generating parser!
    exit /b 1
)
