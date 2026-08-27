# Aggiornare GPS

L'updater scarica sempre l'ultima versione del ramo `main` da:

https://github.com/rizindiegala/gps

Non servono Git, comandi da terminale o un account GitHub.

## Installazione per i colleghi

1. Aprire la pagina **Releases** del repository:
   https://github.com/rizindiegala/gps/releases/latest
2. Scaricare il file corretto:
   - Windows: `Aggiorna-GPS-Windows.exe`
   - Mac Apple Silicon: `Aggiorna-GPS-macOS-Apple-Silicon.zip`
3. Copiare l'updater nella cartella principale di GPS, accanto ad `app.py`.
4. Chiudere GPS prima di avviare l'aggiornamento.

L'updater può essere riutilizzato per tutti gli aggiornamenti futuri.

## Utilizzo

1. Chiudere GPS.
2. Fare doppio clic su **Aggiorna GPS**.
3. Attendere il messaggio **Aggiornamento completato**.
4. Chiudere l'updater e avviare normalmente GPS.

L'updater:

- scarica il codice più recente;
- aggiorna le dipendenze dentro l'ambiente Python `env`;
- scarica in anticipo il browser usato per le ricerche, così la prima ricerca
  non resta in attesa;
- elimina solo i vecchi file che erano gestiti dall'updater;
- ripristina i file precedenti se la copia del nuovo codice fallisce.

Non modifica mai:

- `.env` e le credenziali Genba;
- `data_file/data.json`;
- i file dentro `exports/`;
- i chromedriver eventualmente messi a mano nel progetto;
- log, cookie, ambiente Python e repository Git locale.

## Primo avvio su Windows

Gli eseguibili non sono firmati. Windows potrebbe mostrare SmartScreen:

1. scegliere **Ulteriori informazioni**;
2. scegliere **Esegui comunque**.

I successivi avvii si fanno normalmente con doppio clic.

## Primo avvio su macOS

La build supporta Mac Apple Silicon (M1 o successivi). Poiché l'app non è firmata:

1. estrarre lo ZIP;
2. copiare `Aggiorna GPS.app` accanto ad `app.py`;
3. fare clic destro sull'app e scegliere **Apri**;
4. confermare nuovamente **Apri**.

Se macOS continua a bloccarla, aprire **Impostazioni di Sistema > Privacy e
sicurezza** e scegliere **Apri comunque**. In seguito basterà il doppio clic.

## Errori comuni

- **GPS è aperto**: chiudere la finestra/terminale di GPS e riprovare.
- **Python non è installato**: l'installazione non contiene più `env`; installare
  Python 3 oppure ripristinare la cartella `env`.
- **Impossibile contattare GitHub**: controllare la connessione Internet e
  verificare che il repository sia pubblico.
- **Installazione dipendenze fallita**: il codice non viene sostituito; copiare
  il testo dell'errore e inviarlo allo sviluppatore.

## Creare una nuova build dell'updater

Il workflow `.github/workflows/build-updaters.yml` parte automaticamente quando
cambiano i file dell'updater. Può anche essere avviato da:

**GitHub > Actions > Build updater > Run workflow**

Al termine crea una nuova Release e la imposta come ultima versione. Le normali
modifiche all'app non richiedono di ricompilare l'updater: esso scarica sempre
il contenuto corrente di `main`.
