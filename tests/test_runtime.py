"""Only project-owned teaching model executed. Input scope recorded in report."""
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def test_cpu_teaching_runtime():
    torch=pytest.importorskip('torch',reason='未安装可选 PyTorch CPU，运行验证未完成')
    from examples.mini_decoder import MiniDecoder, Attention
    import inspect
    source_lines, first_line=inspect.getsourcelines(Attention.forward)
    before_repeat_line=first_line+next(i for i,line in enumerate(source_lines) if 'k = k.repeat_interleave' in line)
    records=[]
    counts=[]
    for name in ['mha','gqa']:
        torch.manual_seed(2026)
        c=json.loads((ROOT/f'examples/configs/{name}.json').read_text())
        model=MiniDecoder(c).eval().float()
        shapes={};handles=[]
        for key in ['q_proj','k_proj','v_proj']:
            handles.append(getattr(model.blocks[0].attention,key).register_forward_hook(lambda m,i,o,k=key:shapes.update({k:list(o.shape)})))
        tokens=torch.randint(0,128,(2,4))
        with torch.no_grad(): logits=model(tokens)
        for h in handles:h.remove()
        assert list(logits.shape)==[2,4,128]
        assert shapes['q_proj']==[2,4,64]
        assert shapes['k_proj']==[2,4,64 if name=='mha' else 16]
        assert shapes['v_proj']==shapes['k_proj']
        # Observe reshape/repeat at source execution lines, separate from static data.
        import sys
        observed={}
        def tracer(frame,event,arg):
            if frame.f_code.co_name=='forward' and frame.f_code.co_filename.endswith('mini_decoder.py') and 'scores' in frame.f_locals and 'q' in frame.f_locals:
                observed['after_repeat']=list(frame.f_locals['k'].shape)
                observed['after_repeat_v']=list(frame.f_locals['v'].shape)
            if frame.f_code.co_name=='forward' and frame.f_code.co_filename.endswith('mini_decoder.py') and frame.f_lineno==before_repeat_line:
                observed['before_repeat']=list(frame.f_locals['k'].shape)
                observed['before_repeat_v']=list(frame.f_locals['v'].shape)
            return tracer
        sys.settrace(tracer)
        try:
            with torch.no_grad(): model(tokens)
        finally:sys.settrace(None)
        assert observed['before_repeat']==[2,c['num_key_value_heads'],4,8]
        assert observed['after_repeat']==[2,8,4,8]
        assert observed['before_repeat_v']==observed['before_repeat']
        assert observed['after_repeat_v']==observed['after_repeat']
        count=sum(p.numel() for p in model.parameters());counts.append(count)
        kv_count=model.blocks[0].attention.k_proj.weight.numel()+model.blocks[0].attention.v_proj.weight.numel()
        assert count==json.loads((ROOT/f'build/{name}.architecture.json').read_text())['snapshot']['parameterCount']
        records.append(dict(kvProjectionParametersPerLayer=kv_count,model=name,output=list(logits.shape),projections=shapes,kv=observed,parameters=count))
    assert counts[0]-counts[1]==12288
    assert records[0]['kvProjectionParametersPerLayer']-records[1]['kvProjectionParametersPerLayer']==6144
    (ROOT/'build/runtime_observations.json').write_text(json.dumps(dict(kind='runtime-test-report',torchVersion=torch.__version__,device='cpu',dtype='float32',seed=2026,input=[2,4],mode='eval',scope='项目自带教学模型；不代表分析器执行过目标源码',records=records),ensure_ascii=False,indent=2))
