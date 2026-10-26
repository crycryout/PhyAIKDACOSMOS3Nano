"""Experimental M3542 GEN route choices; all other shapes keep frozen dynamic V3."""
import collections,ctypes,json
import torch
class MainGemmRoutes:
    def __init__(self,linear,selected=None):
        self.linear=linear;self.original=list(linear.bindings);self.stats=collections.Counter()
        self.selected=selected or {};self.active={};self.variant="inherited"
        categories=set()
        replacement=[]
        for mod,frozen,fast in self.original:
            weight=fast.__defaults__[1];category=fast.__defaults__[2];categories.add(category)
            def route(x,_fast=fast,_b=weight,_category=category):
                spec=self.active.get(_category)
                if spec is None or x.ndim<2 or not x.is_cuda or x.dtype!=torch.bfloat16 or x.shape[-1]!=_b.shape[0]:
                    return _fast(x)
                aa=x.reshape(-1,x.shape[-1])
                if aa.shape[0]!=3542 or aa.stride(-1)!=1 or aa.stride(0)!=aa.shape[1]:
                    return _fast(x)
                if spec.get("shape") is not None and list(spec["shape"])!=[aa.shape[0],_b.shape[1],aa.shape[1]]:
                    self.stats["manifest_guard_fallback"]+=1;return _fast(x)
                if spec["method"]=="torch_mm":
                    value=torch.mm(aa,_b)
                else:
                    assert spec["method"]=="lt"
                    stream=torch.cuda.current_stream(aa.device).cuda_stream
                    signature=json.dumps(spec["attrs"],sort_keys=True)
                    key=(tuple(aa.shape),tuple(_b.shape),tuple(_b.stride()),aa.device.index,stream,"main_full_cfg_v1/"+_category+"/"+signature)
                    if key not in linear.plans:
                        wskey=(aa.device.index,stream)
                        if wskey not in linear.workspaces:linear.workspaces[wskey]=torch.empty(64*1024*1024,device=aa.device,dtype=torch.uint8)
                        ws=linear.workspaces[wskey]
                        plan=linear.lib.lt_make(aa.shape[0],_b.shape[1],aa.shape[1],int(_b.stride(-1)==1),ws.numel(),1)
                        attrs=(ctypes.c_int*9)(*[spec["attrs"][str(i)] for i in range(9)])
                        index=linear.lib.lt_configure(plan,attrs,ws.numel())
                        if index<0:
                            linear.lib.lt_free(plan);self.stats["configuration_fallback"]+=1;return _fast(x)
                        linear.plans[key]=(plan,index,ws);self.stats["plan_miss"]+=1
                    plan,index,ws=linear.plans[key]
                    value=torch.empty((aa.shape[0],_b.shape[1]),device=aa.device,dtype=aa.dtype)
                    rc=linear.lib.lt_run(plan,index,aa.data_ptr(),_b.data_ptr(),value.data_ptr(),ws.data_ptr(),ws.numel(),stream)
                    assert rc==0,(_category,rc)
                linear.calls+=1;self.stats[spec["method"]+"/"+_category]+=1;self.stats["dispatch"]+=1
                return value.reshape(*x.shape[:-1],_b.shape[1]),None
            replacement.append((mod,frozen,route))
        self.categories=sorted(categories);linear.bindings=replacement
    def set_variant(self,label):
        self.variant=label
        if label=="inherited":self.active={}
        elif label=="torch_all":self.active={c:dict(method="torch_mm") for c in self.categories}
        elif label.startswith("torch:"):self.active={label.split(":",1)[1]:dict(method="torch_mm")}
        elif label=="selected_all":self.active=dict(self.selected)
        elif label.startswith("selected:"):
            category=label.split(":",1)[1];self.active={category:self.selected[category]} if category in self.selected else {}
        else:raise ValueError(label)
    def close(self):
        self.active={};self.linear.bindings=self.original
