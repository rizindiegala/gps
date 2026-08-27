# GPS - Genba price scraper

Applicazione locale che, dato un elenco di sku id, legge i prezzi per valuta dal
portale Genba eTailer, li converte in USD, EUR e GBP e permette di esportarli in
un file Excel.

Gira sul computer di chi la usa: si apre nel browser all'indirizzo
`http://127.0.0.1:2000` e non è raggiungibile dall'esterno.

## Prerequisiti

Serve **solo Python 3** ([python.org/downloads](https://www.python.org/downloads/)).
Su Windows, durante l'installazione, spuntare **Add Python to PATH**.

Tutto il resto lo installa l'updater dentro la cartella dell'app, senza toccare
il sistema: le librerie Python finiscono nell'ambiente `env` e il browser usato
per le ricerche viene scaricato automaticamente da Selenium. Non serve
installare Google Chrome: se non c'è, viene usata una copia di Chrome for
Testing riservata all'app.

Serve inoltre il file **`.env`** con le credenziali, che non è incluso qui e
viene fornito separatamente. Vedere la sezione [Il file .env](#il-file-env).

## Installazione su Windows

1. Scaricare il codice:
   [main.zip](https://github.com/rizindiegala/gps/archive/refs/heads/main.zip)
   ed estrarre la cartella dove si preferisce, ad esempio `Documenti\GPS`.
2. Scaricare `Aggiorna-GPS-Windows.exe` dalla pagina
   [Releases](https://github.com/rizindiegala/gps/releases/latest) e copiarlo
   **dentro la cartella estratta**, accanto ad `app.py`.
3. Fare doppio clic su `Aggiorna-GPS-Windows.exe`. Se Windows mostra
   SmartScreen, scegliere **Ulteriori informazioni** e poi **Esegui comunque**.
   L'updater crea l'ambiente Python e installa le dipendenze: attendere il
   messaggio **Aggiornamento completato**.
4. Copiare il file `.env` nella stessa cartella.
5. Avviare l'app con **`run.bat`**.

## Installazione su Mac

L'updater è compilato per **Mac Apple Silicon** (M1 o successivi).

1. Scaricare il codice:
   [main.zip](https://github.com/rizindiegala/gps/archive/refs/heads/main.zip)
   ed estrarre la cartella dove si preferisce.
2. Scaricare `Aggiorna-GPS-macOS-Apple-Silicon.zip` dalla pagina
   [Releases](https://github.com/rizindiegala/gps/releases/latest), estrarlo e
   copiare `Aggiorna GPS.app` **dentro la cartella estratta**, accanto ad
   `app.py`.
3. Fare clic destro su `Aggiorna GPS.app`, scegliere **Apri** e confermare
   **Apri** una seconda volta: l'app non è firmata, quindi il doppio clic
   diretto viene bloccato al primo avvio. Attendere il messaggio
   **Aggiornamento completato**.
4. Copiare il file `.env` nella stessa cartella.
5. Avviare l'app con **`app.command`**. Se il doppio clic non funziona, aprire
   il Terminale nella cartella ed eseguire una volta `chmod +x app.command`.

## Il file .env

Contiene le credenziali e va copiato nella cartella principale, accanto ad
`app.py`. Non è nel repository e non deve essere condiviso pubblicamente.
La struttura è quella di [`.env.example`](.env.example):

```
GENBA_USERNAME=
GENBA_PASSWORD=
CURRENCYLAYER_API_KEY=
```

Senza questo file l'app si avvia ma non riesce a fare login su Genba né a
convertire i prezzi in valuta.

**Il nome deve iniziare con il punto**: `.env`, non `env`. I sistemi nascondono
i file che iniziano con il punto e alcuni programmi di posta lo rimuovono in
fase di salvataggio, quindi vale la pena controllare. Su macOS si mostrano i
file nascosti nel Finder con **Cmd + Shift + punto**, su Windows dal menu
**Visualizza > Elementi nascosti**. Un file chiamato `env` senza il punto, oltre
a non essere letto dall'app, impedisce di creare l'ambiente Python.

## Uso

1. Avviare l'app: si apre il browser da solo. La finestra nera del terminale
   deve restare aperta per tutto il tempo di utilizzo.
2. Incollare gli sku id nel campo di sinistra, **uno per riga**.
3. Indicare la valuta di output: `usd`, `eur` oppure `gbp`.
4. Premere **Cerca** e attendere. Si apre una finestra di Chrome che naviga da
   sola sul portale Genba: non chiuderla e non usarla. Alla primissima ricerca,
   se il browser non era ancora stato scaricato, l'attesa può arrivare a qualche
   minuto; dalla seconda in poi è immediata.
5. A ricerca conclusa, **Esporta tutto** genera un file `.xlsx` dentro la
   sottocartella `exports`.

I dati di un prodotto già cercato vengono riutilizzati dalla cache locale per
un'ora, quindi le ricerche ripetute sono immediate e non riaprono Chrome.

Per chiudere l'app: chiudere la finestra del terminale.

## Aggiornamenti

Chiudere GPS e fare doppio clic sull'updater. Scarica sempre l'ultima versione e
non tocca il file `.env`, la cache dei prezzi né i file già esportati.
Istruzioni complete e casi particolari in [AGGIORNAMENTO.md](AGGIORNAMENTO.md).

## Problemi comuni

- **Si apre e si chiude subito**: manca l'ambiente Python. Eseguire l'updater
  nella cartella dell'app.
- **Errore sulle credenziali**: manca il file `.env` oppure è incompleto.
- **La ricerca non trova il prodotto**: il portale Genba può aver cambiato
  pagina, oppure lo sku id non esiste nel catalogo.
- **GPS è aperto** durante l'aggiornamento: chiudere la finestra del terminale
  e riavviare l'updater.
