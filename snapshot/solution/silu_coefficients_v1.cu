#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cstdint>
struct alignas(16) Pack8 { uint16_t x[8]; };
__device__ __forceinline__ float silu_coefficient(float g) {
 float r;
 asm("{" ".reg .f32 e,t;" "mul.rn.ftz.f32 t,%1,0fBFB8AA3B;"
     "ex2.approx.ftz.f32 e,t;" "add.rn.ftz.f32 t,e,0f3F800000;"
     "div.approx.ftz.f32 %0,%1,t;" "}" : "=f"(r) : "f"(g));
 return r;
}
__device__ __forceinline__ float to_float(uint16_t bits) {
 __nv_bfloat16_raw raw; raw.x=bits;return __bfloat162float(__nv_bfloat16(raw));
}
__global__ void populate_table(float* table) {
 int i=blockIdx.x*blockDim.x+threadIdx.x;
 if(i<65536)table[i]=silu_coefficient(to_float((uint16_t)i));
}
template<bool Table> __global__ void silu_apply(const uint16_t* __restrict__ x,uint16_t* __restrict__ y,const float* __restrict__ table,int n,int64_t total) {
 int64_t first=((int64_t)blockIdx.x*blockDim.x+threadIdx.x)*8;
 if(first>=total)return;
 int64_t row=first/n;int col=first%n;
 Pack8 gates=*reinterpret_cast<const Pack8*>(x+row*(2*n)+col);
 Pack8 ups=*reinterpret_cast<const Pack8*>(x+row*(2*n)+n+col);
 Pack8 output;
 #pragma unroll
 for(int j=0;j<8;j++) {
  float coefficient=Table?__ldg(table+gates.x[j]):silu_coefficient(to_float(gates.x[j]));
  float up=to_float(ups.x[j]),value;
  asm("mul.rn.ftz.f32 %0,%1,%2;" : "=f"(value) : "f"(coefficient),"f"(up));
  __nv_bfloat16_raw raw=__float2bfloat16_rn(value);
  output.x[j]=raw.x;
 }
 *reinterpret_cast<Pack8*>(y+first)=output;
}
extern "C" int silu_table_build(float* table,void* stream) {
 populate_table<<<256,256,0,(cudaStream_t)stream>>>(table);return (int)cudaGetLastError();
}
extern "C" int silu_table_apply(void* input,void* output,float* table,int rows,int n,int threads,int use_table,void* stream) {
 if(n%8 || n<8 || rows<1 || (threads!=128 && threads!=256 && threads!=512))return (int)cudaErrorInvalidValue;
 int64_t count=(int64_t)rows*n;int grid=(count+threads*8-1)/(threads*8);
 if(use_table)silu_apply<true><<<grid,threads,0,(cudaStream_t)stream>>>((uint16_t*)input,(uint16_t*)output,table,n,count);
 else silu_apply<false><<<grid,threads,0,(cudaStream_t)stream>>>((uint16_t*)input,(uint16_t*)output,table,n,count);
 return (int)cudaGetLastError();
}
