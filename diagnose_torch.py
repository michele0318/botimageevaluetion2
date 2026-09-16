"""Read-only diagnostic for Windows torch DLL loading."""
import sys
import os
import faulthandler
faulthandler.dump_traceback_later(60)
def trace(frame,event,arg):
    if frame.f_code.co_name=='_load_dll_libraries':
        if event=='line' and frame.f_lineno==246:
            print('Loading',os.path.basename(frame.f_locals.get('dll','?')),flush=True)
        return trace
    return None
sys.settrace(trace)
import torch
sys.settrace(None)
faulthandler.cancel_dump_traceback_later()
print('Torch:',torch.__version__,'CUDA:',torch.cuda.is_available(),flush=True)
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0),flush=True)
    print((torch.ones(2,device='cuda')*2).cpu(),flush=True)
