/* The seal: one SHA-256 digest over everything that defines what this core IS: its limits, build id, constitution articles and method table.
 * The release tool signs the digest (HMAC-SHA-256 with a provisioned key). The core refuses to start if digest or tag do not match,
 * and re-checks the digest on every call: a changed byte freezes it. A software seal detects accidental or one-copy tampering; the hardware
 * lock (RISC-V PMP, phase 3) is what makes it unchangeable. HMAC is symmetric; a public-key signature comes with phase 2. */
#ifndef COS_SEAL_H
#define COS_SEAL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "cos_limits.h"

#ifdef __cplusplus
extern "C" {
#endif

#define COS_FLAG_JSON 1u /* a method flag: its input must be bracket-balanced JSON-like text (see COS_SCAN_JSON) */

typedef struct CosArticle {
  uint16_t id;
  const char *title;
  const char *text;
} CosArticle;

typedef struct CosMethodRule {
  uint16_t id; /* 0..255; the table must be sorted by id, ids unique */
  uint8_t flags;
  uint32_t max_len; /* 0 = COS_MAX_INPUT */
  const char *name;
} CosMethodRule;

typedef struct CosSealInput {
  const CosArticle *articles;
  uint32_t n_articles;
  const CosMethodRule *methods;
  uint32_t n_methods;
  const char *build_id;
} CosSealInput;

void cos_seal_digest(const CosSealInput *in, uint8_t out[32]);
void cos_seal_tag(const uint8_t *key, size_t keylen, const uint8_t digest[32], uint8_t tag[32]); /* HMAC-SHA-256(key, "QCOS-SEAL-TAG-V1" + digest) */
bool cos_seal_check(const CosSealInput *in, const uint8_t sealed[32]);

#ifdef __cplusplus
}
#endif
#endif
