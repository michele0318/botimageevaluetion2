import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from PIL import Image
import dataset_tools as data
import learning
import run_task_bot as bot

def picture(color):
    out=io.BytesIO(); Image.new('RGB',(100,100),color).save(out,format='PNG'); return out.getvalue()

with tempfile.TemporaryDirectory() as temporary:
    folder=Path(temporary)
    images=[picture('red'),picture('blue')]
    path=data.capture('Photograph of a frog on branches',images,folder)
    record=json.loads(path.read_text())
    record.update(correct_choice='1',verification='Visible site feedback',feedback='The branches underneath the frog look unnatural.',split='train')
    data.write_json(path,record)
    rule='When branches appear, inspect their connections for unnatural structure.'
    with patch.object(learning,'text_json',return_value={'rule':rule,'evidence':'branches underneath the frog look unnatural'}):
        assert learning.distill(path)
    with patch.object(learning,'records',side_effect=lambda: data.records(folder)):
        assert rule in learning.guidance('A bird on tree branches',split='train')
        with patch.object(bot.LOCAL_HTTP,'post') as post:
            post.return_value.json.return_value={'message':{'content':'{"choice":"2"}'}}
            assert bot.decide('A bird on tree branches',images,use_corrections=False,lesson_split='train')=='2'
            assert rule in post.call_args.kwargs['json']['messages'][1]['content']
            assert 'A bird on tree branches' in post.call_args.kwargs['json']['messages'][1]['content']
            assert post.call_args.kwargs['json']['format']['properties']['choice']['enum']==['1','2']
        record=json.loads(path.read_text()); record['split']='test'; data.write_json(path,record)
        assert not learning.guidance('A bird on tree branches',split='train')
    with patch.object(learning,'text_json',return_value={'choice':'1','evidence':'invented quote'}):
        assert learning.feedback_choice('Image 1 is better') is None
    with patch.object(learning,'text_json',return_value={'choice':'1','evidence':'Image 1 is better'}):
        assert learning.feedback_choice('Image 1 is better')=='1'
    changed=Image.open(io.BytesIO(images[0])); changed.putpixel((0,0),(254,0,0)); out=io.BytesIO(); changed.save(out,format='PNG')
    assert data.same_pixels(images[0],out.getvalue())
    assert not data.same_pixels(images[0],images[1])
print('PASS: verified feedback produces guidance used on NEW prompts; evidence checked; hold-out lessons excluded; screenshot noise tolerated')
