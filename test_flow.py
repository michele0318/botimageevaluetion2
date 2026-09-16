"""Local browser regression checks. No connection to Mindrift or Ollama."""
import base64
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from playwright.sync_api import sync_playwright
import run_task_bot as bot
import dataset_tools as data
import guided_training as guided


def picture(color):
    buffer = io.BytesIO()
    Image.new('RGB', (32, 32), color).save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


html = f'''<div id="prompt-display">Red square</div>
<div><img id="img-1" src="{picture('red')}"><input type="radio" name="selected_image" value="0"></div>
<div><img id="img-2" src="{picture('blue')}"><input type="radio" name="selected_image" value="1"></div>
<input name="submit_after_hint" value="False" type="hidden">
<button id="submitBtn" onclick="send()">Submit</button>
<script>window.answers=[];function send() {{
 answers.push(document.querySelector('input:checked').value);
 document.querySelector('input:checked').checked=false;
 if(answers.length==1)document.querySelector('[name=submit_after_hint]').value='True';
 else if(answers.length==2){{document.querySelector('#prompt-display').textContent='Blue square';document.querySelector('[name=submit_after_hint]').value='False';}}
 else document.body.innerHTML='No tasks available';
}}</script>'''

with tempfile.TemporaryDirectory() as temporary, sync_playwright() as pw:
    with patch.object(bot, 'STATE', Path(temporary)), patch.object(bot, 'open_tasks'):
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        page.set_content('<iframe style="width:1350px;height:900px"></iframe>')
        frame = page.frames[1]
        normal_html = html.split('<script>')[0] + '''<script>window.answers=[];function send(){
        answers.push(document.querySelector('input:checked').value);
        document.querySelector('input:checked').checked=false;
        if(answers.length===1)document.querySelector('#prompt-display').textContent='Blue square';
        else document.body.innerHTML='No tasks available';}</script>'''
        frame.set_content(normal_html)
        with patch.object(bot, 'decide', side_effect=['1', '2']):
            bot.run(context, page, False)
        assert frame.evaluate('window.answers') == ['0', '1']
        print('PASS: both image controls, next task and exhaustion')
        frame.set_content(html.replace('Red square', 'Blue square'))
        with patch.object(bot, 'decide') as model:
            try:
                bot.run(context, page, False)
            except bot.Stop as error:
                assert 'gia inviato' in str(error)
            else:
                raise AssertionError('Duplicate submission allowed')
            model.assert_not_called()
        print('PASS: duplicate guard persists across runs within the same phase')
        (bot.STATE / 'pending.txt').unlink()
        with patch.object(bot, 'decide', return_value='2'):
            bot.run(context, page, True)
        assert frame.evaluate('window.answers') == []
        print('PASS: dry-run sends nothing')
        frame.set_content(html)
        with patch.object(bot, 'decide', return_value='1') as model:
            try:
                bot.run(context, page, False)
            except bot.Stop as error:
                assert 'gia inviato' in str(error)
            else:
                raise AssertionError('Repeated image pair was resubmitted after hints')
            assert model.call_count == 1
        assert frame.evaluate('window.answers') == ['0']
        print('PASS: same pair after hints is never automatically resubmitted')
        frame.set_content(html)
        folder = Path(temporary) / 'examples'
        actions = []
        pending_before = (bot.STATE / 'pending.txt').read_bytes()

        def human_actions():
            items = data.records(folder)
            if not frame.locator('#local-training-panel').count():
                return
            if not actions:
                frame.locator('#local-training-panel [data-answer="1"]').click()
                actions.append('first label')
            elif items and items[0][1]['correct_choice'] == '1' and len(actions) == 1:
                assert frame.evaluate('window.answers') == []
                frame.locator('#local-training-panel [data-answer="2"]').click()
                actions.append('correction')
            elif items and items[0][1]['correct_choice'] == '2':
                assert frame.evaluate('window.answers') == []
                assert len(items[0][1]['label_history']) == 2
                raise bot.Stop('Test complete')

        with patch.object(guided, 'capture', side_effect=lambda p, im: data.capture(p, im, folder)), \
             patch.object(bot, 'check_stop', side_effect=human_actions), \
             patch.object(bot, 'decide') as model:
            try:
                guided.run(context, page)
            except bot.Stop as error:
                assert str(error) == 'Test complete'
            model.assert_not_called()
        assert (bot.STATE / 'pending.txt').read_bytes() == pending_before
        print('PASS: guided collection and correction; no AI calls, no submissions, pending guard intact')
        first_path, first = data.records(folder)[0]
        images = [(first_path.parent / f'image_{i}.png').read_bytes() for i in (1, 2)]
        assert data.corrected_answer('Red square', images, folder) == '2'
        assert data.corrected_answer('Red square', images[::-1], folder) == '1'
        assert data.corrected_answer('Blue square', images, folder) is None
        with patch.object(data, 'corrected_answer', return_value='2'), patch.object(bot.LOCAL_HTTP, 'post') as inference:
            assert bot.decide('Red square', images) == '2'
            inference.assert_not_called()
        print('PASS: saved correction affects decisions, reverses correctly, uses no model call and respects the prompt')
        reverse = data.capture('Different prompt', images[::-1], folder)
        second = json.loads(reverse.read_text())
        assert first['split'] == second['split']
        assert second['correct_choice'] is None
        print('PASS: reversed image pairs stay in one split; new examples have no invented labels')
        page.screenshot(path=str(bot.ROOT / 'training_preview.png'))
        browser.close()
