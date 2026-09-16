"""Local experimental image ranking. Does not open Mindrift or submit answers."""
import argparse
from pathlib import Path
import torch
import train_ranker as ranker

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prompt_file',type=Path)
    parser.add_argument('image_1',type=Path)
    parser.add_argument('image_2',type=Path)
    args=parser.parse_args()
    torch.set_num_threads(4)
    adapter=torch.load(ranker.OUT/'adapter.pt',weights_only=True)
    if adapter['version']!=ranker.VERSION: raise ValueError('Incompatible adapter')
    if adapter['fingerprint']!=ranker.fingerprint(ranker.verified()):
        raise ValueError('Verified examples changed: retrain before using this adapter')
    model=ranker.load_model()
    f,base,original,tokens,chunks=ranker.features(model,args.prompt_file.read_text(encoding='utf-8'),[args.image_1,args.image_2])
    margin=float(base[0]-base[1]+((f[0]-f[1]).double()/adapter['scale'])@adapter['weights'])
    print(f'Baseline: Image {1 if base[0]>base[1] else 2}; adapted: Image {1 if margin>0 else 2}')
    print(f'Prompt: {tokens} tokens in {chunks} chunks. Score difference: {margin:.4f}')
    print('Experimental suggestion only; score difference is NOT a calibrated probability.')
