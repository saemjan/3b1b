/* A RAM block device with a power cut: after `budget` writes the next write is lost (or torn: half a sector lands), and every later call fails
 * until c17_ram_reboot(). Test-only. */
#ifndef C17_RAMDEV_H
#define C17_RAMDEV_H
#include <stdbool.h>
#include <string.h>

#include "../c17/cos_blockdev.h"

typedef struct RamDev {
  uint8_t *img;
  uint32_t nblocks;
  long budget; /* writes still allowed; negative = unlimited */
  int tear;    /* when the power fails: 0 = the write is lost, 1 = the first 256 bytes of the sector land, 2 = only the first 100 */
  bool dead;
  long writes;
  long flushes;
} RamDev;

static int ram_read(void *c, uint32_t blk, uint8_t *buf) {
  RamDev *d = (RamDev *)c;
  if (blk >= d->nblocks) return -1;
  memcpy(buf, d->img + (size_t)blk * COS_BLOCK_SIZE, COS_BLOCK_SIZE);
  return 0;
}
static int ram_write(void *c, uint32_t blk, const uint8_t *buf) {
  RamDev *d = (RamDev *)c;
  if (blk >= d->nblocks || d->dead) return -1;
  if (d->budget == 0) {
    d->dead = true;
    if (d->tear) memcpy(d->img + (size_t)blk * COS_BLOCK_SIZE, buf, d->tear == 1 ? 256u : 100u);
    return -1;
  }
  if (d->budget > 0) d->budget--;
  d->writes++;
  memcpy(d->img + (size_t)blk * COS_BLOCK_SIZE, buf, COS_BLOCK_SIZE);
  return 0;
}
static int ram_flush(void *c) {
  RamDev *d = (RamDev *)c;
  if (d->dead) return -1;
  d->flushes++;
  return 0;
}
static inline CosBlockDev ram_dev(RamDev *d) {
  CosBlockDev b = {d, d->nblocks, ram_read, ram_write, ram_flush};
  return b;
}
static inline void ram_reboot(RamDev *d) {
  d->dead = false;
  d->budget = -1;
}
#endif
