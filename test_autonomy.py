"""Autonomous training defaults and navigation isolation, using local fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock
from playwright.sync_api import sync_playwright
import run_task_bot as bot
from guided_training import can_auto_resume

assert can_auto_resume('exam','new',False,'You have completed 0/40 training tasks')
assert not can_auto_resume('exam','new',False,'You have completed 0/25 exam tasks')
assert not can_auto_resume('same','same',True,'You have completed 3/40 training tasks')
assert not can_auto_resume('old','new',True,'You have completed 3/40 training tasks Please take another look:')
assert can_auto_resume('old','new',True,'You have completed 4/40 training tasks')

class ReachedModel(Exception): pass
with TemporaryDirectory() as temp:
    with patch.object(bot,'STATE',Path(temp)), patch.object(bot.sys,'argv',['run_task_bot.py']), \
         patch.object(bot.socket,'socket',return_value=Mock()), \
         patch.object(bot,'ollama_check',side_effect=ReachedModel) as check, \
         patch.object(bot,'sync_playwright') as browser:
        try: bot.main()
        except ReachedModel: pass
        else: raise AssertionError('Default launch did not select automatic training')
        check.assert_called_once(); browser.assert_not_called()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context()
        visited=[]
        def route(request):
            url=request.request.url; visited.append(url)
            if url.endswith('/project'):
                html='<h1>'+bot.TITLE+'</h1><div><span>'+bot.TITLE+'</span></div>'
                # Exactly one title and button in the module card.
                html='<div><span>'+bot.TITLE+'</span><button onclick="document.body.innerHTML=\'<a target=_blank href=https://fixture.test/task>Open External Platform</a>\'">Start tasks</button></div>'
            else:
                html='<img id=img-1 alt=one style="width:10px;height:10px"><img id=img-2 alt=two style="width:10px;height:10px">'
            request.fulfill(body=html,content_type='text/html')
        context.route('https://fixture.test/**',route)
        unrelated=context.new_page()
        unrelated.set_content('<a target=_blank href=https://fixture.test/wrong>Open External Platform</a>')
        stale=context.new_page()
        stale.set_content('<img id=img-1><img id=img-2 style="width:10px;height:10px">')
        host=context.new_page()
        with patch.object(bot,'PROJECT','https://fixture.test/project'), patch.object(bot,'STATE',Path(temp)), \
             patch.object(bot,'save_session'):
            bot.open_tasks(context,host)
        assert any(url.endswith('/task') for url in visited)
        assert not any(url.endswith('/wrong') for url in visited)
        assert context.pages[-1].url=='https://fixture.test/task'
        host.close()
        assert bot.wait_browser(context,10)
        browser.close()
print('PASS: default automatic training; no exam autoresume; no same-task retry; isolated module navigation; closed host tab tolerated')
