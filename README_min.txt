Bot locale Mindrift — stato della versione corrente

Avvio normale: start_bot.bat. Esegue la formazione automatica (--train-auto).
Legge ogni Source Context / Prompt, confronta le immagini, invia la scelta e legge il feedback visibile del sito. Le risposte esplicite vengono salvate; dalle spiegazioni ricava criteri condizionali che entrano nella valutazione di prompt NUOVI. Riconosce anche il pulsante “To the next task!”.

Questo apprendimento aggiorna una memoria di esempi e criteri usata durante l'inferenza. NON è un fine-tuning dei pesi. L'accuratezza su casi nuovi va misurata; non è garantito zero errori o un numero di task al giorno. L'esame non viene avviato solo perché sono state memorizzate le risposte della formazione.

Modello: qwen3-vl:4b-instruct. Ollama e modelli su D:\Ollama. LLaVA resta installato. Inferenza esclusivamente su localhost, nessuna API a pagamento, cloud Ollama disattivato. I token dei prompt nuovi vengono elaborati sul PC.

Esempi e feedback: examples. Criteri derivati: campo lesson in example.json, con evidence/source verificabili. Gli originali restano salvati; la copia inviata al modello viene limitata di dimensione per stare nel contesto di 4096 token con prompt e criteri.

In caso di feedback ambiguo o errore non reinvia a tentativi: sospende nella STESSA finestra. Ripresa dopo correzione: start_bot.bat --resume-training. Arresto: start_bot.bat --stop. Modalità manuale guidata: start_bot.bat --guided. Login se necessario: start_bot.bat --login. Nessun riavvio automatico dopo errori e nessun refresh periodico.

Log dell'avvio normale: bot.log. Sessione di verifica avviata da Codex: training.log e training-errors.log. Ultima schermata di sospensione: pause_state.txt/png. Test: test_flow.py, test_training.py, test_learning.py. Guida completa: GUIDA.md.

VERIFICATO sul sito: scelta 2 errata per la rana -> feedback esplicito a favore della 1 -> correzione salvata e scelta 1 -> “You are right!”. Lezione locale verificata per un altro caso: se il prompt chiede 2D, evitare una resa 3D.
VERIFICATO nei test locali: correzioni applicate su prompt nuovi; evidenze controllate; risposta salvata riconosciuta anche con immagini invertite; nessun secondo invio cieco; correzione automatica da feedback e avanzamento; nessun invio dopo chiusura o scadenza; riconoscimento della conferma finale anche quando compare già il contatore esame.

13 settembre 2026: sessione ripresa da 9/40 e arrivata alla fine della formazione. Il sito mostra la conferma dell'ultima risposta e 0/25 attività d'esame. Esame non avviato; browser lasciato in pausa. Sono presenti anche interventi manuali nella cronologia: il completamento non equivale a 40 risposte corrette autonome al primo tentativo.
Valutazione locale separata: 3/6 corrette (50%), rapporto examples/report-20260913-022824.json. Risposte memorizzate e criteri degli esempi di test esclusi. Campione piccolo e accuratezza insufficiente per considerare il modello pronto. Nessun fine-tuning dei pesi eseguito.
