/* QCOS sovereign kernel: every capacity lives here, as in xv6's param.h.
 * C17, no heap, no floating point. Changing a number here changes the seal (see cos_seal.c), on purpose.
 * Adapted from xv6-riscv (MIT): kernel/param.h. Rewritten in C17 for the Saem sovereign kernel. */
#ifndef COS_LIMITS_H
#define COS_LIMITS_H

#ifdef __cplusplus
#define COS_STATIC_ASSERT(c, m) static_assert(c, m)
#else
#define COS_STATIC_ASSERT(c, m) _Static_assert(c, m)
#endif

#define COS_WORKING_LIMIT 32u    /* L1: active registers per node */
#define COS_EPISODIC_RING 64u    /* L2: episodic slots per node (a power of two) */
#define COS_REG_DATA 40u         /* payload bytes of one register or episode */
#define COS_CACHE_LINE 64u       /* hot shared fields are aligned to this */
#define COS_POOL_MAX 1048576u    /* largest pool; handles carry a 32-bit index */

#define COS_BLOCK_SIZE 512u      /* journal block size: one sector */
#define COS_LOG_BLOCKS 30u       /* most blocks in one journal transaction (xv6 LOGSIZE) */
#define COS_REC_HEADER 88u       /* record header bytes inside one block */
#define COS_PAYLOAD_MAX (COS_BLOCK_SIZE - COS_REC_HEADER) /* 424 */
#define COS_HOME_START (2u + COS_LOG_BLOCKS)              /* first record block: 0 superblock, 1 log header, 2.. log data */

#define COS_MAX_INPUT 65536u     /* gate: bytes in one request */
#define COS_MAX_DEPTH 32u        /* gate: bracket nesting */
#define COS_MAX_METHODS 256u     /* gate: method ids 0..255 */
#define COS_QUARANTINE_AFTER 8u  /* gate: rejects from one method before it is quarantined */

COS_STATIC_ASSERT((COS_EPISODIC_RING & (COS_EPISODIC_RING - 1u)) == 0u, "episodic ring must be a power of two");
COS_STATIC_ASSERT(COS_WORKING_LIMIT >= 1u && COS_WORKING_LIMIT <= 250u, "register index must fit in a byte with room for a sentinel");
COS_STATIC_ASSERT(COS_BLOCK_SIZE == 512u, "journal layout assumes 512-byte blocks");
COS_STATIC_ASSERT(COS_REC_HEADER + 1u < COS_BLOCK_SIZE, "a record must have room for a payload");
COS_STATIC_ASSERT(COS_MAX_DEPTH <= 32u, "bracket stack is one 32-bit word");
COS_STATIC_ASSERT(COS_MAX_METHODS == 256u, "method ids are 8-bit table indexes");

#endif
