/* A fixed pool of slots handed out as generation-stamped handles. Lock-free: a tagged Treiber stack.
 * The pool manages only slot numbers; the caller keeps its own payload array indexed by cos_handle_index().
 * Adapted from xv6-riscv (MIT): kernel/kalloc.c (free list) and the lock lab (kalloctest). Rewritten in C17 for the Saem sovereign kernel. */
#ifndef COS_POOL_H
#define COS_POOL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "cos_limits.h"
#include "cos_status.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef uint64_t CosHandle; /* generation (high 32 bits, odd while allocated) | slot index (low 32 bits); 0 is never valid */
typedef struct CosPool CosPool;

static inline uint32_t cos_handle_index(CosHandle h) { return (uint32_t)(h & 0xffffffffu); }
static inline uint32_t cos_handle_gen(CosHandle h) { return (uint32_t)(h >> 32); }

size_t cos_pool_bytes(uint32_t capacity);                         /* 0 when capacity is 0 or above COS_POOL_MAX */
CosPool *cos_pool_init(void *mem, size_t len, uint32_t capacity); /* NULL if mem is not 64-byte aligned or len is too small */
CosStatus cos_pool_alloc(CosPool *p, CosHandle *out);             /* COS_E_FULL when no slot is free */
CosStatus cos_pool_free(CosPool *p, CosHandle h);                 /* COS_E_STALE on a second free; COS_E_INVALID on a forged handle */
bool cos_pool_valid(const CosPool *p, CosHandle h);
uint32_t cos_pool_capacity(const CosPool *p);
uint32_t cos_pool_in_use(const CosPool *p);
uint64_t cos_pool_retries(const CosPool *p); /* failed compare-and-swaps: the contention number, like xv6's ntas */

#ifdef __cplusplus
}
#endif
#endif
