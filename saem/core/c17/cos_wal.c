#include "cos_wal.h"

#include <string.h>

#include "cos_le.h"
#include "cos_sha256.h"

#define WAL_MAGIC 0x4c415753u /* bytes 'S' 'W' 'A' 'L' */
#define WAL_VERSION 1u
#define H_BNO 24u
#define H_DATAHASH (H_BNO + 4u * COS_LOG_BLOCKS) /* 144 */
#define H_HASH (H_DATAHASH + 32u)                /* 176 */

COS_STATIC_ASSERT(H_HASH + 32u <= COS_BLOCK_SIZE, "log header must fit in one block");

struct CosWal {
  CosBlockDev dev;
  uint32_t log_start;
  uint32_t n;
  uint64_t seq;
  uint32_t bno[COS_LOG_BLOCKS];
  uint8_t data[COS_LOG_BLOCKS][COS_BLOCK_SIZE];
  uint8_t scratch[COS_BLOCK_SIZE];
};

size_t cos_wal_bytes(void) { return sizeof(struct CosWal); }

CosWal *cos_wal_init(void *mem, size_t len, const CosBlockDev *dev, uint32_t log_start) {
  if (mem == NULL || dev == NULL || len < sizeof(struct CosWal) || ((uintptr_t)mem % 8u) != 0u) return NULL;
  if (dev->read == NULL || dev->write == NULL || dev->flush == NULL) return NULL;
  if ((uint64_t)log_start + 1u + COS_LOG_BLOCKS > dev->nblocks) return NULL;
  memset(mem, 0, sizeof(struct CosWal));
  CosWal *w = (CosWal *)mem;
  w->dev = *dev;
  w->log_start = log_start;
  return w;
}

static bool in_log(const CosWal *w, uint32_t blk) { return blk >= w->log_start && blk <= w->log_start + COS_LOG_BLOCKS; }

static void header_build(const CosWal *w, uint32_t n, uint8_t out[COS_BLOCK_SIZE]) {
  memset(out, 0, COS_BLOCK_SIZE);
  cos_put32(out, WAL_MAGIC);
  cos_put32(out + 4, WAL_VERSION);
  cos_put64(out + 8, w->seq);
  cos_put32(out + 16, n);
  for (uint32_t i = 0; i < n; ++i) cos_put32(out + H_BNO + 4u * i, w->bno[i]);
  if (n > 0u) {
    CosSha256 c;
    cos_sha256_init(&c);
    for (uint32_t i = 0; i < n; ++i) cos_sha256_update(&c, w->data[i], COS_BLOCK_SIZE);
    cos_sha256_final(&c, out + H_DATAHASH);
  }
  cos_sha256(out, H_HASH, out + H_HASH);
}

/* COS_OK when the block is a self-consistent header; COS_E_NOT_FOUND when it is blank, foreign or torn (nothing was committed). */
static CosStatus header_parse(const uint8_t b[COS_BLOCK_SIZE], uint32_t *n, uint64_t *seq) {
  if (cos_get32(b) != WAL_MAGIC || cos_get32(b + 4) != WAL_VERSION) return COS_E_NOT_FOUND;
  uint8_t h[32];
  cos_sha256(b, H_HASH, h);
  if (!cos_ct_equal(h, b + H_HASH, 32)) return COS_E_NOT_FOUND;
  *n = cos_get32(b + 16);
  *seq = cos_get64(b + 8);
  return COS_OK;
}

static CosStatus write_block(CosWal *w, uint32_t blk, const uint8_t *buf) { return w->dev.write(w->dev.ctx, blk, buf) == 0 ? COS_OK : COS_E_IO; }
static CosStatus flush_dev(CosWal *w) { return w->dev.flush(w->dev.ctx) == 0 ? COS_OK : COS_E_IO; }

static CosStatus install_and_clear(CosWal *w) {
  for (uint32_t i = 0; i < w->n; ++i) {
    const CosStatus st = write_block(w, w->bno[i], w->data[i]);
    if (st != COS_OK) return st;
  }
  CosStatus st = flush_dev(w);
  if (st != COS_OK) return st;
  header_build(w, 0, w->scratch); /* erase the transaction: the commit is complete */
  st = write_block(w, w->log_start, w->scratch);
  if (st != COS_OK) return st;
  st = flush_dev(w);
  if (st != COS_OK) return st;
  w->n = 0;
  return COS_OK;
}

CosStatus cos_wal_recover(CosWal *w, uint32_t *replayed) {
  *replayed = 0;
  if (w->dev.read(w->dev.ctx, w->log_start, w->scratch) != 0) return COS_E_IO;
  uint32_t n = 0;
  uint64_t seq = 0;
  if (header_parse(w->scratch, &n, &seq) != COS_OK) { /* nothing was committed (blank, or the commit write was torn) */
    w->n = 0;
    return COS_OK;
  }
  w->seq = seq;
  if (n == 0u) {
    w->n = 0;
    return COS_OK;
  }
  if (n > COS_LOG_BLOCKS) return COS_E_CORRUPT;
  for (uint32_t i = 0; i < n; ++i) w->bno[i] = cos_get32(w->scratch + H_BNO + 4u * i);
  uint8_t want[32];
  memcpy(want, w->scratch + H_DATAHASH, 32);
  for (uint32_t i = 0; i < n; ++i) {
    if (w->bno[i] >= w->dev.nblocks || in_log(w, w->bno[i])) return COS_E_CORRUPT;
    if (w->dev.read(w->dev.ctx, w->log_start + 1u + i, w->data[i]) != 0) return COS_E_IO;
  }
  CosSha256 c;
  uint8_t got[32];
  cos_sha256_init(&c);
  for (uint32_t i = 0; i < n; ++i) cos_sha256_update(&c, w->data[i], COS_BLOCK_SIZE);
  cos_sha256_final(&c, got);
  if (!cos_ct_equal(got, want, 32)) return COS_E_CORRUPT; /* the header was durable but its blocks are not: the device broke the flush contract */
  w->n = n;
  const CosStatus st = install_and_clear(w);
  if (st != COS_OK) return st;
  *replayed = n;
  return COS_OK;
}

CosStatus cos_wal_begin(CosWal *w) {
  w->n = 0;
  return COS_OK;
}

CosStatus cos_wal_put(CosWal *w, uint32_t blk, const uint8_t data[COS_BLOCK_SIZE]) {
  if (blk >= w->dev.nblocks || in_log(w, blk)) return COS_E_INVALID;
  for (uint32_t i = 0; i < w->n; ++i) {
    if (w->bno[i] == blk) { /* absorption: one copy of a block per transaction */
      memcpy(w->data[i], data, COS_BLOCK_SIZE);
      return COS_OK;
    }
  }
  if (w->n >= COS_LOG_BLOCKS) return COS_E_FULL;
  w->bno[w->n] = blk;
  memcpy(w->data[w->n], data, COS_BLOCK_SIZE);
  w->n++;
  return COS_OK;
}

CosStatus cos_wal_commit(CosWal *w) {
  if (w->n == 0u) return COS_OK;
  CosStatus st;
  for (uint32_t i = 0; i < w->n; ++i) {
    st = write_block(w, w->log_start + 1u + i, w->data[i]);
    if (st != COS_OK) return st;
  }
  st = flush_dev(w);
  if (st != COS_OK) return st;
  w->seq++;
  header_build(w, w->n, w->scratch);
  st = write_block(w, w->log_start, w->scratch); /* the commit point */
  if (st != COS_OK) return st;
  st = flush_dev(w);
  if (st != COS_OK) return st;
  return install_and_clear(w);
}

void cos_wal_abort(CosWal *w) { w->n = 0; }
uint64_t cos_wal_seq(const CosWal *w) { return w->seq; }
