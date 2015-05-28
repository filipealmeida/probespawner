@echo off
if "%~1" equ "" goto :error

setLocal EnableDelayedExpansion
set CLASSPATH="
for /R ./jars %%a in (*.jar) do (
  set CLASSPATH=!CLASSPATH!;%%a
)
set CLASSPATH=!CLASSPATH!"
echo !CLASSPATH!

jython.bat probespawner.py --configuration=%1
goto :EOF

:error
echo USAGE: %0 JSONFILE
exit /b %errorlevel%