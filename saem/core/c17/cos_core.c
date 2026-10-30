#include "cos_core.h"

#include <stdalign.h>
#include <stdatomic.h>
#include <string.h>

#include "cos_le.h"
#include "cos_sha256.h"

struct CosCore {
  alignas(COS_CACHE_LINE) _Atomic uint32_t frozen; /* 0 = running, else a CosFreezeReason */
  alignas(COS_CACHE_LINE) _Atomic uint64_t calls;
  alignas(COS_CACHE_LINE) _Atomic uint64_t accepted;
  alignas(COS_CACHE_LINE) _Atomic uint64_t rejected;
  alignas(COS_CACHE_LINE) _Atomic uint64_t quarantined;
  alignas(COS_CACHE_LINE) _Atomic uint64_t qmask[COS_MAX_METHODS / 64u]; /* one bit per method id */
  _Atomic uint32_t method_rejects[COS_MAX_METHODS];
  CosSealInput seal;
  uint8_t sealed[32];
  CosJournal *journal;
};

static size_t align_up(size_t n, size_t a) { return (n + a - 1u) / a * a; }

size_t cos_core_bytes(void) { return align_up(sizeof(struct CosCore), COS_CACHE_LINE) + cos_journal_bytes() + COS_CACHE_LINE; }

static const CosMethodRule *find_method(const CosCore *c, uint16_t id) {
  uint32_t lo = 0, hi = c->seal.n_methods; /* binary search: the table is sorted by id */
  while (lo < hi) {
    const uint32_t mid = lo + (hi - lo) / 2u;
    const uint16_t v = c->seal.methods[mid].id;
    if (v == id) return &c->seal.methods[mid];
    if (v < id) lo = mid + 1u;
    else hi = mid;
  }
  return NULL;
}

static bool table_ok(const CosSealInput *s) {
  if (s->n_methods > COS_MAX_METHODS || (s->n_methods > 0u && s->methods == NULL)) return false;
  if (s->n_articles > 0u && s->articles == NULL) return false;
  for (uint32_t i = 0; i < s->n_methods; ++i) {
    if (s->methods[i].id >= COS_MAX_METHODS || s->methods[i].name == NULL) return false;
    if (i > 0u && s->methods[i - 1u].id >= s->methods[i].id) return false; /* sorted, unique */
  }
  for (uint32_t i = 0; i < s->n_articles; ++i)
    if (s->articles[i].title == NULL || s->articles[i].text == NULL) return false;
  return s->build_id != NULL;
}

/* A restart must not lift a quarantine: only a person's journaled approval does. So at open the journal is verified end to end (a broken
 * chain means the core refuses to start) and its QUARANTINE and RELEASE records are replayed into the quarantine mask. */
static CosStatus replay(CosCore *c) {
  uint64_t good = 0, bad = 0;
  CosStatus st = cos_journal_verify(c->journal, &good, &bad);
  if (st != COS_OK) return st;
  const uint64_t n = cos_journal_count(c->journal);
  for (uint64_t s = 0; s < n; ++s) {
    CosRecord r;
    st = cos_journal_read(c->journal, s, &r);
    if (st != COS_OK) return st;
    if (r.kind == COS_EV_QUARANTINE && r.len >= 3u) {
      const uint16_t m = cos_get16(r.payload);
      if (m < COS_MAX_METHODS) atomic_fetch_or_explicit(&c->qmask[m >> 6], 1ull << (m & 63u), memory_order_relaxed);
    } else if (r.kind == COS_EV_RELEASE && r.len >= 2u) {
      const uint16_t m = cos_get16(r.payload);
      if (m < COS_MAX_METHODS) atomic_fetch_and_explicit(&c->qmask[m >> 6], ~(1ull << (m & 63u)), memory_order_relaxed);
    }
  }
  return COS_OK;
}

CosStatus cos_core_open(void *mem, size_t len, const CosConfig *cfg, CosCore **out) {
  if (out == NULL) return COS_E_INVALID;
  *out = NULL; /* set only on success, so a caller that ignores the status cannot use a half-started core */
  if (cfg == NULL) return COS_E_INVALID;
  if (mem == NULL || len < cos_core_bytes() || ((uintptr_t)mem % COS_CACHE_LINE) != 0u) return COS_E_ALIGN;
  if (!table_ok(&cfg->seal) || cfg->key == NULL || cfg->keylen < 16u) return COS_E_INVALID; /* a provisioned key is at least 128 bits */
  uint8_t digest[32], tag[32];
  cos_seal_digest(&cfg->seal, digest);
  if (!cos_ct_equal(digest, cfg->expected_digest, 32)) return COS_E_CORRUPT; /* the tables are not the ones that were signed */
  cos_seal_tag(cfg->key, cfg->keylen, digest, tag);
  if (!cos_ct_equal(tag, cfg->expected_tag, 32)) return COS_E_DENIED;       /* wrong key, or a digest that was never signed */
  memset(mem, 0, sizeof(struct CosCore));
  CosCore *c = (CosCore *)mem;
  atomic_init(&c->frozen, 0u);
  atomic_init(&c->calls, 0u);
  atomic_init(&c->accepted, 0u);
  atomic_init(&c->rejected, 0u);
  atomic_init(&c->quarantined, 0u);
  for (uint32_t i = 0; i < COS_MAX_METHODS / 64u; ++i) atomic_init(&c->qmask[i], 0u);
  for (uint32_t i = 0; i < COS_MAX_METHODS; ++i) atomic_init(&c->method_rejects[i], 0u);
  c->seal = cfg->seal;
  memcpy(c->sealed, digest, 32);
  uint8_t *jmem = (uint8_t *)mem + align_up(sizeof(struct CosCore), COS_CACHE_LINE);
  CosStatus st = cos_journal_open(jmem, len - (size_t)(jmem - (uint8_t *)mem), &cfg->journal_dev, cfg->format_journal, &c->journal);
  if (st != COS_OK) return st;
  st = replay(c); /* the journal is the durable truth: the chain must be whole, and quarantines survive a restart */
  if (st != COS_OK) return st;
  st = cos_journal_append(c->journal, COS_EV_OPEN, digest, 32, cfg->tick); /* no receipt, no start */
  if (st != COS_OK) return st;
  *out = c;
  return COS_OK;
}

static void journal_event(CosCore *c, uint16_t kind, const void *p, uint16_t n, uint64_t tick) { (void)cos_journal_append(c->journal, kind, p, n, tick); }

CosStatus cos_core_freeze(CosCore *c, CosFreezeReason why, uint64_t tick) {
  if (why == COS_FREEZE_NONE) return COS_E_INVALID;
  uint32_t zero = 0u;
  if (atomic_compare_exchange_strong(&c->frozen, &zero, (uint32_t)why)) { /* only the first reason is recorded */
    uint8_t p[4];
    cos_put32(p, (uint32_t)why);
    journal_event(c, COS_EV_FREEZE, p, 4, tick); /* best effort: the journal itself may be the reason */
  }
  return COS_OK;
}

bool cos_core_frozen(const CosCore *c, uint32_t *why) {
  const uint32_t f = atomic_load_explicit(&c->frozen, memory_order_acquire);
  if (why != NULL) *why = f;
  return f != 0u;
}

static CosVerdict verdict(CosZone z, CosStatus st, CosRule rule, uint32_t off, uint16_t method) {
  CosVerdict v = {z, st, rule, off, method};
  return v;
}

CosVerdict cos_core_gate(CosCore *c, uint16_t method, const void *in, size_t n, uint64_t tick) {
  atomic_fetch_add_explicit(&c->calls, 1u, memory_order_relaxed);
  if (cos_core_frozen(c, NULL)) return verdict(COS_ZONE_FREEZE, COS_E_FROZEN, COS_RULE_FROZEN, 0, method);
  if (!cos_seal_check(&c->seal, c->sealed)) { /* something this core is made of has changed: lock out at once */
    (void)cos_core_freeze(c, COS_FREEZE_SEAL, tick);
    return verdict(COS_ZONE_FREEZE, COS_E_FROZEN, COS_RULE_SEAL, 0, method);
  }
  const CosMethodRule *m = find_method(c, method);
  if (m == NULL) {
    atomic_fetch_add_explicit(&c->rejected, 1u, memory_order_relaxed);
    return verdict(COS_ZONE_REJECT, COS_E_UNKNOWN, COS_RULE_METHOD, 0, method);
  }
  const uint64_t bit = 1ull << (method & 63u);
  if ((atomic_load_explicit(&c->qmask[method >> 6], memory_order_acquire) & bit) != 0u) {
    atomic_fetch_add_explicit(&c->quarantined, 1u, memory_order_relaxed);
    return verdict(COS_ZONE_QUARANTINE, COS_E_QUARANTINED, COS_RULE_QUARANTINE, 0, method);
  }
  const CosScan sc = cos_gate_scan((const uint8_t *)in, n, m->max_len, (m->flags & COS_FLAG_JSON) != 0u ? COS_SCAN_JSON : 0u);
  if (sc.status == COS_OK) {
    atomic_fetch_add_explicit(&c->accepted, 1u, memory_order_relaxed);
    if (atomic_load_explicit(&c->method_rejects[method], memory_order_relaxed) != 0u) /* "repeated" means in a row: an accepted input clears the count */
      atomic_store_explicit(&c->method_rejects[method], 0u, memory_order_relaxed);
    return verdict(COS_ZONE_ACCEPT, COS_OK, COS_RULE_NONE, 0, method);
  }
  atomic_fetch_add_explicit(&c->rejected, 1u, memory_order_relaxed);
  const uint32_t seen = atomic_fetch_add_explicit(&c->method_rejects[method], 1u, memory_order_relaxed) + 1u;
  if (seen >= COS_QUARANTINE_AFTER) {
    const uint64_t before = atomic_fetch_or_explicit(&c->qmask[method >> 6], bit, memory_order_acq_rel);
    if ((before & bit) == 0u) { /* this call is the one that quarantined it */
      uint8_t p[3];
      cos_put16(p, method);
      p[2] = (uint8_t)sc.rule;
      journal_event(c, COS_EV_QUARANTINE, p, 3, tick);
    }
  }
  return verdict(COS_ZONE_REJECT, sc.status, sc.rule, sc.offset, method);
}

CosStatus cos_core_audit(CosCore *c, uint16_t kind, const void *payload, uint16_t len, uint64_t tick) {
  if (cos_core_frozen(c, NULL)) return COS_E_FROZEN;
  if (kind < COS_EV_USER) return COS_E_INVALID; /* the low kinds belong to the core: nobody else may write an OPEN, FREEZE, QUARANTINE or RELEASE */
  return cos_journal_append(c->journal, kind, payload, len, tick);
}

CosStatus cos_core_verify(CosCore *c, uint64_t tick) {
  if (cos_core_frozen(c, NULL)) return COS_E_FROZEN;
  uint64_t good = 0, bad = 0;
  const CosStatus st = cos_journal_verify(c->journal, &good, &bad);
  if (st == COS_E_CORRUPT) (void)cos_core_freeze(c, COS_FREEZE_JOURNAL, tick); /* an unreadable device (COS_E_IO) is a failure to report, not proof of tampering */
  return st;
}

bool cos_core_quarantined(const CosCore *c, uint16_t method) {
  if (method >= COS_MAX_METHODS) return false;
  return (atomic_load_explicit(&c->qmask[method >> 6], memory_order_acquire) & (1ull << (method & 63u))) != 0u;
}

CosStatus cos_core_release(CosCore *c, uint16_t method, const char *approver, uint64_t tick) {
  if (cos_core_frozen(c, NULL)) return COS_E_FROZEN;
  if (method >= COS_MAX_METHODS || approver == NULL) return COS_E_INVALID;
  size_t k = 0;
  while (k <= 64u && approver[k] != '\0') ++k; /* never reads past the 65th byte of a C string */
  if (k == 0u) return COS_E_INVALID;           /* an empty name is not an approval */
  if (k > 64u) return COS_E_TOO_BIG;
  const CosScan nm = cos_gate_scan((const uint8_t *)approver, k, 64u, 0u); /* the approver's name is raw input too: Zone 0 first */
  if (nm.status != COS_OK) return nm.status;
  const uint64_t bit = 1ull << (method & 63u);
  if ((atomic_load_explicit(&c->qmask[method >> 6], memory_order_acquire) & bit) == 0u) return COS_E_NOT_FOUND;
  uint8_t p[2 + 64];
  cos_put16(p, method);
  memcpy(p + 2, approver, k);
  const CosStatus st = cos_journal_append(c->journal, COS_EV_RELEASE, p, (uint16_t)(2u + k), tick); /* no receipt, no release */
  if (st != COS_OK) return st;
  atomic_store_explicit(&c->method_rejects[method], 0u, memory_order_relaxed);
  atomic_fetch_and_explicit(&c->qmask[method >> 6], ~bit, memory_order_acq_rel);
  return COS_OK;
}

void cos_core_stats(const CosCore *c, CosCoreStats *out) {
  out->calls = atomic_load_explicit(&c->calls, memory_order_relaxed);
  out->accepted = atomic_load_explicit(&c->accepted, memory_order_relaxed);
  out->rejected = atomic_load_explicit(&c->rejected, memory_order_relaxed);
  out->quarantined = atomic_load_explicit(&c->quarantined, memory_order_relaxed);
  out->journal_records = cos_journal_count(c->journal);
  out->frozen_reason = atomic_load_explicit(&c->frozen, memory_order_relaxed);
}

CosJournal *cos_core_journal(CosCore *c) { return c->journal; }
