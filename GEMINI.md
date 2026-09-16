# Usare Gemini nel bot

Gemini è ora un provider opzionale. La modalità locale resta quella predefinita finché non lo configuri. Gemini riceve prompt, immagini e criteri tramite API Google: non gira sulla GPU del PC e la quota API è distinta dall'app Gemini. Il piano gratuito ha limiti; ore di utilizzo non sono garantite gratuitamente.

## Attivazione

1. Ferma il bot prima di cambiare provider.
2. Crea una chiave su [Google AI Studio](https://aistudio.google.com/apikey). Non incollarla nella chat.
3. In PowerShell esegui:

```powershell
Set-Location 'C:\Users\mannu\Wizard war\mindrift_bot'
& 'D:\Ollama\bot-venv\Scripts\python.exe' configure_gemini.py
```

Inserisci il limite giornaliero stimato in dollari e la chiave quando richiesta: i caratteri sono nascosti. La chiave viene cifrata con Windows DPAPI nella cartella di stato del bot, fuori dal progetto. Questa procedura configura soltanto: non fa inferenze né avvia attività.

Il modello iniziale è `gemini-3.8-flash`, con ragionamento basso. Non è necessariamente il modello usato nell'app Gemini: occorre confrontare lo stesso livello di qualità prima di affidargli attività reali.

## Test senza invii a Mindrift

```powershell
& 'D:\Ollama\bot-venv\Scripts\python.exe' dataset_tools.py evaluate --split test
```

Questo comando invia gli esempi a Google, consuma quota API e salva un rapporto in `examples/report-*.json`, con accuratezza, tempi e consumi. Esclude la ricerca della risposta esatta salvata e usa solo criteri di feedback della suddivisione train. Il piccolo insieme di test già consultato in esperimenti precedenti non certifica l'accuratezza futura. La raccolta attuale comprende 72 esempi verificati dal sito/utente, di cui 12 di test. Senza chiave il test reale non può essere eseguito.

Per avviare successivamente il bot usa `start_bot.bat`: la formazione automatica è ora il comportamento predefinito. L'esame resta un punto di arresto. Il bot conserva la finestra durante le pause e può riprendere quando compare una nuova formazione. I messaggi sono visibili nel terminale e salvati in `bot.log`.

## Consumi e limiti

Prima di ogni inferenza il bot conta i token del prompt e delle immagini, poi riserva nel registro SQLite il costo stimato dell'input con un margine del 10% e dell'intero massimo di 2048 token di output, compreso il ragionamento. A risposta ricevuta riconcilia i consumi comunicati da Google. Se la chiamata ha esito incerto, mantiene la riserva e non riprova automaticamente. Errori API, risposte incomplete o scelte non valide fermano gli invii.

Il limite giornaliero usa la data del PC e riguarda soltanto questo bot: è un freno basato su stime, non un tetto alla fattura dell'account Google. Include anche l'estrazione dei criteri dal feedback. Le risposte già verificate per la stessa coppia non richiedono inferenza. Non vengono usati strumenti di ricerca o servizi aggiuntivi a pagamento.

Tariffe standard verificate il 14 settembre 2026: Gemini 3.8 Flash costa $0,75 per milione di token in ingresso e $3,75 in uscita, ragionamento incluso, fino al 31 dicembre 2026. Da gennaio sono indicati $1,50 e $7,50. Esempio puramente indicativo: 2000 token in ingresso e 500 in uscita costano circa $0,003375 per confronto alle tariffe promozionali. Immagini, istruzioni e ragionamento cambiano il consumo. [Tariffe ufficiali](https://ai.google.dev/gemini-api/docs/pricing).

Il codice richiede un aggiornamento delle tariffe dopo gennaio 2027 e prima di usare un altro modello. Il registro è `D:\Ollama\bot-state\gemini-usage.sqlite`; non cancellarlo per aggirare il limite.

## Tornare al modello locale

```powershell
& 'D:\Ollama\bot-venv\Scripts\python.exe' configure_gemini.py --local
```

Riavvia poi il bot. Il modello Ollama installato e gli esempi salvati restano disponibili.

## Stato della verifica

L'integrazione dispone di test simulati per immagini e prompt, conteggio del ragionamento, arresto al limite, errori e risposte invalide. Il confronto reale di accuratezza con Gemini richiede la tua chiave e non è ancora stato eseguito. Completare la formazione del sito non dimostra che il modello abbia imparato a generalizzare; non viene promesso un risultato perfetto.
