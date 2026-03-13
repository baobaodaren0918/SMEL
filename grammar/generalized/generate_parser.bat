@echo off
REM ANTLR Parser Generator Script for SMEL_Generalized.g4
REM Run this script from the grammar/generalized/ directory

cd /d "%~dp0"

echo Generating ANTLR parser from SMEL_Generalized.g4...
java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMEL_Generalized.g4

if %ERRORLEVEL% == 0 (
    echo Done! SMEL_Generalized parser files generated in current directory.
    echo Files created:
    echo   - SMEL_GeneralizedLexer.py
    echo   - SMEL_GeneralizedParser.py
    echo   - SMEL_GeneralizedListener.py
    echo   - SMEL_GeneralizedVisitor.py
) else (
    echo Error generating parser!
    exit /b 1
)
