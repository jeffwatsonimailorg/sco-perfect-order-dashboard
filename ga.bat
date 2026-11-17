@echo off
cls

REM  NOTE:  for each new project, the file list below should be updated,
REM         and maintained to include the relevant files.

Title Git Add Multiple Files
@ECHO.
@ECHO Beginning to execute your GIT ADD statements.
@ECHO.
REM This batch file will execute multiple commands, each of which will add
REM one file to the staging area.  This is an attempt to reduce the quantity
REM of times the below phrases are typed, in whole or in part.
rem
REM My observation is if the "git add" command line is followed by multiple
REM file names, and the git add fails for one file, the balance of the
REM files is NOT added.  This script will alleviate the need to determine
REM which hand-typed name failed, edit it from command line, and
REM research failing offender.  This format will add all to be added
REM consistently to the staging area.

echo on

REM git add *.*py*
git add *.docx
REM git add sjwModules/
git add *.md
git add .gitignore
REM git add config.yaml
REM git add *.code-workspace
REM git add images/
REM git add pyproject.toml
git add Tableau/
git add artifacts/
REM git add requirements.txt
REM git add *.sql
git status


