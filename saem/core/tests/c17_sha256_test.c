/* SHA-256 and HMAC against the NIST and RFC 4231 vectors, plus streaming splits. */
#include <string.h>

#include "../c17/cos_sha256.h"
#include "c17_check.h"

static void hex_of(const void *d, size_t n, char out[65]) {
  uint8_t h[32];
  cos_sha256(d, n, h);
  cos_hex(h, 32, out);
}

int main(void) {
  CosSuite s = {"c17_sha256", 0, 0};
  char hx[65];
  hex_of("", 0, hx);
  CK(&s, strcmp(hx, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") == 0);
  hex_of("abc", 3, hx);
  CK(&s, strcmp(hx, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0);
  const char *two = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
  hex_of(two, strlen(two), hx);
  CK(&s, strcmp(hx, "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1") == 0);

  /* one million 'a', fed in uneven pieces */
  CosSha256 c;
  uint8_t h[32];
  uint8_t chunk[997];
  memset(chunk, 'a', sizeof chunk);
  cos_sha256_init(&c);
  size_t left = 1000000u;
  while (left > 0) {
    const size_t t = left < sizeof chunk ? left : sizeof chunk;
    cos_sha256_update(&c, chunk, t);
    left -= t;
  }
  cos_sha256_final(&c, h);
  cos_hex(h, 32, hx);
  CK(&s, strcmp(hx, "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0") == 0);

  /* every split point of a 200-byte message gives the same digest as one shot */
  uint8_t msg[200], one[32], two_part[32];
  for (size_t i = 0; i < sizeof msg; ++i) msg[i] = (uint8_t)(i * 7u + 3u);
  cos_sha256(msg, sizeof msg, one);
  int splits_ok = 1;
  for (size_t cut = 0; cut <= sizeof msg; ++cut) {
    cos_sha256_init(&c);
    cos_sha256_update(&c, msg, cut);
    cos_sha256_update(&c, msg + cut, sizeof msg - cut);
    cos_sha256_final(&c, two_part);
    if (memcmp(one, two_part, 32) != 0) splits_ok = 0;
  }
  CK(&s, splits_ok);

  /* RFC 4231 test cases 1, 2 and 6 */
  uint8_t key1[20];
  memset(key1, 0x0b, sizeof key1);
  cos_hmac_sha256(key1, sizeof key1, "Hi There", 8, h);
  cos_hex(h, 32, hx);
  CK(&s, strcmp(hx, "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7") == 0);
  cos_hmac_sha256((const uint8_t *)"Jefe", 4, "what do ya want for nothing?", 28, h);
  cos_hex(h, 32, hx);
  CK(&s, strcmp(hx, "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843") == 0);
  uint8_t key6[131];
  memset(key6, 0xaa, sizeof key6);
  const char *m6 = "Test Using Larger Than Block-Size Key - Hash Key First";
  cos_hmac_sha256(key6, sizeof key6, m6, strlen(m6), h);
  cos_hex(h, 32, hx);
  CK(&s, strcmp(hx, "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54") == 0);

  CK(&s, cos_ct_equal("abcd", "abcd", 4));
  CK(&s, !cos_ct_equal("abcd", "abce", 4));
  CK(&s, cos_ct_equal("x", "y", 0));
  return suite_done(&s);
}
