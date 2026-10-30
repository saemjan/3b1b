/* The only door from the sovereign kernel to storage. The caller fills it: a file with fsync, a flash partition, a RAM image in tests.
 * Contract: write() may reach the medium in any order until flush() returns 0; after flush() everything written before it is durable. */
#ifndef COS_BLOCKDEV_H
#define COS_BLOCKDEV_H
#include <stdint.h>

#include "cos_limits.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct CosBlockDev {
  void *ctx;
  uint32_t nblocks;
  int (*read)(void *ctx, uint32_t blk, uint8_t *buf);        /* buf has COS_BLOCK_SIZE bytes; returns 0 on success */
  int (*write)(void *ctx, uint32_t blk, const uint8_t *buf); /* returns 0 on success */
  int (*flush)(void *ctx);                                   /* barrier; returns 0 on success */
} CosBlockDev;

#ifdef __cplusplus
}
#endif
#endif
