"""Compare a changing random velocity sequence against the pinned original solver."""
import torch

def validate(residency,out,save):
    gen=torch.Generator(device="cuda").manual_seed(19273)
    rows=[]
    for n,karras,shift in [(1,False,5.),(2,False,5.),(4,False,5.),(5,False,1.),(8,False,5.),(4,True,5.)]:
        originals=[residency.original(flow_shift=shift,use_karras_sigmas=karras) for _ in range(2)]
        for obj in originals:obj.set_timesteps(n,device="cuda")
        with residency.request("coefficients",torch.bfloat16):
            prepared=[residency.owner.UniPCMultistepSampler(flow_shift=shift,use_karras_sigmas=karras) for _ in range(2)]
            for obj in prepared:obj.set_timesteps(n,device="cuda")
            left=[torch.randn(shape,device="cuda",dtype=torch.bfloat16,generator=gen) for shape in [(2,17,64),(1,3,4,5,6)]]
            right=[x.clone() for x in left]
            for si in range(n):
                for j in range(2):
                    velocity=torch.randn(left[j].shape,device="cuda",dtype=torch.bfloat16,generator=gen)*0.125
                    left[j]=originals[j].step(velocity,originals[j].timesteps[si],left[j])
                    right[j]=prepared[j].step(velocity,prepared[j].timesteps[si],right[j])
                    equal=bool(torch.equal(left[j].contiguous().view(torch.uint8),right[j].contiguous().view(torch.uint8)))
                    rows.append(dict(steps=n,karras=karras,flow_shift=shift,step=si,sample=j,shape=list(left[j].shape),byte_equal=equal))
                    save(out/"solver-random-sequence-gate.json",dict(complete=False,rows=rows))
                    assert equal,rows[-1]
            assert residency.stats["coefficient_builds"]==1 and residency.stats["coefficient_cache_hits"]==1
    save(out/"solver-random-sequence-gate.json",dict(complete=True,gate_passed=True,rows=rows))
