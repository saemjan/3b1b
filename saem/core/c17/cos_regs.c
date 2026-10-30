#include "cos_regs.h"

#include <stdalign.h>
#include <string.h>

#define S COS_WORKING_LIMIT /* sentinel index of the LRU list */

typedef struct Reg {
  CosValue v;
  uint32_t refcnt;
  uint8_t valid;
  uint8_t pad[3];
} Reg;

COS_STATIC_ASSERT(sizeof(CosValue) == 56u, "CosValue is 56 bytes");
COS_STATIC_ASSERT(sizeof(Reg) == COS_CACHE_LINE, "one register is exactly one cache line");

struct CosRegs {
  alignas(COS_CACHE_LINE) Reg reg[COS_WORKING_LIMIT];
  CosValue ring[COS_EPISODIC_RING];
  uint64_t head, tail; /* free-running counters: occupancy = tail - head, slot = counter % ring size */
  uint32_t l2_live;    /* episodes in the ring that are not tombstones */
  uint8_t nxt[COS_WORKING_LIMIT + 1u]; /* LRU list through indexes; nxt[S] is the most recently used, prv[S] the least */
  uint8_t prv[COS_WORKING_LIMIT + 1u];
  CosRegsStats st;
};

size_t cos_regs_bytes(void) { return sizeof(struct CosRegs); }

static void list_front(CosRegs *r, uint8_t i) { /* insert i as most recently used */
  r->nxt[i] = r->nxt[S];
  r->prv[i] = (uint8_t)S;
  r->prv[r->nxt[S]] = i;
  r->nxt[S] = i;
}

static void list_unlink(CosRegs *r, uint8_t i) {
  r->nxt[r->prv[i]] = r->nxt[i];
  r->prv[r->nxt[i]] = r->prv[i];
}

CosRegs *cos_regs_init(void *mem, size_t len) {
  if (mem == NULL || len < sizeof(struct CosRegs) || ((uintptr_t)mem % COS_CACHE_LINE) != 0u) return NULL;
  memset(mem, 0, sizeof(struct CosRegs));
  CosRegs *r = (CosRegs *)mem;
  r->nxt[S] = (uint8_t)S;
  r->prv[S] = (uint8_t)S;
  for (uint8_t i = 0; i < COS_WORKING_LIMIT; ++i) list_front(r, i);
  return r;
}

static void spill(CosRegs *r, const CosValue *v) {
  if (r->tail - r->head == COS_EPISODIC_RING) { /* the ring is full: the oldest episode is overwritten */
    CosValue *old = &r->ring[r->head % COS_EPISODIC_RING];
    if (old->key != 0u) {
      r->st.dropped++;
      r->l2_live--;
    }
    r->head++;
  }
  r->ring[r->tail % COS_EPISODIC_RING] = *v;
  r->tail++;
  r->l2_live++;
  r->st.spilled++;
}

CosStatus cos_regs_open(CosRegs *r, uint64_t key, uint32_t kind, uint32_t *id, bool *fresh) {
  if (r == NULL || key == 0u || id == NULL || fresh == NULL) return COS_E_INVALID;
  for (uint32_t i = 0; i < COS_WORKING_LIMIT; ++i) { /* hit */
    Reg *g = &r->reg[i];
    if (g->valid && g->v.key == key) {
      if (g->v.kind != kind) return COS_E_INVALID;
      g->refcnt++;
      r->st.hits++;
      *id = i;
      *fresh = false;
      return COS_OK;
    }
  }
  /* miss: pick the least recently used register nobody has pinned; nothing is changed if there is none */
  uint8_t victim = r->prv[S];
  while (victim != S && r->reg[victim].refcnt != 0u) victim = r->prv[victim];
  if (victim == S) return COS_E_FULL;
  r->st.misses++;
  /* look in L2 BEFORE the victim is spilled, so a full ring cannot overwrite the very episode we want back */
  CosValue got;
  bool found = false;
  for (uint64_t c = r->tail; c > r->head; --c) {
    CosValue *e = &r->ring[(c - 1u) % COS_EPISODIC_RING];
    if (e->key == key) {
      if (e->kind != kind) return COS_E_INVALID;
      got = *e;
      e->key = 0u; /* tombstone */
      r->l2_live--;
      found = true;
      break;
    }
  }
  Reg *g = &r->reg[victim];
  if (g->valid) spill(r, &g->v);
  if (found) {
    g->v = got;
    r->st.promoted++;
  } else {
    memset(&g->v, 0, sizeof g->v);
    g->v.key = key;
    g->v.kind = kind;
  }
  g->valid = 1u;
  g->refcnt = 1u;
  *id = victim;
  *fresh = !found;
  return COS_OK;
}

CosValue *cos_regs_value(CosRegs *r, uint32_t id) {
  if (r == NULL || id >= COS_WORKING_LIMIT) return NULL;
  Reg *g = &r->reg[id];
  return (g->valid && g->refcnt > 0u) ? &g->v : NULL;
}

CosStatus cos_regs_close(CosRegs *r, uint32_t id) {
  if (r == NULL || id >= COS_WORKING_LIMIT) return COS_E_INVALID;
  Reg *g = &r->reg[id];
  if (!g->valid || g->refcnt == 0u) return COS_E_INVALID;
  g->refcnt--;
  if (g->refcnt == 0u) {
    list_unlink(r, (uint8_t)id);
    list_front(r, (uint8_t)id);
  }
  return COS_OK;
}

uint32_t cos_regs_l1_used(const CosRegs *r) {
  uint32_t n = 0;
  for (uint32_t i = 0; i < COS_WORKING_LIMIT; ++i) n += r->reg[i].valid ? 1u : 0u;
  return n;
}

uint32_t cos_regs_l2_used(const CosRegs *r) { return r->l2_live; }

CosStatus cos_regs_peek_l2(const CosRegs *r, uint64_t key, CosValue *out) {
  if (key == 0u) return COS_E_INVALID;
  for (uint64_t c = r->tail; c > r->head; --c) {
    const CosValue *e = &r->ring[(c - 1u) % COS_EPISODIC_RING];
    if (e->key == key) {
      *out = *e;
      return COS_OK;
    }
  }
  return COS_E_NOT_FOUND;
}

void cos_regs_stats(const CosRegs *r, CosRegsStats *out) { *out = r->st; }
