#include <cublasLt.h>
#include <cuda_runtime_api.h>
#include <vector>
#include <cstdint>
#include <cstring>
struct Plan {
 cublasLtHandle_t h; cublasLtMatmulDesc_t op;
 cublasLtMatrixLayout_t a,b,c;
 std::vector<cublasLtMatmulHeuristicResult_t> alg;
 int error=0;
};
extern "C" void* lt_make(int m,int n,int k,int b_row,size_t ws,int limit) {
 Plan* p=new Plan; cublasLtCreate(&p->h);
 cublasLtMatmulDescCreate(&p->op,CUBLAS_COMPUTE_32F,CUDA_R_32F);
 cublasLtMatrixLayoutCreate(&p->a,CUDA_R_16BF,m,k,k);
 cublasLtMatrixLayoutCreate(&p->b,CUDA_R_16BF,k,n,b_row?n:k);
 cublasLtMatrixLayoutCreate(&p->c,CUDA_R_16BF,m,n,n);
 cublasLtOrder_t row=CUBLASLT_ORDER_ROW,col=CUBLASLT_ORDER_COL;
 cublasLtMatrixLayoutSetAttribute(p->a,CUBLASLT_MATRIX_LAYOUT_ORDER,&row,sizeof(row));
 cublasLtMatrixLayoutSetAttribute(p->b,CUBLASLT_MATRIX_LAYOUT_ORDER,b_row?&row:&col,sizeof(row));
 cublasLtMatrixLayoutSetAttribute(p->c,CUBLASLT_MATRIX_LAYOUT_ORDER,&row,sizeof(row));
 cublasLtMatmulPreference_t pref;cublasLtMatmulPreferenceCreate(&pref);
 cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,&ws,sizeof(ws));
 p->alg.resize(limit);int got=0;
 p->error=cublasLtMatmulAlgoGetHeuristic(p->h,p->op,p->a,p->b,p->c,p->c,pref,limit,p->alg.data(),&got);
 p->alg.resize(got);cublasLtMatmulPreferenceDestroy(pref);return p;
}
extern "C" int lt_count(void* ptr){return ((Plan*)ptr)->alg.size();}
extern "C" int lt_error(void* ptr){return ((Plan*)ptr)->error;}
extern "C" int lt_attr(void* ptr,int i,int attr) {
 auto* p=(Plan*)ptr;int v=-999;size_t written=0;
 cublasLtMatmulAlgoConfigGetAttribute(&p->alg.at(i).algo,(cublasLtMatmulAlgoConfigAttributes_t)attr,&v,sizeof(v),&written);return v;
}
extern "C" size_t lt_ws(void* ptr,int i){return ((Plan*)ptr)->alg.at(i).workspaceSize;}
extern "C" int lt_run(void* ptr,int i,void* a,void* b,void* out,void* workspace,size_t bytes,void* stream) {
 Plan* p=(Plan*)ptr;float alpha=1,beta=0;
 return cublasLtMatmul(p->h,p->op,&alpha,a,p->a,b,p->b,&beta,out,p->c,out,p->c,&p->alg.at(i).algo,workspace,bytes,(cudaStream_t)stream);
}
extern "C" void lt_free(void* ptr) {
 Plan* p=(Plan*)ptr;cublasLtMatrixLayoutDestroy(p->a);cublasLtMatrixLayoutDestroy(p->b);cublasLtMatrixLayoutDestroy(p->c);cublasLtMatmulDescDestroy(p->op);cublasLtDestroy(p->h);delete p;
}

#include <set>
#include <array>
static int config_read(const cublasLtMatmulAlgo_t& a,int attr) {
 size_t written=0;
 if(attr==7 || attr==8) {uint16_t v=0xffff;auto s=cublasLtMatmulAlgoConfigGetAttribute(&a,(cublasLtMatmulAlgoConfigAttributes_t)attr,&v,sizeof(v),&written);return s==CUBLAS_STATUS_SUCCESS?v:-999;}
 int v=-999;auto s=cublasLtMatmulAlgoConfigGetAttribute(&a,(cublasLtMatmulAlgoConfigAttributes_t)attr,&v,sizeof(v),&written);return s==CUBLAS_STATUS_SUCCESS?v:-999;
}
static std::array<int,9> key(const cublasLtMatmulAlgo_t& a) {
 std::array<int,9> k;for(int i=0;i<9;++i)k[i]=config_read(a,i);return k;
}
static std::vector<uint32_t> caps(const cublasLtMatmulAlgo_t& a,cublasLtMatmulAlgoCapAttributes_t attr) {
 size_t bytes=0;
 if(cublasLtMatmulAlgoCapGetAttribute(&a,attr,nullptr,0,&bytes)!=CUBLAS_STATUS_SUCCESS || !bytes)return {0};
 std::vector<uint32_t> v(bytes/4);size_t got=0;
 if(cublasLtMatmulAlgoCapGetAttribute(&a,attr,v.data(),bytes,&got)!=CUBLAS_STATUS_SUCCESS)return {0};
 v.resize(got/4);return v.empty()?std::vector<uint32_t>{0}:v;
}
extern "C" int lt_attr_full(void* ptr,int i,int attr){return config_read(((Plan*)ptr)->alg.at(i).algo,attr);}
extern "C" int lt_expand(void* ptr,int algo_id,size_t ws) {
 auto* p=(Plan*)ptr;cublasLtMatmulAlgo_t base;
 auto status=cublasLtMatmulAlgoInit(p->h,CUBLAS_COMPUTE_32F,CUDA_R_32F,CUDA_R_16BF,CUDA_R_16BF,CUDA_R_16BF,CUDA_R_16BF,algo_id,&base);
 if(status!=CUBLAS_STATUS_SUCCESS)return -(int)status;
 auto tiles=caps(base,CUBLASLT_ALGO_CAP_TILE_IDS),stages=caps(base,CUBLASLT_ALGO_CAP_STAGES_IDS);
 int max_custom=0;uint32_t max_swizzle=0;size_t got=0;
 cublasLtMatmulAlgoCapGetAttribute(&base,CUBLASLT_ALGO_CAP_CUSTOM_OPTION_MAX,&max_custom,sizeof(max_custom),&got);
 cublasLtMatmulAlgoCapGetAttribute(&base,CUBLASLT_ALGO_CAP_CTA_SWIZZLING_SUPPORT,&max_swizzle,sizeof(max_swizzle),&got);
 max_custom=std::min(max_custom,7);max_swizzle=std::min(max_swizzle,1u);
 std::set<std::array<int,9>> seen;
 for(auto& r:p->alg)seen.insert(key(r.algo));
 int added=0;
 for(auto tile:tiles)for(auto stage:stages)for(uint32_t custom=0;custom<=(uint32_t)max_custom;++custom)for(uint32_t sw=0;sw<=max_swizzle;++sw) {
  auto cfg=base;bool ok=true;
  for(auto pair:std::array<std::pair<int,uint32_t>,4>{{{1,tile},{6,stage},{5,custom},{4,sw}}})
   ok &= cublasLtMatmulAlgoConfigSetAttribute(&cfg,(cublasLtMatmulAlgoConfigAttributes_t)pair.first,&pair.second,sizeof(pair.second))==CUBLAS_STATUS_SUCCESS;
  if(!ok)continue;
  cublasLtMatmulHeuristicResult_t r{};
  if(cublasLtMatmulAlgoCheck(p->h,p->op,p->a,p->b,p->c,p->c,&cfg,&r)!=CUBLAS_STATUS_SUCCESS || r.workspaceSize>ws)continue;
  auto k=key(cfg);if(!seen.insert(k).second)continue;
  r.algo=cfg;p->alg.push_back(r);++added;
 }
 return added;
}
extern "C" int lt_configure(void* ptr,const int* attrs,size_t ws) {
 auto* p=(Plan*)ptr;cublasLtMatmulAlgo_t a;
 auto status=cublasLtMatmulAlgoInit(p->h,CUBLAS_COMPUTE_32F,CUDA_R_32F,CUDA_R_16BF,CUDA_R_16BF,CUDA_R_16BF,CUDA_R_16BF,attrs[0],&a);
 if(status!=CUBLAS_STATUS_SUCCESS)return -(int)status;
 for(int j=1;j<9;++j) {
  if(attrs[j]<0)continue;
  if(j==7 || j==8) {uint16_t v=attrs[j];status=cublasLtMatmulAlgoConfigSetAttribute(&a,(cublasLtMatmulAlgoConfigAttributes_t)j,&v,sizeof(v));}
  else {int v=attrs[j];status=cublasLtMatmulAlgoConfigSetAttribute(&a,(cublasLtMatmulAlgoConfigAttributes_t)j,&v,sizeof(v));}
  if(status!=CUBLAS_STATUS_SUCCESS)return -(int)status;
 }
 cublasLtMatmulHeuristicResult_t r{};
 status=cublasLtMatmulAlgoCheck(p->h,p->op,p->a,p->b,p->c,p->c,&a,&r);
 if(status!=CUBLAS_STATUS_SUCCESS || r.workspaceSize>ws)return -100-(int)status;
 r.algo=a;p->alg.push_back(r);return p->alg.size()-1;
}
