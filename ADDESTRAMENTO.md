# Apprendimento locale: guida e limiti

## Materiale letto dal sito

Sono stati archiviati e analizzati localmente 70 articoli della Wiki, le istruzioni e le FAQ: 72 fonti. I testi originali restano in `site_material/articles` e `site_material/dialogs.json`; i criteri estratti, con citazioni controllate, in `site_material/knowledge`. Il bot recupera i criteri pertinenti al prompt corrente e legge anche i suggerimenti contestuali e le immagini di riferimento della task.

Sono stati archiviati 233 file immagine collegati alle guide, di cui 232 decodificabili, e preparati 181 esempi con didascalie originali in `site_material/teaching/examples.json`. Queste didascalie spiegano elementi visivi: non sono automaticamente etichette «vince immagine 1/2».

Memorizzare queste informazioni non modifica i pesi di Qwen o LLaVA. Il test Qwen3.5 con criteri del sito e output JSON del 13 settembre 2026 ha ottenuto 3/6, senza gli errori di formato della prova precedente. Non dimostra affidabilità sulle attività nuove.

## Esperimento che modifica i pesi

`train_ranker.py` adatta un valutatore ImageReward separato da Ollama. Congela il modello visivo e aggiorna 768 pesi correttivi del punteggio usando solo preferenze verificate: attualmente 31 esempi di training e 6 di test. Le correzioni dubbie vengono escluse. Le didascalie della Wiki non vengono trasformate in preferenze inventate.

Risultati del 13 settembre 2026: ImageReward originale 3/6; primo adattamento di 16 pesi 3/6; adattamento della rappresentazione completa a 768 pesi 2/6. Il primo tentativo usava caratteristiche quasi tutte equivalenti (rango numerico uno); il secondo elimina quel limite ma non migliora la generalizzazione. I pesi sono stati realmente aggiornati e salvati, ma non vengono usati per invii automatici. La mediana di elaborazione delle coppie era circa 0,35 secondi a modello caricato; caricamento e prima inizializzazione richiedono molto più tempo.

La regolarizzazione è scelta con una validazione interna ai soli dati di training. Le immagini dello stesso gruppo devono stare nella stessa suddivisione. I sei esempi di test sono pochi e sono già stati esaminati in precedenti esperimenti: il risultato è esplorativo, non una certificazione.

L'implementazione originale ImageReward taglia il testo a 35 token. L'esperimento usa tutti i token suddivisi in parti e media le rappresentazioni: conserva il contenuto, ma può perdere relazioni tra parti lontane. Inoltre ImageReward usa un ritaglio centrale a 224 pixel, che può perdere dettagli laterali e scritte piccole. Il rapporto confronta anche la versione originale.

## Come ripetere la prova

Apri PowerShell e vai nella cartella:

```powershell
Set-Location 'C:\Users\mannu\Wizard war\mindrift_bot'
```

Quando Ollama non sta valutando una task, libera la memoria GPU:

```powershell
& 'D:\Ollama\app\ollama.exe' stop qwen3.5:4b
& 'D:\Ollama\app\ollama.exe' stop qwen3-vl:4b-instruct
```

Avvia estrazione delle caratteristiche, addestramento e valutazione:

```powershell
& 'D:\Ollama\ranker-venv\Scripts\python.exe' train_ranker.py
```

Per ripetere soltanto l'ottimizzazione usando le caratteristiche già salvate:

```powershell
& 'D:\Ollama\ranker-venv\Scripts\python.exe' train_ranker.py --train-only
```

Se immagini, etichette o prompt cambiano, la cache viene invalidata. Il comando completo ricalcola le caratteristiche. Il comando `--train-only` rifiuta una cache non aggiornata.

Gli artefatti sono `ranker/features.pt`, `ranker/adapter.pt` e `ranker/report.json`. L'ultimo contiene risultati prima/dopo, suddivisione dei dati e limiti. Questo esperimento non invia risposte al sito e non attiva automaticamente il nuovo valutatore nel bot.

Per provare una coppia senza inviarla, salva il prompt completo in un file di testo UTF-8 e usa:

```powershell
& 'D:\Ollama\ranker-venv\Scripts\python.exe' rank_pair.py 'prompt.txt' 'prima.png' 'seconda.png'
```

Il comando mostra la scelta originale e quella adattata. La differenza di punteggio non è una probabilità di correttezza.

## Correggere altri esempi

La formazione salva prompt, immagini e feedback in `examples`. Una correzione verificata può essere registrata anche da terminale:

```powershell
& 'D:\Ollama\bot-venv\Scripts\python.exe' dataset_tools.py status
& 'D:\Ollama\bot-venv\Scripts\python.exe' dataset_tools.py label ID_ESATTO 2 --verification 'Risposta verificata e motivazione'
```

Sostituisci `ID_ESATTO`, la scelta e la motivazione con i dati effettivi. Non etichettare corretta una scelta solo perché l'ha prodotta il bot. Dopo nuove correzioni, ripeti `train_ranker.py` e confronta i risultati. Per misurare la capacità su casi nuovi servono ulteriori esempi verificati che non abbiano guidato le modifiche.

L'elaborazione avviene sul PC, senza API a consumo. Il primo avvio scarica il modello pubblico e le dipendenze; le immagini delle task non vengono inviate a un servizio di inferenza. Lavorare su questo progetto tramite Codex continua invece a utilizzare la quota della chat.
