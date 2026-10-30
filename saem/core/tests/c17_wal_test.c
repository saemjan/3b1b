/* The write-ahead log: a transaction is all-or-nothing at EVERY possible power-cut point, torn writes included,
 * and also when the power fails again during recovery. */
#include <stdalign.h>
#include <string.h>

#include "../c17/cos_wal.h"
#include "c17_check.h"
#include "c17_ramdev.h"

#define NB 64u
static uint8_t img[NB * COS_BLOCK_SIZE];
static uint8_t base[NB * COS_BLOCK_SIZE];
static alignas(64) unsigned char wmem[40000];
static const uint32_t HOME[3] = {40, 41, 42};

static void fill(uint8_t *b, uint8_t v) { memset(b, v, COS_BLOCK_SIZE); }

/* 0 = all old, 1 = all new, -1 = a mixture or something else */
static int state(void) {
  int old = 0, nw = 0;
  for (unsigned i = 0; i < 3; ++i) {
    const uint8_t *b = img + (size_t)HOME[i] * COS_BLOCK_SIZE;
    const uint8_t v = b[0];
    for (unsigned k = 0; k < COS_BLOCK_SIZE; ++k)
      if (b[k] != v) return -1;
    if (v == 'O') old++;
    else if (v == 'N') nw++;
    else return -1;
  }
  return old == 3 ? 0 : (nw == 3 ? 1 : -1);
}

static CosStatus run_txn(RamDev *d, uint8_t v) {
  CosBlockDev dev = ram_dev(d);
  CosWal *w = cos_wal_init(wmem, sizeof wmem, &dev, 1);
  if (w == NULL) return COS_E_INVALID;
  uint8_t b[COS_BLOCK_SIZE];
  fill(b, v);
  cos_wal_begin(w);
  for (unsigned i = 0; i < 3; ++i) {
    const CosStatus st = cos_wal_put(w, HOME[i], b);
    if (st != COS_OK) return st;
  }
  return cos_wal_commit(w);
}

static CosStatus recover(RamDev *d, uint32_t *replayed) {
  CosBlockDev dev = ram_dev(d);
  CosWal *w = cos_wal_init(wmem, sizeof wmem, &dev, 1);
  if (w == NULL) return COS_E_INVALID;
  return cos_wal_recover(w, replayed);
}

int main(void) {
  CosSuite s = {"c17_wal", 0, 0};
  RamDev d = {img, NB, -1, 0, false, 0, 0};

  /* a good start: old data everywhere, blank log */
  memset(img, 0, sizeof img);
  for (unsigned i = 0; i < 3; ++i) fill(img + (size_t)HOME[i] * COS_BLOCK_SIZE, 'O');
  memcpy(base, img, sizeof img);

  /* setup refusals */
  CosBlockDev dev = ram_dev(&d);
  CK(&s, cos_wal_init(wmem, sizeof wmem, &dev, NB - 5) == NULL); /* log would run off the device */
  CK(&s, cos_wal_init(wmem, 100, &dev, 1) == NULL);

  /* clean commit and its write count */
  CK(&s, run_txn(&d, 'N') == COS_OK && state() == 1);
  const long total = d.writes; /* 3 log blocks + header + 3 homes + clear = 8 */
  CK(&s, total == 8);

  /* a transaction that is too big, a block inside the log, and an absorbed repeat */
  { CosWal *w = cos_wal_init(wmem, sizeof wmem, &dev, 1);
    uint8_t b[COS_BLOCK_SIZE];
    fill(b, 1);
    cos_wal_begin(w);
    for (uint32_t i = 0; i < COS_LOG_BLOCKS; ++i) CK(&s, cos_wal_put(w, 32u + i, b) == COS_OK);
    CK(&s, cos_wal_put(w, 63, b) == COS_E_FULL);          /* a full log is an answer */
    CK(&s, cos_wal_put(w, 32, b) == COS_OK);              /* the same block again is absorbed, not a new entry */
    CK(&s, cos_wal_put(w, 5, b) == COS_E_INVALID);        /* inside the log area */
    CK(&s, cos_wal_put(w, NB, b) == COS_E_INVALID);       /* off the device */
    cos_wal_abort(w); }

  /* every power-cut point, with the write lost (0), half of it landing (1: the whole header fits in those 256 bytes, so it
   * may complete the commit) and a sliver landing (2: the header hash cannot match) */
  for (int tear = 0; tear <= 2; ++tear) {
    for (long k = 0; k <= total; ++k) {
      memcpy(img, base, sizeof img);
      ram_reboot(&d);
      d.writes = 0; d.tear = tear; d.budget = k;
      const CosStatus st = run_txn(&d, 'N');
      CK(&s, (k < total) ? st != COS_OK : st == COS_OK);
      ram_reboot(&d);
      uint32_t rep = 0;
      CK(&s, recover(&d, &rep) == COS_OK);
      /* the 4th write is the commit header: once it landed whole the transaction must complete; before that, nothing may show.
       * A half-landed header (tear 1, k 3) may go either way, but never a mixture. */
      const int got = state();
      if (k >= 4) CK(&s, got == 1);
      else if (k == 3 && tear == 1) CK(&s, got == 0 || got == 1);
      else CK(&s, got == 0);
      /* recovery is idempotent */
      CK(&s, recover(&d, &rep) == COS_OK && rep == 0u && state() == got);
    }
  }

  /* the power fails AGAIN during recovery, at every point */
  for (int tear = 0; tear <= 2; ++tear) {
    for (long k2 = 0; k2 <= 5; ++k2) {
      memcpy(img, base, sizeof img);
      ram_reboot(&d);
      d.writes = 0; d.tear = 0; d.budget = 5; /* crash after the commit header and one home block */
      (void)run_txn(&d, 'N');
      ram_reboot(&d);
      d.tear = tear; d.budget = k2;
      uint32_t rep = 0;
      (void)recover(&d, &rep);
      ram_reboot(&d);
      CK(&s, recover(&d, &rep) == COS_OK && state() == 1);
    }
  }

  /* a device that breaks the flush contract: header durable, a logged block not. Detected, never guessed. */
  memcpy(img, base, sizeof img);
  ram_reboot(&d);
  d.writes = 0; d.tear = 0; d.budget = 4;
  (void)run_txn(&d, 'N');
  ram_reboot(&d);
  img[(size_t)3 * COS_BLOCK_SIZE + 7] ^= 0x55; /* damage a logged data block */
  uint32_t rep = 0;
  CK(&s, recover(&d, &rep) == COS_E_CORRUPT && state() == 0);
  return suite_done(&s);
}
