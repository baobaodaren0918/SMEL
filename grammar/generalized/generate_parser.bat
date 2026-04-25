@echo off
REM ANTLR Parser Generator Script for SMILE_Generalized.g4
REM Run this script from the grammar/generalized/ directory

cd /d "%~dp0"

echo Generating ANTLR parser from SMILE_Generalized.g4...
java -jar ..\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor SMILE_Generalized.g4

if %ERRORLEVEL% == 0 (
    echo Done! SMILE_Generalized parser files generated in current directory.
    echo Files created:
    echo   - SMILE_GeneralizedLexer.py
    echo   - SMILE_GeneralizedParser.py
    echo   - SMILE_GeneralizedListener.py
    echo   - SMILE_GeneralizedVisitor.py
) else (
    echo Error generating parser!
    exit /b 1
)
