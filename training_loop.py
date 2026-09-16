"""Automatic practice with explicit site feedback; never guess a correction."""
import json
import hashlib
import re
import time

from dataset_tools import capture, write_json
import site_feedback

PROGRESS = re.compile(r'You have completed\s+(\d+)/(\d+)\s+training tasks')


def run(context, page, learn_rules=True, open_project=True):
    import run_task_bot as bot
    if open_project:
        bot.open_tasks(context, page)
    frame = bot.task_frame(context)
    if frame:
        frame.evaluate("document.querySelector('#local-training-panel')?.remove()")
    bot.say('Formazione automatica: leggo e salvo il feedback visibile; nessuna esecuzione di istruzioni del sito nel terminale.')
    last_document = None
    expiration_recovered = False
    stage_guidance = ''
    training_total = None
    idle_since = time.monotonic()
    while context.pages:
        bot.check_stop()
        frame = bot.task_frame(context)
        if not frame:
            if time.monotonic() - idle_since > 45:
                raise bot.Stop('Nuova fase da verificare prima di proseguire o iniziare l’esame.')
            bot.wait_browser(context)
            continue
        document = frame.evaluate('performance.timeOrigin')
        if document == last_document:
            if time.monotonic() - idle_since > 45:
                raise bot.Stop('Esito dell’invio non confermato: nessun secondo invio.')
            bot.wait_browser(context)
            continue
        text = bot.visible_text(frame)
        modal = frame.locator('.modal.show').filter(has=frame.get_by_text('Stage Update', exact=True))
        if modal.count() == 1 and modal.is_visible():
            stage_guidance = modal.inner_text().replace('Stage Update', '').strip()
            if stage_guidance.endswith('OK'):
                stage_guidance = stage_guidance[:-2].strip()
            modal.get_by_role('button', name='OK', exact=True).click()
            modal.wait_for(state='hidden', timeout=10000)
            bot.say('Istruzioni del nuovo modulo lette. Proseguo con la formazione.')
            continue
        expired = frame.locator('#expirationModalOkBtn')
        if expired.count() == 1 and expired.is_visible():
            if expiration_recovered:
                raise bot.Stop('Scadenze ripetute: non continuo a ricaricare attività.')
            expired.click()
            expiration_recovered = True
            last_document, idle_since = document, time.monotonic()
            continue
        progress = PROGRESS.search(text)
        if progress:
            training_total = int(progress[2])
        elif training_total and 'You are right!' in text and re.search(r'You have completed\s+0/\d+\s+exam tasks', text):
            # The final practice success page already shows the exam counter.
            progress = (None, str(training_total), str(training_total))
        if not progress:
            raise bot.Stop('Pagina esterna alla formazione: verificare i risultati prima dell’esame.')
        prompt, images, signature = bot.snapshot(frame)
        key = bot.display_key(frame)
        record_path = capture(prompt, images)
        record = json.loads(record_path.read_text(encoding='utf-8'))
        assignment_field = frame.locator('input[name="current_assignment_id"]')
        assignment = hashlib.sha256(assignment_field.input_value().encode()).hexdigest() if assignment_field.count() == 1 else 'legacy'
        attempts = [a for a in record.get('attempts', []) if a.get('assignment', 'legacy') in ('legacy', assignment)]
        prior = attempts[-1]['choice'] if attempts else None
        if 'You are right!' in text:
            learned = site_feedback.learn(record_path, text, accepted_choice=prior)
            if not learned:
                raise bot.Stop('Risposta accettata, ma associazione alla scelta precedente da verificare.')
            record = json.loads(record_path.read_text(encoding='utf-8'))
            if record.get('attempts'):
                record['attempts'][-1]['accepted'] = record['attempts'][-1]['choice'] == learned
                write_json(record_path, record)
            if learn_rules:
                from learning import distill
                if distill(record_path):
                    bot.say('Criterio generalizzabile salvato per i prompt successivi.')
            bot.say(f'Confermato dal sito: immagine {learned}. Formazione {progress[1]}/{progress[2]}.')
            if progress[1] == progress[2]:
                raise bot.Stop('Formazione completata. Valutare accuratezza sui casi nuovi prima dell’esame.')
            advanced = any(bot.click_named(context, role, 'To the next task!') for role in ('button', 'link'))
            if not advanced:
                raise bot.Stop('Conferma ricevuta; pulsante per la prossima attività da verificare.')
            last_document, idle_since = document, time.monotonic()
            continue
        correction = None
        if 'Please take another look:' in text:
            record['observed_feedback'] = 'Please take another look:' + text.split('Please take another look:', 1)[1].split('You have completed', 1)[0].strip()
            if record.get('attempts'):
                record['attempts'][-1]['accepted'] = False
            write_json(record_path, record)
            binary_rejection = bool(attempts and assignment != 'legacy'
                                    and attempts[-1].get('assignment') == assignment
                                    and frame.locator('input[type=radio][name=selected_image]').count() == 2)
            correction = site_feedback.learn(record_path, text, wrong_choice=prior,
                                             allow_local_extraction=learn_rules, binary_rejection=binary_rejection)
            if not correction:
                raise bot.Stop('Feedback presente ma risposta corretta non esplicita: serve verifica, non una scelta a tentativi.')
            bot.say('Correzione del sito acquisita: immagine ' + correction)
            if learn_rules:
                from learning import distill
                if distill(record_path):
                    bot.say('Criterio generalizzabile salvato per i prompt successivi.')
        phase = bot.form_phase(frame)
        if not correction and record.get('feedback') and record.get('verification', '').startswith('Correzione esplicita visibile del sito:'):
            if prior and record.get('correct_choice') in ('1', '2') and record['correct_choice'] != prior:
                correction = record['correct_choice']
                bot.say('Riutilizzo la correzione del sito già salvata per questo esercizio.')
        if attempts and not correction:
            raise bot.Stop('Coppia già tentata senza una nuova correzione verificata; nessun reinvio.')
        if correction:
            choice = correction
        else:
            hints, references = bot.task_resources(frame, record_path)
            choice = bot.decide(prompt, images, task_guidance=stage_guidance,
                                contextual_hints=hints, references=references)
        if any(a['choice'] == choice and a['phase'] == phase for a in attempts):
            raise bot.Stop('La stessa risposta è già stata inviata in questa fase; nessun reinvio.')
        bot.check_stop()
        if frame.page.is_closed() or frame.is_detached():
            raise bot.Stop('Pagina dell’attività chiusa durante la valutazione; nessuna risposta inviata.')
        if bot.display_key(frame) != key:
            raise bot.Stop('Attività cambiata durante la valutazione; risposta non inviata.')
        bot.select_choice(frame, choice)
        frame.wait_for_function("() => {const b=document.querySelector('#submitBtn'); return b && !b.disabled}", timeout=15000)
        if bot.display_key(frame) != key:
            raise bot.Stop('Attività cambiata prima dell’invio; nessuna risposta inviata.')
        expired = frame.locator('#expirationModalOkBtn')
        if expired.count() and expired.is_visible():
            raise bot.Stop('Attività scaduta durante la valutazione; nessuna risposta inviata.')
        record = json.loads(record_path.read_text(encoding='utf-8'))
        record.setdefault('attempts', []).append({'choice': choice, 'phase': phase, 'accepted': None,
                                                'assignment': assignment, 'corrected': bool(correction), 'time': time.strftime('%Y-%m-%dT%H:%M:%S')})
        write_json(record_path, record)
        bot.set_pending(signature)
        bot.check_stop()
        frame.locator('#submitBtn').click(timeout=15000)
        bot.say('Formazione: inviata immagine ' + choice + (' dopo correzione esplicita.' if correction else '.'))
        last_document, idle_since = document, time.monotonic()
