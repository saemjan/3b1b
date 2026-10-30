/* Registers: exact limit, LRU recycling, pins, spill to the ring, promotion back, ring overflow, determinism. */
#include <stdalign.h>
#include <string.h>

#include "../c17/cos_regs.h"
#include "c17_check.h"

static alignas(64) unsigned char mem_a[8192];
static alignas(64) unsigned char mem_b[8192];

static void put(CosRegs *r, uint32_t id, uint8_t tag) {
  CosValue *v = cos_regs_value(r, id);
  v->len = 1;
  v->data[0] = tag;
}

int main(void) {
  CosSuite s = {"c17_regs", 0, 0};
  CK(&s, cos_regs_bytes() <= sizeof mem_a);
  CK(&s, cos_regs_init(mem_a + 8, sizeof mem_a - 8) == NULL);
  CK(&s, cos_regs_init(mem_a, cos_regs_bytes() - 1u) == NULL);

  CosRegs *r = cos_regs_init(mem_a, sizeof mem_a);
  CK(&s, r != NULL);
  uint32_t id[COS_WORKING_LIMIT + 1u];
  bool fresh;

  /* 1. exactly COS_WORKING_LIMIT registers can be pinned; the next open is refused and changes nothing */
  for (uint32_t k = 1; k <= COS_WORKING_LIMIT; ++k) {
    CK(&s, cos_regs_open(r, k, 7, &id[k], &fresh) == COS_OK && fresh);
    put(r, id[k], (uint8_t)(k + 100u));
  }
  CK(&s, cos_regs_l1_used(r) == COS_WORKING_LIMIT);
  CosRegsStats st0, st1;
  cos_regs_stats(r, &st0);
  uint32_t dummy;
  CK(&s, cos_regs_open(r, 999, 7, &dummy, &fresh) == COS_E_FULL);
  cos_regs_stats(r, &st1);
  CK(&s, memcmp(&st0, &st1, sizeof st0) == 0 && cos_regs_l2_used(r) == 0u);
  CK(&s, cos_regs_open(r, 0, 7, &dummy, &fresh) == COS_E_INVALID);

  /* 2. close in order 1..32; hits keep the data */
  for (uint32_t k = 1; k <= COS_WORKING_LIMIT; ++k) CK(&s, cos_regs_close(r, id[k]) == COS_OK);
  CK(&s, cos_regs_close(r, id[1]) == COS_E_INVALID); /* not pinned any more */
  CK(&s, cos_regs_value(r, id[1]) == NULL);
  CK(&s, cos_regs_open(r, 5, 7, &dummy, &fresh) == COS_OK && !fresh && cos_regs_value(r, dummy)->data[0] == 105u);
  CK(&s, cos_regs_open(r, 5, 8, &id[0], &fresh) == COS_E_INVALID); /* same key, different kind */
  CK(&s, cos_regs_close(r, dummy) == COS_OK);   /* 5 is now the most recently used */

  /* 3. LRU: key 1 was closed first, so a new key evicts it into L2; opening key 1 brings it back intact */
  CK(&s, cos_regs_open(r, 500, 7, &id[0], &fresh) == COS_OK && fresh);
  CK(&s, cos_regs_close(r, id[0]) == COS_OK);
  CosValue ev;
  CK(&s, cos_regs_peek_l2(r, 1, &ev) == COS_OK && ev.data[0] == 101u && ev.len == 1u);
  CK(&s, cos_regs_peek_l2(r, 2, &ev) == COS_E_NOT_FOUND);
  CK(&s, cos_regs_open(r, 1, 7, &id[1], &fresh) == COS_OK && !fresh && cos_regs_value(r, id[1])->data[0] == 101u);
  CK(&s, cos_regs_peek_l2(r, 1, &ev) == COS_E_NOT_FOUND); /* it left L2 */
  CK(&s, cos_regs_close(r, id[1]) == COS_OK);
  cos_regs_stats(r, &st1);
  CK(&s, st1.promoted == 1u && st1.spilled == 2u);

  /* 4. a pinned register is never recycled, however much traffic passes by; a double pin needs two closes */
  uint32_t a, a2;
  CK(&s, cos_regs_open(r, 77, 3, &a, &fresh) == COS_OK);
  put(r, a, 42);
  CK(&s, cos_regs_open(r, 77, 3, &a2, &fresh) == COS_OK && a2 == a && !fresh);
  for (uint32_t k = 1000; k < 1100; ++k) {
    uint32_t t;
    CK(&s, cos_regs_open(r, k, 1, &t, &fresh) == COS_OK);
    CK(&s, cos_regs_close(r, t) == COS_OK);
  }
  CK(&s, cos_regs_value(r, a) != NULL && cos_regs_value(r, a)->data[0] == 42u);
  CK(&s, cos_regs_close(r, a) == COS_OK);
  CK(&s, cos_regs_value(r, a) != NULL); /* still pinned once */
  CK(&s, cos_regs_close(r, a) == COS_OK);
  CK(&s, cos_regs_value(r, a) == NULL);

  /* 5. ring overflow on a clean instance: 200 keys through 32 registers */
  r = cos_regs_init(mem_a, sizeof mem_a);
  for (uint32_t k = 1; k <= 200u; ++k) {
    uint32_t t;
    CK(&s, cos_regs_open(r, k, 1, &t, &fresh) == COS_OK && fresh);
    put(r, t, (uint8_t)k);
    CK(&s, cos_regs_close(r, t) == COS_OK);
  }
  cos_regs_stats(r, &st1);
  CK(&s, st1.spilled == 168u && st1.dropped == 104u && cos_regs_l2_used(r) == COS_EPISODIC_RING && cos_regs_l1_used(r) == COS_WORKING_LIMIT);
  CK(&s, cos_regs_peek_l2(r, 168, &ev) == COS_OK && ev.data[0] == 168u);
  CK(&s, cos_regs_peek_l2(r, 105, &ev) == COS_OK);
  CK(&s, cos_regs_peek_l2(r, 104, &ev) == COS_E_NOT_FOUND); /* fell off the ring */
  { uint32_t t; CK(&s, cos_regs_open(r, 104, 1, &t, &fresh) == COS_OK && fresh); CK(&s, cos_regs_close(r, t) == COS_OK); }

  /* 6. the episode we want back is the OLDEST in a full ring: it must survive the spill of the victim */
  r = cos_regs_init(mem_a, sizeof mem_a);
  for (uint32_t k = 1; k <= 32u + 64u; ++k) {
    uint32_t t;
    CK(&s, cos_regs_open(r, k, 1, &t, &fresh) == COS_OK);
    put(r, t, (uint8_t)k);
    CK(&s, cos_regs_close(r, t) == COS_OK);
  } /* ring now holds keys 1..64, full */
  { uint32_t t; CK(&s, cos_regs_open(r, 1, 1, &t, &fresh) == COS_OK && !fresh && cos_regs_value(r, t)->data[0] == 1u); CK(&s, cos_regs_close(r, t) == COS_OK); }

  /* 7. determinism: the same operations on two instances leave identical bytes */
  CosRegs *x = cos_regs_init(mem_a, sizeof mem_a);
  CosRegs *y = cos_regs_init(mem_b, sizeof mem_b);
  unsigned long q = 123456789ul;
  for (int it = 0; it < 5000; ++it) {
    q ^= q << 13; q ^= q >> 7; q ^= q << 17;
    const uint64_t key = 1u + (q % 90u);
    CosRegs *both[2] = {x, y};
    for (int w = 0; w < 2; ++w) {
      uint32_t t;
      if (cos_regs_open(both[w], key, 1, &t, &fresh) == COS_OK) {
        CosValue *v = cos_regs_value(both[w], t);
        v->len = 2; v->data[0] = (uint8_t)key; v->data[1] = (uint8_t)(q >> 8);
        cos_regs_close(both[w], t);
      }
    }
  }
  CK(&s, memcmp(x, y, cos_regs_bytes()) == 0);
  return suite_done(&s);
}
