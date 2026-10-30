/* SHA-256 (FIPS 180-4) and HMAC (RFC 2104). Constants are the same table as core/src/sha256.hpp; both are tested against NIST vectors. */
#include "cos_sha256.h"

#include <string.h>

static const uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be,
    0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa,
    0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85,
    0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f,
    0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

static uint32_t rotr(uint32_t x, unsigned n) { return (x >> n) | (x << (32u - n)); }

static void block(uint32_t h[8], const uint8_t p[64]) {
  uint32_t w[64];
  for (unsigned i = 0; i < 16; ++i)
    w[i] = ((uint32_t)p[i * 4] << 24) | ((uint32_t)p[i * 4 + 1] << 16) | ((uint32_t)p[i * 4 + 2] << 8) | (uint32_t)p[i * 4 + 3];
  for (unsigned i = 16; i < 64; ++i) {
    const uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
    const uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
    w[i] = w[i - 16] + s0 + w[i - 7] + s1;
  }
  uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
  for (unsigned i = 0; i < 64; ++i) {
    const uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
    const uint32_t ch = (e & f) ^ (~e & g);
    const uint32_t t1 = hh + S1 + ch + K[i] + w[i];
    const uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
    const uint32_t mj = (a & b) ^ (a & c) ^ (b & c);
    const uint32_t t2 = S0 + mj;
    hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
  }
  h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
}

void cos_sha256_init(CosSha256 *c) {
  static const uint32_t iv[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
  memcpy(c->h, iv, sizeof iv);
  c->bytes = 0;
  c->fill = 0;
}

void cos_sha256_update(CosSha256 *c, const void *data, size_t n) {
  const uint8_t *p = (const uint8_t *)data;
  c->bytes += (uint64_t)n;
  while (n > 0) {
    const size_t room = 64u - c->fill;
    const size_t take = n < room ? n : room;
    memcpy(c->buf + c->fill, p, take);
    c->fill += (uint32_t)take;
    p += take;
    n -= take;
    if (c->fill == 64u) {
      block(c->h, c->buf);
      c->fill = 0;
    }
  }
}

void cos_sha256_final(CosSha256 *c, uint8_t out[32]) {
  const uint64_t bits = c->bytes * 8u;
  const uint8_t one = 0x80;
  const uint8_t zero = 0;
  cos_sha256_update(c, &one, 1);
  while (c->fill != 56u) cos_sha256_update(c, &zero, 1);
  uint8_t len[8];
  for (unsigned i = 0; i < 8; ++i) len[i] = (uint8_t)(bits >> (56u - 8u * i));
  cos_sha256_update(c, len, 8);
  for (unsigned i = 0; i < 8; ++i) {
    out[i * 4] = (uint8_t)(c->h[i] >> 24);
    out[i * 4 + 1] = (uint8_t)(c->h[i] >> 16);
    out[i * 4 + 2] = (uint8_t)(c->h[i] >> 8);
    out[i * 4 + 3] = (uint8_t)c->h[i];
  }
  memset(c, 0, sizeof *c);
}

void cos_sha256(const void *data, size_t n, uint8_t out[32]) {
  CosSha256 c;
  cos_sha256_init(&c);
  cos_sha256_update(&c, data, n);
  cos_sha256_final(&c, out);
}

void cos_hmac_sha256(const uint8_t *key, size_t keylen, const void *msg, size_t n, uint8_t out[32]) {
  uint8_t k[64];
  memset(k, 0, sizeof k);
  if (keylen > 64u) cos_sha256(key, keylen, k);
  else if (keylen > 0u) memcpy(k, key, keylen);
  uint8_t pad[64];
  uint8_t inner[32];
  CosSha256 c;
  for (unsigned i = 0; i < 64; ++i) pad[i] = (uint8_t)(k[i] ^ 0x36u);
  cos_sha256_init(&c);
  cos_sha256_update(&c, pad, 64);
  cos_sha256_update(&c, msg, n);
  cos_sha256_final(&c, inner);
  for (unsigned i = 0; i < 64; ++i) pad[i] = (uint8_t)(k[i] ^ 0x5cu);
  cos_sha256_init(&c);
  cos_sha256_update(&c, pad, 64);
  cos_sha256_update(&c, inner, 32);
  cos_sha256_final(&c, out);
  memset(k, 0, sizeof k);
  memset(pad, 0, sizeof pad);
}

bool cos_ct_equal(const void *a, const void *b, size_t n) {
  const volatile uint8_t *x = (const volatile uint8_t *)a;
  const volatile uint8_t *y = (const volatile uint8_t *)b;
  uint8_t diff = 0;
  for (size_t i = 0; i < n; ++i) diff = (uint8_t)(diff | (x[i] ^ y[i]));
  return diff == 0;
}

void cos_hex(const uint8_t *in, size_t n, char *out) {
  static const char hex[] = "0123456789abcdef";
  for (size_t i = 0; i < n; ++i) {
    out[2 * i] = hex[in[i] >> 4];
    out[2 * i + 1] = hex[in[i] & 15u];
  }
  out[2 * n] = '\0';
}
