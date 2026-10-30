/* The model's working memory: L1 = COS_WORKING_LIMIT registers with LRU recycling, L2 = a COS_EPISODIC_RING-slot ring of spilled episodes.
 * One CosRegs belongs to ONE node (one writer, no locks). Nodes share through rings, never through registers.
 * Adapted from xv6-riscv (MIT): kernel/bio.c (LRU buffer cache, pin counts) and kernel/pipe.c (free-running ring counters).
 * Rewritten in C17 for the Saem sovereign kernel: indexes instead of pointers, and a full table returns COS_E_FULL instead of panicking. */
#ifndef COS_REGS_H
#define COS_REGS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "cos_limits.h"
#include "cos_status.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct CosValue {
  uint64_t key; /* identity; never 0; set by cos_regs_open, do not change */
  uint32_t kind;
  uint32_t len; /* bytes of data in use */
  uint8_t data[COS_REG_DATA];
} CosValue;

typedef struct CosRegsStats {
  uint64_t hits, misses, promoted, spilled, dropped;
} CosRegsStats;

typedef struct CosRegs CosRegs;

size_t cos_regs_bytes(void);
CosRegs *cos_regs_init(void *mem, size_t len); /* NULL if mem is not 64-byte aligned or too small */

/* Pin the register for `key`: from L1 if present, else promoted from L2, else a fresh zeroed one (*fresh = true).
 * COS_E_FULL when all registers are pinned; COS_E_INVALID for key 0 or a kind that differs from the resident one. Nothing changes on failure. */
CosStatus cos_regs_open(CosRegs *r, uint64_t key, uint32_t kind, uint32_t *id, bool *fresh);
CosValue *cos_regs_value(CosRegs *r, uint32_t id); /* NULL unless `id` is currently pinned */
CosStatus cos_regs_close(CosRegs *r, uint32_t id); /* unpin; at zero pins the register becomes the most recently used */

uint32_t cos_regs_l1_used(const CosRegs *r);
uint32_t cos_regs_l2_used(const CosRegs *r);
CosStatus cos_regs_peek_l2(const CosRegs *r, uint64_t key, CosValue *out); /* newest matching episode, not removed */
void cos_regs_stats(const CosRegs *r, CosRegsStats *out);

#ifdef __cplusplus
}
#endif
#endif
