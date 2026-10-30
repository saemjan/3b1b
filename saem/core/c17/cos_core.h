/* The sovereign core handle: everything the kernel keeps lives in ONE caller-supplied block of memory (zero heap, zero globals).
 * The caller asks cos_core_bytes(), provides that much 64-byte-aligned memory, and opens a core in it. Many cores can exist side by side.
 *   frozen flag + counters + quarantine mask (hot, atomic, one cache line each) | the sealed tables | the audit journal
 * Every call: frozen? -> seal intact? -> method known? -> not quarantined? -> Zone 0 scan -> verdict. Reject, Quarantine, Freeze: see docs/ARCHITECTURE.md. */
#ifndef COS_CORE_H
#define COS_CORE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "cos_blockdev.h"
#include "cos_gate.h"
#include "cos_journal.h"
#include "cos_seal.h"
#include "cos_status.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum CosZone { COS_ZONE_ACCEPT = 0, COS_ZONE_REJECT = 1, COS_ZONE_QUARANTINE = 2, COS_ZONE_FREEZE = 3 } CosZone;
typedef enum CosFreezeReason { COS_FREEZE_NONE = 0, COS_FREEZE_SEAL = 1, COS_FREEZE_JOURNAL = 2, COS_FREEZE_INVARIANT = 3, COS_FREEZE_MANUAL = 4 } CosFreezeReason;
typedef enum CosEvent { COS_EV_OPEN = 1, COS_EV_FREEZE = 2, COS_EV_QUARANTINE = 3, COS_EV_RELEASE = 4, COS_EV_USER = 256 } CosEvent;

typedef struct CosVerdict {
  CosZone zone;
  CosStatus status;
  CosRule rule;
  uint32_t offset; /* byte offset of the first violation, for REJECT by the scan */
  uint16_t method;
} CosVerdict;

typedef struct CosConfig {
  CosSealInput seal;              /* the tables this core is bound to; they must stay alive and unchanged while the core is open */
  uint8_t expected_digest[32];    /* from the release tool (tools/seal.py) */
  uint8_t expected_tag[32];
  const uint8_t *key;             /* the provisioned HMAC key; used to verify the tag at open, not kept */
  size_t keylen;
  CosBlockDev journal_dev;
  bool format_journal;            /* true on first use of a device */
  uint64_t tick;                  /* logical time for the open record */
} CosConfig;

typedef struct CosCoreStats {
  uint64_t calls, accepted, rejected, quarantined;
  uint64_t journal_records;
  uint32_t frozen_reason; /* 0 when running */
} CosCoreStats;

typedef struct CosCore CosCore;

size_t cos_core_bytes(void);
/* Refuses to start (and says why) if the tables do not match the signed digest and tag (COS_E_CORRUPT, COS_E_DENIED), the method table is
 * not sorted or the key shorter than 16 bytes (COS_E_INVALID), or the journal chain is broken (COS_E_CORRUPT). A quarantine recorded in the
 * journal is still in force after a restart. *out is set only on COS_OK.
 * A broken journal device does not freeze the gate (rejecting bad input needs no receipt) but every action that needs a receipt, an audit
 * record or a release, fails with COS_E_IO until the core is reopened: no receipt, no action. */
CosStatus cos_core_open(void *mem, size_t len, const CosConfig *cfg, CosCore **out);
CosVerdict cos_core_gate(CosCore *c, uint16_t method, const void *in, size_t n, uint64_t tick);
CosStatus cos_core_audit(CosCore *c, uint16_t kind, const void *payload, uint16_t len, uint64_t tick); /* kind >= COS_EV_USER; COS_E_FROZEN when frozen */
CosStatus cos_core_verify(CosCore *c, uint64_t tick); /* the monitor: walks the journal chain; a broken chain freezes the core (COS_FREEZE_JOURNAL) */
bool cos_core_quarantined(const CosCore *c, uint16_t method);
CosStatus cos_core_freeze(CosCore *c, CosFreezeReason why, uint64_t tick);                            /* the first reason wins */
bool cos_core_frozen(const CosCore *c, uint32_t *why);
CosStatus cos_core_release(CosCore *c, uint16_t method, const char *approver, uint64_t tick);         /* a person (1..64 bytes of clean text) lifts a quarantine; journaled first */
void cos_core_stats(const CosCore *c, CosCoreStats *out);
CosJournal *cos_core_journal(CosCore *c);

#ifdef __cplusplus
}
#endif
#endif
