"""Collect human-verified examples while the user works in the same browser."""
import json
import time
import re

from playwright.sync_api import Error as BrowserError
from dataset_tools import capture, write_json


PANEL = """({id, saved}) => {
 const old=document.getElementById('local-training-panel'); if(old)old.remove();
 const box=document.createElement('aside'); box.id='local-training-panel';
 box.style.cssText='position:fixed;top:12px;right:12px;z-index:2147483000;width:min(280px,calc(100vw - 60px));max-height:calc(100vh - 60px);overflow:auto;padding:14px;border:2px solid #287c56;border-radius:10px;background:#fff;color:#17251e;font:14px/1.4 sans-serif;box-shadow:0 3px 18px #0003';
 box.innerHTML='<details open><summary style="cursor:pointer;font-weight:bold">Training guidato · locale</summary><p>Il bot non sceglie e non invia. Usa il sito normalmente.</p><p>Solo quando hai verificato la risposta, salvala qui per questa coppia:</p><button type="button" data-answer="1">1 corretta</button> <button type="button" data-answer="2">2 corretta</button><p data-status></p><details><summary>Come funziona</summary>Le scelte salvate non vengono inviate al sito. Puoi correggere una scelta salvandone un’altra. Lascia senza risposta gli esempi dubbi. Chiudi il browser per terminare.</details></details>';
 box.querySelector('[data-status]').textContent=saved ? 'Risposta verificata salvata: '+saved : 'Esempio raccolto · risposta ancora da verificare';
 for(const button of box.querySelectorAll('[data-answer]')) {
  button.style.cssText='padding:8px;background:#e3f4e9;color:#142d20;border:1px solid #287c56;border-radius:5px;cursor:pointer';
  button.addEventListener('click',()=>{
   window.__localTrainingEvent={id,choice:button.dataset.answer};
   box.querySelector('[data-status]').textContent='Salvataggio in corso…';
  });
 }
 document.body.appendChild(box);
}"""


def save_label(path, choice):
    if choice not in ('1', '2'):
        raise ValueError('Scelta non valida')
    record = json.loads(path.read_text(encoding='utf-8'))
    history = record.setdefault('label_history', [])
    history.append({'previous': record['correct_choice'], 'choice': choice,
                    'time': time.strftime('%Y-%m-%dT%H:%M:%S')})
    record.update(correct_choice=choice, verification='Risposta dichiarata verificata dall’utente nel training guidato')
    write_json(path, record)


def can_auto_resume(paused_key, current_key, initially_training, text):
    return bool(re.search(r'completed\s+\d+/\d+\s+training tasks',text)
                and 'Please take another look:' not in text and 'You are right!' not in text
                and (not initially_training or current_key!=paused_key))


def run(context, page, open_project=True, auto_resume_training=False):
    import run_task_bot as bot
    bot.say('Training guidato: nessuna scelta o risposta automatica. Correggi gli esempi nel pannello verde.')
    if open_project:
        bot.open_tasks(context, page)
    paused_frame=bot.task_frame(context)
    paused_key=bot.display_key(paused_frame) if paused_frame else None
    initially_training=bool(paused_frame and re.search(r'completed\s+\d+/\d+\s+training tasks',bot.visible_text(paused_frame)))
    if auto_resume_training:
        bot.say('Ripresa automatica quando il sito mostra una nuova attivita di formazione; esame escluso.')
    active_key = active_frame = record_path = None
    while context.pages:
        bot.check_stop()
        resume = bot.STATE / 'resume-training.request'
        if resume.exists():
            resume.unlink()
            return True
        try:
            frame = bot.task_frame(context)
            if not frame:
                # The user handles site feedback/navigation. Keep the browser open.
                bot.wait_browser(context,500)
                continue
            key = bot.display_key(frame)
            if auto_resume_training and can_auto_resume(paused_key,key,initially_training,bot.visible_text(frame)):
                bot.say('Nuova formazione disponibile: riprendo automaticamente nella stessa finestra.')
                return True
            if frame != active_frame or key != active_key:
                if not key[0] or not key[1] or not key[2]:
                    frame.page.wait_for_timeout(300)
                    continue
                prompt, images, _ = bot.snapshot(frame)
                if bot.display_key(frame) != key:
                    continue
                record_path = capture(prompt, images)
                record = json.loads(record_path.read_text(encoding='utf-8'))
                visible = bot.visible_text(frame)
                for marker in ('Please take another look:', 'You are right!'):
                    if marker in visible:
                        record['observed_feedback'] = marker + visible.split(marker, 1)[1].split('You have completed', 1)[0].strip()
                        write_json(record_path, record)
                        break
                frame.evaluate(PANEL, {'id': record['id'], 'saved': record['correct_choice']})
                active_key, active_frame = key, frame
                bot.say('Esempio raccolto; attendo verifica umana. Totale e accuratezza: dataset_tools.py status.')
            event = frame.evaluate('() => {const e=window.__localTrainingEvent; window.__localTrainingEvent=null; return e}')
            if event and record_path and event.get('id') == record_path.parent.name:
                if bot.display_key(frame) != active_key:
                    bot.say('Pagina cambiata: correzione non associata alla nuova coppia.')
                    continue
                save_label(record_path, event['choice'])
                frame.locator('#local-training-panel [data-status]').evaluate(
                    '(e, choice) => e.textContent="Risposta verificata salvata: "+choice+". Nessun invio al sito."', event['choice'])
                bot.say('Correzione umana salvata: immagine ' + event['choice'])
            frame.page.wait_for_timeout(300)
        except BrowserError:
            if not context.pages:
                return
            # Frame replacement is normal on site navigation; never reload/reopen it.
            active_key = active_frame = None
            try:
                bot.wait_browser(context,1000)
            except BrowserError:
                return
