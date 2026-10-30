#include "cos_seal.h"

#include <string.h>

#include "cos_le.h"
#include "cos_sha256.h"

static void u16(CosSha256 *c, uint16_t v) { uint8_t b[2]; cos_put16(b, v); cos_sha256_update(c, b, 2); }
static void u32(CosSha256 *c, uint32_t v) { uint8_t b[4]; cos_put32(b, v); cos_sha256_update(c, b, 4); }
static void str(CosSha256 *c, const char *s) {
  const size_t n = s != NULL ? strlen(s) : 0u;
  u32(c, (uint32_t)n);
  if (n > 0u) cos_sha256_update(c, s, n);
}

/* Canonical encoding (all integers little-endian), the same in tools/seal.py:
 *   "QCOS-SEAL-V1\0"
 *   limits: WORKING_LIMIT, EPISODIC_RING, REG_DATA, BLOCK_SIZE, LOG_BLOCKS, MAX_INPUT, MAX_DEPTH, MAX_METHODS, QUARANTINE_AFTER (u32 each)
 *   str build_id
 *   u32 n_articles, each: u16 id, str title, str text
 *   u32 n_methods,  each: u16 id, u8 flags, u32 max_len, str name        (str = u32 length, then the bytes) */
void cos_seal_digest(const CosSealInput *in, uint8_t out[32]) {
  CosSha256 c;
  cos_sha256_init(&c);
  cos_sha256_update(&c, "QCOS-SEAL-V1", 13); /* includes the NUL */
  u32(&c, COS_WORKING_LIMIT);
  u32(&c, COS_EPISODIC_RING);
  u32(&c, COS_REG_DATA);
  u32(&c, COS_BLOCK_SIZE);
  u32(&c, COS_LOG_BLOCKS);
  u32(&c, COS_MAX_INPUT);
  u32(&c, COS_MAX_DEPTH);
  u32(&c, COS_MAX_METHODS);
  u32(&c, COS_QUARANTINE_AFTER);
  str(&c, in->build_id);
  u32(&c, in->n_articles);
  for (uint32_t i = 0; i < in->n_articles; ++i) {
    u16(&c, in->articles[i].id);
    str(&c, in->articles[i].title);
    str(&c, in->articles[i].text);
  }
  u32(&c, in->n_methods);
  for (uint32_t i = 0; i < in->n_methods; ++i) {
    u16(&c, in->methods[i].id);
    cos_sha256_update(&c, &in->methods[i].flags, 1);
    u32(&c, in->methods[i].max_len);
    str(&c, in->methods[i].name);
  }
  cos_sha256_final(&c, out);
}

void cos_seal_tag(const uint8_t *key, size_t keylen, const uint8_t digest[32], uint8_t tag[32]) {
  uint8_t msg[16 + 32];
  memcpy(msg, "QCOS-SEAL-TAG-V1", 16);
  memcpy(msg + 16, digest, 32);
  cos_hmac_sha256(key, keylen, msg, sizeof msg, tag);
}

bool cos_seal_check(const CosSealInput *in, const uint8_t sealed[32]) {
  uint8_t d[32];
  cos_seal_digest(in, d);
  return cos_ct_equal(d, sealed, 32);
}
