"""Exercise true original PhyAI CUDA Graph before installing the candidate."""
from dynamic_model_common_v4 import *
import traceback

a=parser().parse_args()
assert a.cuda_graph
engine,vae,vae_runner,counts=setup(a)
runner=engine.entry.scheduler.runner
control=None
report=dict(complete=False,gate_passed=False,oracle="original official CUDA Graph before any candidate installation",rows=[])
try:
    from phyai.models.cosmos3 import Cosmos3ActionRequest,pixel_to_latent_shape
    rng=torch.Generator(device="cuda").manual_seed(615)
    pixels=torch.rand(1,3,5,128,192,device="cuda",dtype=torch.bfloat16,generator=rng)*2-1
    rows=[]
    for name,p,n in [("graph_len11_7",11,7),("graph_len33_19",33,19)]:
        ti=(torch.arange(p,device="cuda",dtype=torch.long)+100).unsqueeze(0)
        ni=(torch.arange(n,device="cuda",dtype=torch.long)+291).unsqueeze(0)
        req=Cosmos3ActionRequest(text_ids=ti,text_mask=torch.ones_like(ti),
            neg_text_ids=ni,neg_text_mask=torch.ones_like(ni),
            video_shape=pixel_to_latent_shape(5,128,192),mode="policy",domain_id=8,
            action_chunk=8,raw_action_dim=10,action_dim=64,fps=15.,
            num_inference_steps=a.steps,guidance_scale=3.,seed=42,cond_frame_indexes=(0,))
        rows.append((name,req))
    refs={}
    for mode in ("original_graph","candidate_official_graph_fallback"):
        if mode.startswith("candidate"):
            runner.invalidate_cache()
            control=install(engine,vae)
        for name,req in rows:
            idle();torch.cuda.synchronize();counts.clear()
            if control is None:
                latent=vae_runner.encode(pixels)
                value=engine.step(dataclasses.replace(req,cond_video_latents=latent))
            else:
                value=control.full(pixels,req,vae_runner,engine)
            torch.cuda.synchronize()
            graph_rows={key:dict(captures=g.num_captures,replays=g.num_replays,
                                  graph_live=g.graph is not None)
                        for key,g in runner._graphs.items()}
            if control is None:
                assert set(graph_rows)=={"cond","uncond"},graph_rows
                assert all(r["captures"]>=1 and r["replays"]>=a.steps for r in graph_rows.values()),graph_rows
                refs[name]=value.detach().clone()
                exact=True
            else:
                exact=bool(torch.equal(refs[name].contiguous().view(torch.uint8),value.contiguous().view(torch.uint8)))
                assert exact,(name,action_hash(refs[name]),action_hash(value))
                assert control.last_request_stats["dynamic"]["reason"]=="official_cuda_graph",control.last_request_stats
                # Control restores candidate mode and releases the official graphs.
                assert not runner._graphs
            assert counts["vae_encode"]==1 and counts["engine_step"]==1,counts
            assert value.dtype==torch.bfloat16 and torch.isfinite(value).all()
            assert list(value.shape)==[1,8,10]
            outpath=a.out/"actions"/(mode+"-"+name+".pt")
            outpath.parent.mkdir(parents=True,exist_ok=True)
            torch.save(value.cpu(),outpath)
            record=dict(mode=mode,case=name,positive_length=req.text_ids.shape[1],
                        negative_length=req.neg_text_ids.shape[1],byte_equal=exact,
                        action_sha256=action_hash(value),phase_counts=dict(counts),graphs_after_request=graph_rows,
                        optimization=None if control is None else control.last_request_stats)
            report["rows"].append(record);save(a.out/"graph-fallback-validation.json",report)
            emit("graph_validation",**record)
    report.update(complete=True,gate_passed=True)
    save(a.out/"graph-fallback-validation.json",report)
except Exception as exc:
    report.update(error=repr(exc),traceback=traceback.format_exc())
    save(a.out/"graph-fallback-validation.json",report)
    raise
finally:
    if control is not None:control.close()
    engine.close()
