@echo off
setlocal enabledelayedexpansion
color 0A

echo ==========================================
echo    AGGIORNAMENTO AUTOMATICO GITHUB (HIPA)
echo ==========================================
echo/

REM Il token viene letto dalla variabile d'ambiente di sistema.
if "%GITHUB_TOKEN%"=="" (
    echo [ATTENZIONE] Variabile d'ambiente GITHUB_TOKEN non trovata.
    echo            Proseguo comunque usando le credenziali Git salvate ^(Credential Manager^).
    echo            Se il push fallisce, imposta il token con: setx GITHUB_TOKEN "IL_TUO_TOKEN"
)

REM --- TENTA RIMOZIONE FILE LETTERALE 'nul' (se presente) ---
del /f /q "\\?\%CD%\nul" >nul 2>&1

REM --- FIX LOCK FILES ---
if not exist ".git\index.lock" goto SKIP_LOCK
echo [*] Rilevato file di blocco (index.lock). Rimozione in corso...
del /f /q ".git\index.lock"
if not errorlevel 1 goto SKIP_LOCK
echo [X] Impossibile rimuovere il file di blocco. Chiudi altri processi Git.
goto ERRORE
:SKIP_LOCK

REM --- CONTROLLO INIZIALIZZAZIONE ---
if not exist ".git" (
    echo [*] Inizializzazione repository in corso...
    git init
    git branch -M main
    git remote add origin https://github.com/trandafile/hipa
)

REM --- CONFIGURAZIONE IDENTITA E ACCESSO (DEVE STARE DOPO GIT INIT) ---
git config user.email "lu.boccia@gmail.com"
git config user.name "trandafile"
git config core.safecrlf false

REM --- CONFIGURAZIONE .GITIGNORE ---
if not exist ".gitignore" (
    echo [*] Creazione .gitignore ottimizzato...
    echo # HFSS e Simulazione> .gitignore
    echo *.aedtresults/>> .gitignore
    echo *.results/>> .gitignore
    echo *.lock>> .gitignore
    echo *.auto>> .gitignore
    echo *.semaphore>> .gitignore
    echo *.asol>> .gitignore
    echo *.log>> .gitignore
)

REM 0. Pull preventivo
echo [0/4] Controllo aggiornamenti remoti...
git pull origin main --rebase --autostash >nul 2>&1

REM 1. Aggiunta file
echo/
echo [1/4] Aggiunta file locali in corso...
REM Pulisce la cache nel caso il gitignore sia cambiato (ignora errori se e' il primo commit)
git rm -r --cached . >nul 2>&1
git add .
if errorlevel 1 goto ERRORE

REM --- GESTIONE ISSUE TRAMITE API GITHUB ---
echo/
echo [2/4] Controllo Issue aperte su GitHub...
powershell -Command "$token='%GITHUB_TOKEN%'; $headers=@{}; if($token -ne ''){ $headers['Authorization']='Bearer '+$token }; $response = Invoke-RestMethod -Uri 'https://api.github.com/repos/trandafile/hipa/issues?state=open' -Headers $headers -ErrorAction SilentlyContinue; if($response){ Write-Host '--- ISSUE APERTE ---' -ForegroundColor Cyan; foreach($issue in $response){ Write-Host \"[#$($issue.number)] $($issue.title)\" } Write-Host '--------------------' -ForegroundColor Cyan} else { Write-Host 'Nessuna issue trovata (o repo privato senza token configurato).' -ForegroundColor Yellow }"

echo/
set "issue_suffix="
set /p num_issues="Vuoi associare/chiudere issue? (es: 3 o 3,5,12 o premi INVIO per saltare): "
if not "!num_issues!"=="" (
    set "processed=!num_issues:,= !"
    set "issue_suffix="
    for %%i in (!processed!) do (
        set "issue_suffix=!issue_suffix! Fixes #%%i"
    )
    echo [*] Il commit fara' riferimento alle issue:!issue_suffix!
)

REM 2. Messaggio e Commit
echo/
set /p desc="[3/4] Scrivi cosa hai cambiato (premi Invio per usare Data e Ora): "
if "!desc!"=="" set desc=Aggiornamento automatico %date% %time%

set "final_commit_msg=!desc!!issue_suffix!"

echo [*] Creazione commit...
git commit -m "!final_commit_msg!"
if errorlevel 1 (
    echo [*] Nulla da committare o nessun file modificato.
    goto FINE_PUSH
)

REM 3. Push
echo/
echo [4/4] Caricamento su GitHub...
if "%GITHUB_TOKEN%"=="" (
    git push -u origin main
) else (
    REM Formato corretto per l'uso del token nei remote HTTPS
    git push -u https://trandafile:%GITHUB_TOKEN%@github.com/trandafile/hipa.git main
)
if errorlevel 1 goto ERRORE

:FINE_PUSH
REM --- GESTIONE VERSIONI (TAGS) ---
echo/
echo ==========================================
echo Vuoi creare una nuova VERSIONE UFFICIALE?
echo (Questo "congelera'" lo stato attuale, es. v1.0.0)
echo ==========================================
set /p do_tag="Creare nuova versione? (s/n): "
if /i "!do_tag!"=="s" (
    set /p tag_name="Inserisci il nome della versione (es. v1.0 o v1.2.1): "
    if not "!tag_name!"=="" (
        echo [*] Creazione versione !tag_name! in corso...
        git tag !tag_name!
        git push origin !tag_name!
        echo [*] Versione !tag_name! creata e caricata con successo su GitHub!
    )
)

echo/
echo ==========================================
echo    SUCCESSO! PROCEDURA COMPLETATA.
echo ==========================================
color 07
pause
exit

:ERRORE
color 0C
echo/
echo ========================================================
echo    ERRORE CRITICO RILEVATO
echo ========================================================
echo/
echo Possibili cause:
echo 1. Google Drive sta bloccando i file (sincronizzazione in corso).
echo 2. File aperti in altri programmi (es. HFSS o PDF reader).
echo 3. Connessione internet assente.
echo 4. Credenziali Git non valide.
echo/
pause
color 07
exit /b