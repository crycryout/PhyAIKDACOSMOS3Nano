"""Request-local preparation of original UniPC coefficients on the same GPU."""
import collections
import contextlib
import torch

def p_coefficients(sigmas,si,order,device,dtype):
    sigma_t=sigmas[si+1].to(device)
    sigma_s0=sigmas[si].to(device)
    alpha_t,sigma_t=1.0-sigma_t,sigma_t
    alpha_s0,sigma_s0=1.0-sigma_s0,sigma_s0
    lambda_t=torch.log(alpha_t)-torch.log(sigma_t)
    lambda_s0=torch.log(alpha_s0)-torch.log(sigma_s0)
    h=lambda_t-lambda_s0
    rks=[]
    for i in range(1,order):
        sigma_i=sigmas[si-i].to(device)
        a_si,s_si=1.0-sigma_i,sigma_i
        lambda_si=torch.log(a_si)-torch.log(s_si)
        rks.append((lambda_si-lambda_s0)/h)
    hh=-h
    h_phi_1=torch.expm1(hh)
    b_h=torch.expm1(hh)
    rhos=torch.tensor([0.5],dtype=dtype,device=device) if order>1 else None
    return sigma_t/sigma_s0,alpha_t*h_phi_1,alpha_t*b_h,rks,rhos

def c_coefficients(sigmas,si,order,device,dtype):
    sigma_t=sigmas[si].to(device)
    sigma_s0=sigmas[si-1].to(device)
    alpha_t,sigma_t=1.0-sigma_t,sigma_t
    alpha_s0,sigma_s0=1.0-sigma_s0,sigma_s0
    lambda_t=torch.log(alpha_t)-torch.log(sigma_t)
    lambda_s0=torch.log(alpha_s0)-torch.log(sigma_s0)
    h=lambda_t-lambda_s0
    rks=[]
    for i in range(1,order):
        sigma_i=sigmas[si-(i+1)].to(device)
        a_si,s_si=1.0-sigma_i,sigma_i
        lambda_si=torch.log(a_si)-torch.log(s_si)
        rks.append((lambda_si-lambda_s0)/h)
    history_rks=list(rks)
    rks.append(torch.tensor(1.0,device=device))
    rks=torch.stack(rks).to(device)
    hh=-h
    h_phi_1=torch.expm1(hh)
    h_phi_k=h_phi_1/hh-1
    b_h=torch.expm1(hh)
    r_rows,b_rows=[],[]
    factorial_i=1
    for i in range(1,order+1):
        r_rows.append(torch.pow(rks,i-1))
        b_rows.append(h_phi_k*factorial_i/b_h)
        factorial_i*=i+1
        h_phi_k=h_phi_k/hh-1.0/factorial_i
    r_mat=torch.stack(r_rows)
    b_vec=torch.stack(b_rows).to(device)
    if order==1:
        rhos=torch.tensor([0.5],dtype=dtype,device=device)
    else:
        rhos=torch.linalg.solve(r_mat,b_vec).to(device=device,dtype=dtype)
    return sigma_t/sigma_s0,alpha_t*h_phi_1,alpha_t*b_h,history_rks,rhos

class SamplerResidency:
    def __init__(self):
        from phyai.models.cosmos3 import scheduler_cosmos3_policy
        self.owner=scheduler_cosmos3_policy
        self.original=self.owner.UniPCMultistepSampler
        self.stats=collections.Counter()
        self.active=False
    @contextlib.contextmanager
    def request(self,variant,dtype):
        assert variant in {"inherited","coefficients"}
        assert not self.active
        stats=self.stats
        stats.clear();stats["request_contexts"]=1
        if variant=="inherited":
            yield
            return
        original=self.original
        cache={}
        class PreparedSampler(original):
            def set_timesteps(self,num_inference_steps,device=None):
                super().set_timesteps(num_inference_steps,device=device)
                assert self.solver_order==2 and self.predict_x0 and self.solver_type=="bh2"
                key=(tuple(self.sigmas.tolist()),int(num_inference_steps),self.solver_order,
                     self.lower_order_final,str(device),str(dtype))
                self.sigmas=self.sigmas.to(device)
                stats["sigma_table_uploads"]+=1
                if key in cache:
                    self._prepared_p,self._prepared_c=cache[key]
                    stats["coefficient_cache_hits"]+=1
                else:
                    ps,cs=[],[]
                    previous_order=0
                    for si in range(int(num_inference_steps)):
                        cs.append(c_coefficients(self.sigmas,si,previous_order,device,dtype) if si>0 else None)
                        order=min(self.solver_order,num_inference_steps-si) if self.lower_order_final else self.solver_order
                        order=min(order,si+1)
                        ps.append(p_coefficients(self.sigmas,si,order,device,dtype))
                        previous_order=order
                    self._prepared_p,self._prepared_c=ps,cs
                    cache[key]=(ps,cs)
                    stats["coefficient_builds"]+=1
            def step(self,model_output,timestep,sample):
                assert sample.dtype==dtype and sample.device==self.sigmas.device
                stats["solver_steps"]+=1
                return super().step(model_output,timestep,sample)
            def _p_update(self,sample,order):
                stats["coefficient_p_updates"]+=1
                m0=self.model_outputs[-1]
                ratio,first,second,rks,rhos=self._prepared_p[self._step_index]
                assert len(rks)==order-1
                d1s=[(self.model_outputs[-(i+1)]-m0)/rk for i,rk in enumerate(rks,1)]
                d1s_t=torch.stack(d1s,dim=1) if d1s else None
                x_t=ratio*sample-first*m0
                if d1s_t is not None:
                    pred_res=torch.einsum("k,bkc...->bc...",rhos,d1s_t)
                    x_t=x_t-second*pred_res
                return x_t.to(sample.dtype)
            def _c_update(self,this_model_output,last_sample,this_sample,order):
                stats["coefficient_c_updates"]+=1
                m0=self.model_outputs[-1]
                ratio,first,second,rks,rhos=self._prepared_c[self._step_index]
                assert len(rks)==order-1
                d1s=[(self.model_outputs[-(i+1)]-m0)/rk for i,rk in enumerate(rks,1)]
                d1s_t=torch.stack(d1s,dim=1) if d1s else None
                x_t=ratio*last_sample-first*m0
                corr_res=torch.einsum("k,bkc...->bc...",rhos[:-1],d1s_t) if d1s_t is not None else 0.0
                d1_t=this_model_output-m0
                x_t=x_t-second*(corr_res+rhos[-1]*d1_t)
                return x_t.to(this_sample.dtype)
        assert self.owner.UniPCMultistepSampler is original
        self.active=True
        self.owner.UniPCMultistepSampler=PreparedSampler
        try:
            yield
        finally:
            self.owner.UniPCMultistepSampler=original
            self.active=False
            cache.clear()
