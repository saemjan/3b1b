/* Write-ahead redo log: a transaction of up to COS_LOG_BLOCKS blocks reaches the medium completely or not at all.
 * Adapted from xv6-riscv (MIT): kernel/log.c (begin_op, log_write, commit, install_trans, recover_from_log).
 * Rewritten in C17 for the Saem sovereign kernel. Two changes: the header carries SHA-256 hashes, so a torn header or a lying
 * device is DETECTED instead of trusted, and a full transaction returns COS_E_FULL instead of panicking.
 * One writer at a time (the journal serialises). Layout on the device: block log_start = header, log_start+1.. = the logged blocks. */
#ifndef COS_WAL_H
#define COS_WAL_H
#include <stddef.h>
#include <stdint.h>

#include "cos_blockdev.h"
#include "cos_status.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct CosWal CosWal;

size_t cos_wal_bytes(void);
CosWal *cos_wal_init(void *mem, size_t len, const CosBlockDev *dev, uint32_t log_start); /* NULL on bad memory or a device too small */
CosStatus cos_wal_recover(CosWal *w, uint32_t *replayed); /* run at every start: finishes a committed transaction, ignores an uncommitted one */
CosStatus cos_wal_begin(CosWal *w);
CosStatus cos_wal_put(CosWal *w, uint32_t blk, const uint8_t data[COS_BLOCK_SIZE]); /* absorbs a repeated block; COS_E_FULL past the limit */
CosStatus cos_wal_commit(CosWal *w);
void cos_wal_abort(CosWal *w);
uint64_t cos_wal_seq(const CosWal *w);

#ifdef __cplusplus
}
#endif
#endif
