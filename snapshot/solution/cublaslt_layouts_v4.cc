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
extern "C" void* lt_make_layout(int m,int n,int k,int a_col,int b_col,int c_col,int mpad,size_t ws,int limit) {
 Plan* p=new Plan; cublasLtCreate(&p->h);
 cublasLtMatmulDescCreate(&p->op,CUBLAS_COMPUTE_32F,CUDA_R_32F);
 cublasLtMatrixLayoutCreate(&p->a,CUDA_R_16BF,m,k,a_col?mpad:k);
 cublasLtMatrixLayoutCreate(&p->b,CUDA_R_16BF,k,n,b_col?k:n);
 cublasLtMatrixLayoutCreate(&p->c,CUDA_R_16BF,m,n,c_col?mpad:n);
 cublasLtOrder_t row=CUBLASLT_ORDER_ROW,col=CUBLASLT_ORDER_COL;
 cublasLtMatrixLayoutSetAttribute(p->a,CUBLASLT_MATRIX_LAYOUT_ORDER,a_col?&col:&row,sizeof(row));
 cublasLtMatrixLayoutSetAttribute(p->b,CUBLASLT_MATRIX_LAYOUT_ORDER,b_col?&col:&row,sizeof(row));
 cublasLtMatrixLayoutSetAttribute(p->c,CUBLASLT_MATRIX_LAYOUT_ORDER,c_col?&col:&row,sizeof(row));
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

extern "C" int lt_cap_bytes(void* ptr,int i,int attr) {
 size_t bytes=0;auto* p=(Plan*)ptr;auto status=cublasLtMatmulAlgoCapGetAttribute(&p->alg.at(i).algo,(cublasLtMatmulAlgoCapAttributes_t)attr,nullptr,0,&bytes);
 return status==CUBLAS_STATUS_SUCCESS?(int)bytes:-(int)status;
}
extern "C" int lt_expand_explicit(void* ptr,size_t ws) {
 auto* p=(Plan*)ptr;auto seeds=p->alg;std::set<std::array<int,9>> seen;
 for(auto& r:p->alg)seen.insert(key(r.algo));int added=0;
 std::vector<int> tiles={15,17,18,19,20,21,22,23,24,26,29,32,33,116,117,118,119,176,177,232,318,321,324,326,328,331,333,335,338,340,342,345,347,349,352,354,356,359,361,363,400,403,406,409,412,414,416,419,421,423,426,428,430,433,435,437,439,441,443,445,447,493,495,497,500,502,504,507,509,511,513,631};
 for(auto& seed:seeds)for(int tile:tiles)for(int stage:{0,35,36,16,22})for(int custom:{0,1,2,3})for(int sw:{0,1})for(uint16_t cluster:{2,3,5,6}) {
  auto cfg=seed.algo;bool ok=true;
  for(auto pair:std::array<std::pair<int,int>,4>{{{1,tile},{6,stage},{5,custom},{4,sw}}})
   ok &= cublasLtMatmulAlgoConfigSetAttribute(&cfg,(cublasLtMatmulAlgoConfigAttributes_t)pair.first,&pair.second,sizeof(pair.second))==CUBLAS_STATUS_SUCCESS;
  ok &= cublasLtMatmulAlgoConfigSetAttribute(&cfg,CUBLASLT_ALGO_CONFIG_CLUSTER_SHAPE_ID,&cluster,sizeof(cluster))==CUBLAS_STATUS_SUCCESS;
  if(!ok)continue;auto k=key(cfg);if(seen.count(k))continue;
  cublasLtMatmulHeuristicResult_t r{};
  if(cublasLtMatmulAlgoCheck(p->h,p->op,p->a,p->b,p->c,p->c,&cfg,&r)!=CUBLAS_STATUS_SUCCESS || r.workspaceSize>ws)continue;
  seen.insert(k);r.algo=cfg;p->alg.push_back(r);++added;
 }
 return added;
}
extern "C" int lt_find_existing(void* ptr,const int* attrs) {
 auto* p=(Plan*)ptr;
 for(int i=0;i<(int)p->alg.size();++i) {
  bool same=true;for(int j=0;j<9;++j)if(attrs[j]>=0 && attrs[j]!=config_read(p->alg[i].algo,j))same=false;
  if(same)return i;
 }
 return -1;
}
