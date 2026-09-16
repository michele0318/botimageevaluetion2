"""Exercise source retrieval and contextual reference images without site submissions."""
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from playwright.sync_api import sync_playwright
import run_task_bot as bot
from site_knowledge import guidance

def png(color):
    stream=io.BytesIO()
    Image.new('RGB',(100,100),color).save(stream,format='PNG')
    return stream.getvalue()

with tempfile.TemporaryDirectory() as temporary:
    folder=Path(temporary)
    (folder/'light.json').write_text(json.dumps({'title':'Light direction','rules':[{'rule':'For sunlight, shadow directions must agree.'}]}))
    (folder/'type.json').write_text(json.dumps({'title':'Typography','rules':[{'rule':'For poster typography, preserve readable lettering.'}]}))
    assert 'readable lettering' in guidance('poster typography',folder)
    assert 'shadow directions' not in guidance('poster typography',folder)
    assert not guidance('unrelated zebra',folder)
    assert len(guidance('poster typography',folder,budget=20)) == 0
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page()
        page.set_content('''<div id=prompt-display><span class=prompt-anchor>Example logo</span></div>
          <div id=hints-list><div class=hint-card><div class=hint-query>Example logo</div>
          <div class=hint-images><button class=hint-image-link><img></button><button class=hint-image-link><img></button></div>
          <div class=hint-reasoning>Compare the lettering with these references.</div></div></div>''')
        with patch.object(bot,'image_bytes',side_effect=[png('red'),png('blue')]):
            hints,refs=bot.task_resources(page.main_frame)
        assert len(refs)==2 and 'Compare the lettering' in hints
        assert all(r['label']=='Example logo' for r in refs)
        raw=bot.comparison_image([png('green'),png('yellow')],refs)
        sheet=Image.open(io.BytesIO(raw))
        assert sheet.width*sheet.height <= 1_705_000
        browser.close()
print('PASS: relevant grounded rules retrieved; all hint images collected; reference sheet bounded.')
