/* SHA-256, HMAC-SHA-256, constant-time compare, hex. C17, no heap, no globals. */
#ifndef COS_SHA256_H
#define COS_SHA256_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct CosSha256 {
  uint32_t h[8];
  uint64_t bytes;
  uint8_t buf[64];
  uint32_t fill;
} CosSha256;

void cos_sha256_init(CosSha256 *c);
void cos_sha256_update(CosSha256 *c, const void *data, size_t n);
void cos_sha256_final(CosSha256 *c, uint8_t out[32]);
void cos_sha256(const void *data, size_t n, uint8_t out[32]);
void cos_hmac_sha256(const uint8_t *key, size_t keylen, const void *msg, size_t n, uint8_t out[32]);
bool cos_ct_equal(const void *a, const void *b, size_t n); /* time does not depend on where the bytes differ */
void cos_hex(const uint8_t *in, size_t n, char *out);      /* out has room for 2n+1 chars */

#ifdef __cplusplus
}
#endif
#endif
