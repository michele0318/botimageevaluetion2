"""End-to-end feedback learning with an isolated local HTTP training fixture."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
from pathlib import Path
import tempfile
from threading import Thread
from unittest.mock import patch
from urllib.parse import parse_qs

from PIL import Image
from playwright.sync_api import sync_playwright
import dataset_tools as data
import run_task_bot as bot
import site_feedback
import training_loop


def image(color):
    buffer = io.BytesIO()
    Image.new('RGB', (100, 100), color).save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


class Site(BaseHTTPRequestHandler):
    answers = []
    stage_accepted = False
    def log_message(self, *_): pass
    def do_GET(self):
        self.render(2 if self.path == '/next' else 1)
    def do_POST(self):
        form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
        task, choice = int(form['task'][0]), form['selected_image'][0]
        if task == 2:
            Site.stage_accepted = form.get('stage_ok') == ['1']
        self.answers.append(choice)
        self.render(task, choice == str(task), True)
    def render(self, task, correct=False, feedback=False):
        message = ('You are right! ' if correct else 'Please take another look: ') if feedback else ''
        if feedback: message += f'Image {task} stands out as the superior choice.'
        controls = '<a href="/next">To the next task!</a>' if correct else '<button id="submitBtn">Submit</button>'
        modal = '''<div class="modal show" style="position:fixed;inset:0;background:white;z-index:9999"><h2>Stage Update</h2><p>Now focus on prompt relevance.</p><button type="button" onclick="document.querySelector('[name=stage_ok]').value='1';this.parentNode.remove()">OK</button></div>''' if task == 2 and not feedback else ''
        progress = '0/25 exam tasks' if task == 2 and correct else f'{task if correct else task-1}/2 training tasks'
        page = f'''<body><p>{message}</p><p>You have completed {progress}</p>
        {modal}
        <div id="prompt-display">{'Red' if task == 1 else 'Blue'} square</div>
        <form method="post"><input name="task" value="{task}" type="hidden">
        <input name="stage_ok" value="0" type="hidden">
        <input name="submit_after_hint" value="{'True' if feedback else 'False'}" type="hidden">
        <div><img id="img-1" src="{image('red')}"><input name="selected_image" type="radio" value="1"></div>
        <div><img id="img-2" src="{image('blue')}"><input name="selected_image" type="radio" value="2"></div>
        {controls}</form></body>'''.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(page)))
        self.end_headers()
        self.wfile.write(page)


assert site_feedback.correct_choice('Please take another look: Image 1 stands out as the superior choice. Image 2 has artifacts.') == '1'
assert site_feedback.correct_choice('Please take another look: compare Image 1 and Image 2.') is None
assert site_feedback.correct_choice('The image says: Image 1 stands out as the superior choice.') is None
assert site_feedback.correct_choice('Please take another look: Image 1 has fewer artifacts with the banknotes and obtrusive text. The second image wins.') == '2'
assert site_feedback.correct_choice('Please take another look: The first image wins.') == '1'
assert site_feedback.correct_choice('Please take another look: Image 1 is better. The second image wins.') is None

with tempfile.TemporaryDirectory() as temporary:
    folder = Path(temporary)
    rejection = folder / 'rejection.json'
    data.write_json(rejection, {'correct_choice': None})
    assert site_feedback.learn(rejection, 'Please take another look: Image 1 has a critical flaw.', wrong_choice='1') is None
    assert site_feedback.learn(rejection, 'Please take another look: Image 1 has a critical flaw.', wrong_choice='1', binary_rejection=True) == '2'
    assert site_feedback.learn(rejection, 'You are right! Image 2 is better.', accepted_choice='1') is None
    import json
    assert not json.loads(rejection.read_text())['verification']
    server = ThreadingHTTPServer(('127.0.0.1', 0), Site)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            def open_local(c, p):
                p.goto(f'http://127.0.0.1:{server.server_port}/')
            with patch.object(bot, 'STATE', folder), patch.object(bot, 'open_tasks', side_effect=open_local), \
                 patch.object(training_loop, 'capture', side_effect=lambda p, im: data.capture(p, im, folder/'examples')), \
                 patch.object(bot, 'decide', side_effect=['2', '2']) as model:
                try:
                    training_loop.run(context, page, learn_rules=False)
                except bot.Stop as error:
                    assert 'Formazione completata' in str(error), str(error)
                else:
                    raise AssertionError('Completion not detected')
                assert model.call_count == 2, 'Correction must not repeat the failed model call'
            assert Site.answers == ['2', '1', '2'], Site.answers
            assert Site.stage_accepted
            saved = data.records(folder/'examples')
            assert len(saved) == 2
            assert {r['prompt']: r['correct_choice'] for _, r in saved} == {'Red square': '1', 'Blue square': '2'}
            assert all(r['attempts'][-1]['accepted'] for _, r in saved)
            for scenario in ('expired', 'closed'):
                probe = context.new_page()
                before = list(Site.answers)
                def interrupted_decision(*args, **kwargs):
                    if scenario == 'closed':
                        probe.close()
                    else:
                        probe.evaluate("document.body.insertAdjacentHTML('beforeend', '<button id=expirationModalOkBtn>Expired</button>')")
                    return '1'
                with patch.object(bot, 'STATE', folder), patch.object(bot, 'open_tasks', side_effect=open_local), \
                     patch.object(training_loop, 'capture', side_effect=lambda p, im: data.capture(p, im, folder/scenario)), \
                     patch.object(bot, 'decide', side_effect=interrupted_decision):
                    try:
                        training_loop.run(context, probe, learn_rules=False)
                    except bot.Stop as error:
                        assert ('chiusa' if scenario == 'closed' else 'scaduta') in str(error), str(error)
                    else:
                        raise AssertionError('Interrupted task must stop')
                assert Site.answers == before, 'Must not submit after expiration or closure'
                assert all(not r.get('attempts') for _, r in data.records(folder/scenario))
                if not probe.is_closed():
                    probe.close()
            browser.close()
        print('PASS: wrong answer -> explicit feedback -> saved correction -> correct answer -> next task -> completion')
        print('PASS: ambiguous feedback is not a label; accepted answers saved; no repeated inference after correction')
    finally:
        server.shutdown()
        server.server_close()
