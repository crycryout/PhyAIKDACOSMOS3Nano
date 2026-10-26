"""Validate runtime attention tails, bounded cache and true official fallback."""
from types import SimpleNamespace
import torch
from phyai.layers.attention.enums import AttnLayout,AttnMode

def validate(control,out,save):
    compact=control.compact
    original=compact.official_forwards[0]
    fast=compact.bindings[0][2]
    generator=torch.Generator(device="cuda").manual_seed(913)
    doc=dict(complete=False,rows=[],fallbacks=[],max_plans=compact.max_plans)
    for nq,nk in [(1,1),(31,17),(63,64),(64,65),(65,129),(127,191),(128,257),(129,513),(257,319),(3542,3543),(3542,3573),(1472,1505)]:
        q=torch.randn(1,nq,32,128,device="cuda",dtype=torch.bfloat16,generator=generator)
        k=torch.randn(1,nk,8,128,device="cuda",dtype=torch.bfloat16,generator=generator)
        v=torch.randn(k.shape,device="cuda",dtype=torch.bfloat16,generator=generator)
        ref=original(q,k,v)
        got=fast(q,k,v)
        torch.cuda.synchronize()
        exact=bool(torch.equal(ref.contiguous().view(torch.uint8),got.contiguous().view(torch.uint8)))
        delta=ref.float()-got.float()
        row=dict(q=nq,kv=nk,byte_equal=exact,max_abs=float(delta.abs().max()),
                 relative_l2=float(delta.norm()/ref.float().norm().clamp_min(1e-12)),plan_entries=len(compact.plans))
        doc["rows"].append(row);save(out/"attention-dynamic-validation.json",doc)
        assert exact,("Attention BF16 byte gate",row)
        assert len(compact.plans)<=compact.max_plans
    sentinel=object()
    seen=[]
    def spy(q,k,v,ctx=None):
        seen.append((q,k,v,ctx));return sentinel
    compact.official_forwards[0]=spy
    try:
        q=torch.empty(1,65,32,128,device="cuda",dtype=torch.bfloat16)
        k=torch.empty(1,79,8,128,device="cuda",dtype=torch.bfloat16);v=torch.empty_like(k)
        context=SimpleNamespace(mask=object(),layout=AttnLayout.PADDED_4D,mode=AttnMode.PREFILL,
                                cu_seqlens_q=None,cu_seqlens_kv=None)
        checks=[("custom_mask",q,k,v,context),("batch2",q.expand(2,-1,-1,-1),k.expand(2,-1,-1,-1),v.expand(2,-1,-1,-1),None),
                ("dtype",q.float(),k.float(),v.float(),None),
                ("nonunit_dim_stride",torch.empty(1,65,32,256,device="cuda",dtype=torch.bfloat16)[...,::2],k,v,None)]
        for name,qq,kk,vv,ctx in checks:
            before=len(seen)
            assert fast(qq,kk,vv,ctx) is sentinel
            assert len(seen)==before+1 and seen[-1][0] is qq and seen[-1][3] is ctx
            doc["fallbacks"].append(dict(case=name,called_original_official=True))
    finally:
        compact.official_forwards[0]=original
    doc.update(complete=True,cache_stats=dict(compact.stats),final_entries=len(compact.plans))
    save(out/"attention-dynamic-validation.json",doc)
    compact.clear()
