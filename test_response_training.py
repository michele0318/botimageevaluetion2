import io
from unittest.mock import Mock
from PIL import Image
import response_training as r

assert r.stage('You have completed 0/40 training tasks')==(0,40,'training')
assert r.stage('You have completed 0/30 exam tasks')==(0,30,'exam')
assert r.stage('unknown') is None
def png(color):
    out=io.BytesIO(); Image.new('RGB',(800,600),color).save(out,format='PNG'); return out.getvalue()
sheet=Image.open(io.BytesIO(r.sheet([png('red'),png('blue')],[png('green'),png('yellow')])))
assert sheet.width*sheet.height<=2_000_000
page=Mock(); page.locator.return_value.input_value.return_value='changed'
try: r.submit(page,'original','both')
except RuntimeError: pass
else: raise AssertionError('Stale assignment submitted')
page.locator.return_value.click.assert_not_called()
print('PASS: stage detection, originals included, bounded image size, stale submission blocked')
