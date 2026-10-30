/* Helper for tools/check_c17.py: prints what the C kernel computes, so Python can compare it with independent implementations.
 *   c17_dump gate     the gate's rule number (one hex digit) for every code point U+0000..U+10FFFF, each encoded alone; then, after a newline,
 *                     the rule number for ZWJ right after each code point and, after another newline, for ZWNJ right after each code point
 *   c17_dump hash     reads lines "keyhex msghex" (key "-" = none) from stdin; prints "sha256hex hmachex" per line ("-" when there is no key)
 * Test tooling only: it uses stdio, the kernel itself does not. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cos_gate.h"
#include "cos_sha256.h"

static size_t enc(uint32_t cp, uint8_t *b) {
  if (cp < 0x80u) { b[0] = (uint8_t)cp; return 1; }
  if (cp < 0x800u) { b[0] = (uint8_t)(0xC0u | (cp >> 6)); b[1] = (uint8_t)(0x80u | (cp & 0x3Fu)); return 2; }
  if (cp < 0x10000u) {
    b[0] = (uint8_t)(0xE0u | (cp >> 12)); b[1] = (uint8_t)(0x80u | ((cp >> 6) & 0x3Fu)); b[2] = (uint8_t)(0x80u | (cp & 0x3Fu));
    return 3;
  }
  b[0] = (uint8_t)(0xF0u | (cp >> 18)); b[1] = (uint8_t)(0x80u | ((cp >> 12) & 0x3Fu));
  b[2] = (uint8_t)(0x80u | ((cp >> 6) & 0x3Fu)); b[3] = (uint8_t)(0x80u | (cp & 0x3Fu));
  return 4;
}

static int dump_gate(void) {
  static const char hexd[] = "0123456789abcdef";
  for (uint32_t cp = 0; cp <= 0x10FFFFu; ++cp) {
    uint8_t b[4];
    const size_t n = enc(cp, b);
    putchar(hexd[cos_gate_scan(b, n, 0, 0).rule]);
  }
  putchar('\n');
  for (int pass = 0; pass < 2; ++pass) {
    const uint32_t joiner = pass == 0 ? 0x200Du : 0x200Cu;
    for (uint32_t cp = 0; cp <= 0x10FFFFu; ++cp) {
      uint8_t b[8];
      size_t n = enc(cp, b);
      n += enc(joiner, b + n);
      putchar(hexd[cos_gate_scan(b, n, 0, 0).rule]); /* if the first code point is itself refused, its rule shows instead */
    }
    putchar('\n');
  }
  return 0;
}

static int unhex(const char *s, uint8_t *out, size_t cap, size_t *n) {
  const size_t len = strlen(s);
  if (len % 2u != 0u || len / 2u > cap) return -1;
  for (size_t i = 0; i < len / 2u; ++i) {
    unsigned v = 0;
    if (sscanf(s + 2u * i, "%2x", &v) != 1) return -1;
    out[i] = (uint8_t)v;
  }
  *n = len / 2u;
  return 0;
}

static int dump_hash(void) {
  static char line[1 << 17];
  static uint8_t key[8192], msg[32768];
  while (fgets(line, sizeof line, stdin) != NULL) {
    char kh[16384], mh[65536];
    kh[0] = mh[0] = '\0';
    const char *sp = strchr(line, ' ');
    if (sp == NULL) return 2;
    size_t kl = (size_t)(sp - line);
    if (kl >= sizeof kh) return 2;
    memcpy(kh, line, kl);
    kh[kl] = '\0';
    char *end = strpbrk(sp + 1, "\r\n");
    if (end != NULL) *end = '\0';
    if (strlen(sp + 1) >= sizeof mh) return 2;
    strcpy(mh, sp + 1);
    size_t keyn = 0, msgn = 0;
    const int has_key = strcmp(kh, "-") != 0;
    if (has_key && unhex(kh, key, sizeof key, &keyn) != 0) return 2;
    if (unhex(mh, msg, sizeof msg, &msgn) != 0) return 2;
    uint8_t d[32], m[32];
    char dh[65], mhx[65];
    cos_sha256(msg, msgn, d);
    cos_hex(d, 32, dh);
    if (has_key) {
      cos_hmac_sha256(key, keyn, msg, msgn, m);
      cos_hex(m, 32, mhx);
    } else {
      strcpy(mhx, "-");
    }
    printf("%s %s\n", dh, mhx);
  }
  return 0;
}

int main(int argc, char **argv) {
  if (argc == 2 && strcmp(argv[1], "gate") == 0) return dump_gate();
  if (argc == 2 && strcmp(argv[1], "hash") == 0) return dump_hash();
  fprintf(stderr, "usage: c17_dump gate|hash\n");
  return 2;
}
