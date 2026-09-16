"""Prepare visual teaching examples using original site captions, not model labels."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps
from dataset_tools import write_json, records

root=Path(__file__).resolve().parent/'site_material'
output=root/'teaching'
output.mkdir(exist_ok=True)
manifest=json.loads((root/'image_manifest.json').read_text(encoding='utf-8'))
by_url={r['source']:r for r in manifest}
test_hashes=set()
for path,record in records():
    if record.get('split')=='test':
        for i in (1,2):
            with Image.open(path.parent/f'image_{i}.png') as im:
                test_hashes.add(hashlib.sha256(im.convert('RGB').tobytes()).hexdigest())
valid={}
failed=[]
for entry in manifest:
    try:
        with Image.open(root/entry['file']) as im:
            image=ImageOps.exif_transpose(im).convert('RGB')
            pixel_hash=hashlib.sha256(image.tobytes()).hexdigest()
            if pixel_hash in test_hashes:
                continue
            name=entry['sha256']+'.png'
            image.save(output/name)
            valid[entry['source']]=name
    except (OSError,ValueError):
        failed.append(entry['file'])
examples=[]
for path in sorted((root/'articles').glob('*.json')):
    item=json.loads(path.read_text(encoding='utf-8'))
    for index,figure in enumerate(item['figures']):
        caption=figure['caption'].strip()
        urls=[image['src'] for image in figure['images']]
        if not urls or any(url not in valid for url in urls) or len(caption.split())<15:
            continue
        examples.append({'id':path.stem+'-'+str(index),'source':item['url'],
                         'images':[valid[url] for url in urls],
                         'instruction':'Explain the visual construction and teaching point illustrated here. Topic: '+item['title'],
                         'answer':caption,'label_source':'original_site_figure_caption',
                         'purpose':'visual_instruction_training_only_not_an_independent_test'})
write_json(output/'examples.json',examples)
write_json(output/'audit.json',{'archived_images':len(manifest),'decoded_images':len(valid),
                              'invalid_or_unsupported':failed,'teaching_examples':len(examples),
                              'exact_test_image_pixels_excluded':True,
                              'weights_trained':False})
print(f'{len(valid)}/{len(manifest)} images decoded; {len(examples)} original visual teaching examples prepared; {len(failed)} unsupported images.')
