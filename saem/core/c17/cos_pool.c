#include "cos_pool.h"

#include <stdalign.h>
#include <stdatomic.h>
#include <string.h>

typedef struct Slot {
  _Atomic uint32_t gen;  /* even: free, odd: allocated; every alloc and every free adds one */
  _Atomic uint32_t next; /* while free: index+1 of the next free slot, 0 ends the list */
} Slot;

struct CosPool {
  alignas(COS_CACHE_LINE) _Atomic uint64_t head; /* tag (high 32) | index+1 of the top free slot (low 32); the tag defeats ABA */
  alignas(COS_CACHE_LINE) _Atomic uint32_t in_use;
  alignas(COS_CACHE_LINE) _Atomic uint64_t retries;
  alignas(COS_CACHE_LINE) uint32_t capacity;
  Slot slot[];
};

size_t cos_pool_bytes(uint32_t capacity) {
  if (capacity == 0u || capacity > COS_POOL_MAX) return 0;
  return offsetof(struct CosPool, slot) + (size_t)capacity * sizeof(Slot);
}

CosPool *cos_pool_init(void *mem, size_t len, uint32_t capacity) {
  const size_t need = cos_pool_bytes(capacity);
  if (need == 0u || mem == NULL || len < need) return NULL;
  if (((uintptr_t)mem % COS_CACHE_LINE) != 0u) return NULL;
  memset(mem, 0, need);
  CosPool *p = (CosPool *)mem;
  p->capacity = capacity;
  for (uint32_t i = 0; i < capacity; ++i) {
    atomic_init(&p->slot[i].gen, 0u);
    atomic_init(&p->slot[i].next, i + 1u < capacity ? i + 2u : 0u);
  }
  atomic_init(&p->head, 1u); /* tag 0, top = slot 0: slots come out in order 0,1,2,... */
  atomic_init(&p->in_use, 0u);
  atomic_init(&p->retries, 0u);
  return p;
}

CosStatus cos_pool_alloc(CosPool *p, CosHandle *out) {
  uint64_t h = atomic_load_explicit(&p->head, memory_order_acquire);
  for (;;) {
    const uint32_t top = (uint32_t)h;
    if (top == 0u) return COS_E_FULL;
    const uint32_t next = atomic_load_explicit(&p->slot[top - 1u].next, memory_order_relaxed);
    const uint64_t nh = (((h >> 32) + 1u) << 32) | (uint64_t)next;
    if (atomic_compare_exchange_strong_explicit(&p->head, &h, nh, memory_order_acq_rel, memory_order_acquire)) {
      const uint32_t i = top - 1u;
      const uint32_t g = atomic_load_explicit(&p->slot[i].gen, memory_order_relaxed) + 1u; /* even to odd */
      atomic_store_explicit(&p->slot[i].gen, g, memory_order_release);
      atomic_fetch_add_explicit(&p->in_use, 1u, memory_order_relaxed);
      *out = ((uint64_t)g << 32) | (uint64_t)i;
      return COS_OK;
    }
    atomic_fetch_add_explicit(&p->retries, 1u, memory_order_relaxed);
  }
}

CosStatus cos_pool_free(CosPool *p, CosHandle hd) {
  const uint32_t i = cos_handle_index(hd);
  const uint32_t g = cos_handle_gen(hd);
  if (i >= p->capacity || (g & 1u) == 0u) return COS_E_INVALID;
  uint32_t expect = g;
  if (!atomic_compare_exchange_strong_explicit(&p->slot[i].gen, &expect, g + 1u, memory_order_acq_rel, memory_order_acquire))
    return COS_E_STALE;
  uint64_t h = atomic_load_explicit(&p->head, memory_order_relaxed);
  for (;;) {
    atomic_store_explicit(&p->slot[i].next, (uint32_t)h, memory_order_relaxed);
    const uint64_t nh = (((h >> 32) + 1u) << 32) | (uint64_t)(i + 1u);
    if (atomic_compare_exchange_strong_explicit(&p->head, &h, nh, memory_order_release, memory_order_relaxed)) break;
    atomic_fetch_add_explicit(&p->retries, 1u, memory_order_relaxed);
  }
  atomic_fetch_sub_explicit(&p->in_use, 1u, memory_order_relaxed);
  return COS_OK;
}

bool cos_pool_valid(const CosPool *p, CosHandle hd) {
  const uint32_t i = cos_handle_index(hd);
  const uint32_t g = cos_handle_gen(hd);
  if (i >= p->capacity || (g & 1u) == 0u) return false;
  return atomic_load_explicit(&p->slot[i].gen, memory_order_acquire) == g;
}

uint32_t cos_pool_capacity(const CosPool *p) { return p->capacity; }
uint32_t cos_pool_in_use(const CosPool *p) { return atomic_load_explicit(&p->in_use, memory_order_relaxed); }
uint64_t cos_pool_retries(const CosPool *p) { return atomic_load_explicit(&p->retries, memory_order_relaxed); }
