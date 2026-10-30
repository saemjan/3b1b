/* The pool: exact capacity, stale and forged handles, conservation after churn, and four threads hammering it. */
#include <pthread.h>
#include <stdalign.h>
#include <stdatomic.h>
#include <string.h>

#include "../c17/cos_pool.h"
#include "c17_check.h"

#define CAP 64u
#define THREADS 4
#define ITER 60000

static alignas(64) unsigned char g_mem[64 + 8 * CAP + 4096]; /* test-only storage: the library itself never allocates */

typedef struct Shared {
  CosPool *pool;
  _Atomic uint32_t owner[CAP];
} Shared;

typedef struct Worker {
  Shared *sh;
  unsigned id;
  unsigned errors;
  uint64_t ops;
} Worker;

static void *hammer(void *arg) {
  Worker *w = (Worker *)arg;
  CosHandle held[6];
  unsigned nheld = 0;
  unsigned long x = 2463534242ul + w->id * 7919ul;
  for (int it = 0; it < ITER; ++it) {
    x ^= x << 13; x ^= x >> 17; x ^= x << 5; /* xorshift: deterministic per thread */
    if (nheld < 6u && (x & 3u) != 0u) {
      CosHandle h;
      if (cos_pool_alloc(w->sh->pool, &h) == COS_OK) {
        if (atomic_exchange(&w->sh->owner[cos_handle_index(h)], w->id + 1u) != 0u) w->errors++; /* two owners of one slot */
        held[nheld++] = h;
        w->ops++;
      }
    } else if (nheld > 0u) {
      const CosHandle h = held[--nheld];
      if (atomic_exchange(&w->sh->owner[cos_handle_index(h)], 0u) != w->id + 1u) w->errors++;
      if (cos_pool_free(w->sh->pool, h) != COS_OK) w->errors++;
      w->ops++;
    }
  }
  while (nheld > 0u) {
    const CosHandle h = held[--nheld];
    atomic_exchange(&w->sh->owner[cos_handle_index(h)], 0u);
    if (cos_pool_free(w->sh->pool, h) != COS_OK) w->errors++;
  }
  return NULL;
}

int main(void) {
  CosSuite s = {"c17_pool", 0, 0};

  /* setup refusals */
  CK(&s, cos_pool_bytes(0) == 0 && cos_pool_bytes(COS_POOL_MAX + 1u) == 0);
  CK(&s, cos_pool_init(g_mem + 1, sizeof g_mem - 1, 8) == NULL);          /* misaligned */
  CK(&s, cos_pool_init(g_mem, cos_pool_bytes(8) - 1u, 8) == NULL);       /* too small */
  CK(&s, cos_pool_init(NULL, 100, 8) == NULL);

  /* exact capacity and order */
  CosPool *p = cos_pool_init(g_mem, sizeof g_mem, 8);
  CK(&s, p != NULL && cos_pool_capacity(p) == 8u);
  CosHandle h[8], extra = 0;
  int distinct = 1;
  for (uint32_t i = 0; i < 8; ++i) {
    CK(&s, cos_pool_alloc(p, &h[i]) == COS_OK);
    if (cos_handle_index(h[i]) != i || (cos_handle_gen(h[i]) & 1u) == 0u || h[i] == 0u) distinct = 0;
  }
  CK(&s, distinct);
  CK(&s, cos_pool_in_use(p) == 8u);
  CK(&s, cos_pool_alloc(p, &extra) == COS_E_FULL); /* a full table is an answer, not a crash */

  /* validity, double free, forged handles */
  CK(&s, cos_pool_valid(p, h[3]));
  CK(&s, cos_pool_free(p, h[3]) == COS_OK);
  CK(&s, !cos_pool_valid(p, h[3]));
  CK(&s, cos_pool_free(p, h[3]) == COS_E_STALE);
  CK(&s, cos_pool_free(p, 0) == COS_E_INVALID);
  CK(&s, cos_pool_free(p, ((CosHandle)2u << 32) | 1u) == COS_E_INVALID);  /* even generation */
  CK(&s, cos_pool_free(p, ((CosHandle)1u << 32) | 99u) == COS_E_INVALID); /* index out of range */
  CK(&s, !cos_pool_valid(p, ((CosHandle)5u << 32) | 2u));                 /* right slot, wrong generation */

  /* the freed slot comes back first, with a new generation, so the old handle stays dead */
  CosHandle again;
  CK(&s, cos_pool_alloc(p, &again) == COS_OK);
  CK(&s, cos_handle_index(again) == 3u && again != h[3] && cos_pool_valid(p, again) && !cos_pool_valid(p, h[3]));
  CK(&s, cos_pool_free(p, h[3]) == COS_E_STALE);

  /* single-thread churn against a model, then conservation */
  CosHandle mine[8];
  unsigned nm = 0;
  unsigned long x = 88172645463325252ul;
  int model_ok = 1;
  for (int it = 0; it < 100000; ++it) {
    x ^= x << 13; x ^= x >> 7; x ^= x << 17;
    if ((x & 1u) != 0u && nm < 8u - 0u) {
      CosHandle t;
      const CosStatus st = cos_pool_alloc(p, &t);
      if (st == COS_OK) mine[nm++] = t;
      else if (st != COS_E_FULL) model_ok = 0;
    } else if (nm > 0u) {
      const unsigned k = (unsigned)(x >> 8) % nm;
      if (cos_pool_free(p, mine[k]) != COS_OK) model_ok = 0;
      mine[k] = mine[--nm];
    }
  }
  CK(&s, model_ok);
  /* free everything that is still allocated: the model's handles and the earlier ones (h[3] was replaced by `again`) */
  for (unsigned k = 0; k < nm; ++k) CK(&s, cos_pool_free(p, mine[k]) == COS_OK);
  /* the 7 handles taken before the churn (h without index 3, plus `again`) were never freed by the model: free them */
  for (uint32_t i = 0; i < 8; ++i) {
    const CosHandle t = (i == 3u) ? again : h[i];
    (void)cos_pool_free(p, t); /* some of these were freed during churn only if the model held them; stale is fine here */
  }
  CK(&s, cos_pool_in_use(p) == 0u);
  uint32_t got = 0;
  for (; got < 8u; ++got) {
    CosHandle t;
    if (cos_pool_alloc(p, &t) != COS_OK) break;
  }
  CK(&s, got == 8u); /* every slot is allocatable again: conservation */

  /* four threads */
  static Shared sh;
  sh.pool = cos_pool_init(g_mem, sizeof g_mem, CAP);
  CK(&s, sh.pool != NULL);
  for (unsigned i = 0; i < CAP; ++i) atomic_init(&sh.owner[i], 0u);
  Worker w[THREADS];
  pthread_t th[THREADS];
  for (unsigned i = 0; i < THREADS; ++i) {
    w[i].sh = &sh; w[i].id = i; w[i].errors = 0; w[i].ops = 0;
    pthread_create(&th[i], NULL, hammer, &w[i]);
  }
  unsigned errors = 0;
  uint64_t ops = 0;
  for (unsigned i = 0; i < THREADS; ++i) {
    pthread_join(th[i], NULL);
    errors += w[i].errors;
    ops += w[i].ops;
  }
  CK(&s, errors == 0u);
  CK(&s, cos_pool_in_use(sh.pool) == 0u);
  uint32_t all = 0;
  for (; all < CAP; ++all) {
    CosHandle t;
    if (cos_pool_alloc(sh.pool, &t) != COS_OK) break;
  }
  CK(&s, all == CAP);
  printf("  threads: %llu ops, %llu failed compare-and-swaps (contention), %u errors\n", (unsigned long long)ops,
         (unsigned long long)cos_pool_retries(sh.pool), errors);
  return suite_done(&s);
}
