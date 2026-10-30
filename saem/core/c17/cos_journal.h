/* The audit journal: append-only records, each chained to the one before by SHA-256, stored through the write-ahead log so every
 * append is atomic. Anyone who changes, reorders or removes a stored record breaks the chain and cos_journal_verify says where.
 * Limit, stated plainly: restoring an OLDER COMPLETE image of the device is not detectable from the device alone; keep cos_journal_head()
 * (count and head hash) somewhere else (the core does) to anchor it.
 * Adapted from xv6-riscv (MIT): kernel/log.c, and from the Open Math Harness security event journal. Rewritten in C17. */
#ifndef COS_JOURNAL_H
#define COS_JOURNAL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "cos_blockdev.h"
#include "cos_status.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct CosJournal CosJournal;

typedef struct CosRecord {
  uint16_t kind;
  uint16_t len;
  uint64_t seq;
  uint64_t tick; /* logical time given by the caller; the core never reads a clock */
  uint8_t prev[32];
  uint8_t chain[32];
  uint8_t payload[COS_PAYLOAD_MAX];
} CosRecord;

size_t cos_journal_bytes(void);
/* format = true writes a fresh journal. Otherwise the log is recovered and the stored chain tail is checked:
 * COS_E_NOT_FOUND = never formatted, COS_E_CORRUPT = a hash or structure check failed. *out is set only on COS_OK. */
CosStatus cos_journal_open(void *mem, size_t len, const CosBlockDev *dev, bool format, CosJournal **out);
CosStatus cos_journal_append(CosJournal *j, uint16_t kind, const void *payload, uint16_t len, uint64_t tick);
CosStatus cos_journal_read(CosJournal *j, uint64_t seq, CosRecord *out);
CosStatus cos_journal_verify(CosJournal *j, uint64_t *good, uint64_t *bad_seq); /* walks every record; COS_E_CORRUPT names the first bad one */
uint64_t cos_journal_count(const CosJournal *j);
uint64_t cos_journal_capacity(const CosJournal *j);
void cos_journal_head(CosJournal *j, uint8_t out[32]); /* chain value of the newest record (the genesis value when empty) */
uint64_t cos_journal_contention(const CosJournal *j);        /* times an append had to wait for another writer */

#ifdef __cplusplus
}
#endif
#endif
