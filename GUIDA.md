# Formazione automatica e correzioni locali

**Gemini opzionale:** configurazione della chiave sul PC, limite di consumo e test sugli esempi salvati in [GEMINI.md](GEMINI.md). Non è ancora stato eseguito un test reale Gemini: manca la chiave API.

**Esito del 13 settembre 2026:** formazione terminata, esame fermo a 0/25. Il test locale separato ha ottenuto 3/6 corrette (50%): il modello non è ancora dimostrato affidabile per l'esame. Il rapporto è `examples/report-20260913-022824.json`. La memoria delle correzioni funziona, ma non costituisce un fine-tuning dei pesi.

Per le alternative locali e cloud, i costi stimati per 1.000 attività e i confronti effettuati, vedi [ALTERNATIVE.md](ALTERNATIVE.md).

Fai doppio clic su `start_bot.bat`. L'avvio normale, compreso quello all'accesso a Windows, esegue la **formazione automatica**: legge il prompt corrente, confronta le immagini, invia la scelta e legge le correzioni esplicite del sito.

## Come funziona la formazione autonoma

Il bot legge anche le istruzioni dei nuovi moduli e chiude il relativo avviso “Stage Update”. Quando il sito segnala una scelta errata, salva la risposta corretta e la spiegazione, quindi applica la correzione. Quando riceve “You are right!”, riconosce il comando “To the next task!” e prosegue.

Riconosce anche “first image” e “second image”. Se il feedback non nomina il vincitore, può ricavare la risposta dal rifiuto del sito solo quando ci sono esattamente due opzioni e l'invio rifiutato appartiene alla stessa attività identificata. La provenienza della correzione resta nella cronologia. Una correzione che conferma la risposta appena rifiutata viene scartata.

Dalle spiegazioni ricava criteri condizionali, corredati da una citazione del feedback. Questi criteri vengono inclusi nelle valutazioni di **prompt nuovi**: per esempio, rispettare la richiesta di una resa 2D evitando un effetto 3D. Il prompt corrente resta il riferimento; non si limita a ricordare il numero dell'immagine vincente.

La formazione non richiede etichette manuali quando il feedback del sito è interpretabile. Se un esito è ambiguo, il programma sospende gli invii nella stessa finestra. Dopo la correzione del problema si può riprendere con `start_bot.bat --resume-training`, senza riaprire il browser. Il completamento degli esercizi corretti dopo un errore non dimostra accuratezza perfetta sui nuovi casi: l'esame resta subordinato alla verifica dei risultati.

## Modalità manuale facoltativa

Per raccogliere correzioni personalmente, usa `start_bot.bat --guided`. Questa modalità non sceglie e non invia risposte.

1. Usa il browser del bot per leggere il prompt, confrontare le immagini e svolgere la formazione sul sito.
2. Il pannello verde raccoglie in locale prompt e immagini della coppia corrente. Gli esempi nuovi non hanno una risposta inventata dal modello.
3. Quando hai verificato quale risposta è corretta, premi **1 corretta** oppure **2 corretta** nel pannello verde. Attendi il messaggio di salvataggio prima di cambiare pagina.
4. Questi pulsanti salvano una correzione: **non inviano risposte a Mindrift**. I comandi del sito restano sotto il tuo controllo.
5. Se hai salvato una correzione sbagliata, premi il pulsante corretto mentre la stessa coppia è visibile. Viene conservata anche la cronologia delle correzioni. Se non sai la risposta, lascia l'esempio senza etichetta.
6. Premi il titolo del pannello per ridurlo e vedere meglio le immagini. Chiudi tutte le finestre del browser del bot per terminare.

## Cosa viene imparato adesso

Le correzioni sono nella cartella `examples`, accanto al bot. Ogni cartella contiene le due immagini e `example.json` con prompt, risposta verificata e cronologia. Non vengono conservati URL firmati o cookie negli esempi.

Quando viene richiesta una scelta al modello, il programma rilegge le correzioni verificate. Per una coppia già verificata con lo stesso prompt può riusare la risposta senza inferenza, anche se le due immagini sono invertite. Il confronto tollera soltanto minime variazioni di rendering. Per un prompt diverso il modello valuta di nuovo le immagini usando i criteri appresi, senza copiare la risposta di un'altra coppia. Correzioni contraddittorie bloccano la scelta e richiedono verifica.

Questo è apprendimento tramite esempi e istruzioni conservati in memoria esterna, **non un aggiornamento dei pesi del modello**. Il miglioramento sui casi nuovi deve essere misurato. Il vero fine-tuning non è stato ancora eseguito. Non esiste una garanzia di zero errori.

## Controllare i dati e l'accuratezza

Apri PowerShell:

```powershell
cd 'C:\Users\mannu\Wizard war\mindrift_bot'
& 'D:\Ollama\bot-venv\Scripts\python.exe' dataset_tools.py status
```

Per misurare il modello su esempi verificati riservati al test:

```powershell
& 'D:\Ollama\bot-venv\Scripts\python.exe' dataset_tools.py evaluate
```

Il test esclude il riuso delle risposte salvate, altrimenti la percentuale sarebbe ingannevole. Errori del modello o di elaborazione contano come risposte non corrette. Se non ci sono esempi verificati per il test, non viene inventata una percentuale. Coppie con le stesse immagini, anche invertite, restano nella stessa suddivisione per evitare contaminazione tra addestramento e test.

Per preparare i dati nel formato di addestramento QwenVL:

```powershell
& 'D:\Ollama\bot-venv\Scripts\python.exe' dataset_tools.py export
```

L'esportazione produce immagini affiancate, `train.json` e `test.json`, usando solo etichette verificate. Non avvia un addestramento. Il formato segue la [documentazione ufficiale QwenVL](https://github.com/QwenLM/Qwen3-VL/tree/main/qwen-vl-finetune).

## Modello locale e costi

Per il materiale letto dalla Wiki e l'esperimento di addestramento del valutatore separato, consulta [ADDESTRAMENTO.md](ADDESTRAMENTO.md). Include i comandi per ripetere la prova e verificare il risultato prima/dopo; non certifica il bot per l'esame.

Il modello selezionato è `qwen3-vl:4b-instruct` in Ollama; LLaVA resta installato. Inferenza su `127.0.0.1:11434`, cloud Ollama disattivato, nessuna API a pagamento. La raccolta guidata non chiama il modello e non elabora token. Per immagini nuove, l'inferenza continua a elaborare token sul PC senza tariffazione a consumo.

Il modello usa un contesto di 4096 token e resta caricato per 30 minuti dopo l'uso. Le immagini raccolte restano archiviate; solo la copia per l'inferenza viene adattata di dimensione per lasciare spazio al prompt e ai criteri appresi. Nell'ultima sessione, le valutazioni duravano circa 21 secondi a modello caricato. Il tempo varia con le immagini e non è una misura dell'accuratezza o una garanzia di quantità giornaliera.

## Accesso, arresto e modalità

Se il sito richiede l'accesso:

```powershell
.\start_bot.bat --login
```

Usa il tuo account Mindrift e attendi la chiusura automatica dopo la verifica. La sessione resta nel profilo dedicato `D:\Ollama\bot-state\browser`, separato dal Chrome normale, con backup cifrato sul tuo account Windows.

Per fermare il programma da un'altra finestra:

```powershell
.\start_bot.bat --stop
```

La modalità `--dry-run` valuta una coppia senza inviarla. `--collect-example` raccoglie una sola coppia senza usare il modello. `--train-auto` avvia la formazione con lettura del feedback ed è usata dall'avvio normale del batch. `--automatic` conserva il vecchio ciclo generico di invii e non va confusa con la nuova formazione.

Non ci sono refresh periodici o riavvii dopo gli errori. Il collegamento `MindriftLlavaBot.lnk` nella cartella Avvio di Windows apre la formazione automatica. Per disattivarlo, Win+R, `shell:startup`, elimina quel collegamento. Un successivo avvio normale del batch lo ricrea.

Se la pagina viene chiusa o l'attività scade durante la valutazione, il risultato non viene inviato. Giochi e altri programmi che usano la GPU possono rallentare l'inferenza: nella prova del 13 settembre una valutazione ha richiesto 168 secondi, contro circa 19–24 secondi nelle prove successive.
