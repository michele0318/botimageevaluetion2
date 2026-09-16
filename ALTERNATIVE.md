# Confronto dei costi per uso prolungato

Rilevazione: 13 settembre 2026. Il bot Python può lavorare indipendentemente dalla chat. Il limite principale attuale è la qualità delle scelte, non il costo dei token locali.

| Metodo | Costo di inferenza | Stato |
| --- | --- | --- |
| Qwen3-VL 4B Instruct con Ollama | Nessuna tariffa API; elettricità e hardware | Test locale: 3/6 corrette. Non pronto per l'esame. |
| Qwen3.5 4B con Ollama | Nessuna tariffa API; elettricità e hardware | Installato e provato: 3/6 con scelta diretta; 1/6 con breve descrizione prima della scelta. Non impostato come predefinito. |
| Gemini 2.5 Flash-Lite API | $0,10 / milione token input; $0,40 output | Non collegato né provato. |
| Gemini 3.1 Flash-Lite API | $0,25 / milione token input; $1,50 output | Non collegato né provato. |

I prezzi Gemini Standard includono immagini in input; l'output è testo. Con l'ipotesi di 2.000 token input complessivi e 20 output per attività, 1.000 attività costerebbero $0,208 con 2.5 Flash-Lite o $0,53 con 3.1 Flash-Lite, escluse imposte. È una simulazione, non il consumo misurato su Gemini. Risoluzione delle immagini, token di ragionamento ed eventuali nuove chiamate cambiano il costo. Non sono stati attivati pagamenti.

Il piano gratuito Gemini è soggetto alle quote del progetto: non va assunto come illimitato per ore. Nel livello gratuito Google indica che i dati possono essere usati per migliorare i prodotti; nel livello a pagamento indica di no. Non sono state inviate immagini a Google. Un'integrazione cloud richiederebbe una chiave API configurata localmente e un limite di spesa esplicito.

Il programma locale usa una richiesta breve per coppia e una sessione browser persistente. Le operazioni di lettura e invio del sito sono codice, quindi non richiedono una chiamata a Codex per ogni clic. Il lavoro svolto in questa chat consuma invece la quota Codex: non c'è una garanzia di ore illimitate con pochi token.

Per confrontare un modello Ollama installato senza cambiare quello del bot:

```powershell
cd 'C:\Users\mannu\Wizard war\mindrift_bot'
& 'D:\Ollama\bot-venv\Scripts\python.exe' dataset_tools.py evaluate --model qwen3.5:4b
```

Il rapporto salva accuratezza, durata e conteggi token locali. Non invia risposte sul sito. Il confronto ripetuto sullo stesso piccolo insieme di test è esplorativo: servono ulteriori casi nuovi per una validazione indipendente.

Risultati misurati: `examples/report-20260913-090910.json` per Qwen3.5 diretto (circa 6–23 secondi di inferenza a modello caricato); `examples/report-20260913-091200.json` per la strategia sperimentale `--strategy evidence` (1/6, incluso un errore di formato). Quest'ultima resta solo un'opzione di test e non è usata dal bot. Il risultato diretto precedente di Qwen3-VL è in `examples/report-20260913-022824.json`.

Il prossimo confronto utile è con una API Flash-Lite sui dati verificati, prima di qualsiasi impiego nell'esame. La sua accuratezza su queste immagini è ancora sconosciuta. Senza una chiave API configurata sul PC non è stato possibile misurarla; non inserire chiavi in questo documento o nei log.

Fonti: [Qwen3.5 4B, dimensione e supporto visivo](https://ollama.com/library/qwen3.5:4b), [tariffe Gemini](https://ai.google.dev/gemini-api/docs/pricing), [quote Gemini](https://ai.google.dev/gemini-api/docs/rate-limits), [uso e limiti Codex](https://learn.chatgpt.com/docs/pricing).
