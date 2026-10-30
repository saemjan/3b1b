/* One status code for the whole sovereign kernel. Numbers 0..11 equal saem::nx::Err (core/src/nx/common.hpp) on purpose. */
#ifndef COS_STATUS_H
#define COS_STATUS_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum CosStatus {
  COS_OK = 0,
  COS_E_DENIED = 1,
  COS_E_EXPIRED = 2,
  COS_E_REVOKED = 3,
  COS_E_NOT_FOUND = 4,
  COS_E_EXISTS = 5,
  COS_E_FULL = 6,        /* a fixed table is full: an answer, not a crash */
  COS_E_CLOSED = 7,
  COS_E_INVALID = 8,     /* malformed argument */
  COS_E_FROZEN = 9,      /* the core is frozen */
  COS_E_DUPLICATE = 10,
  COS_E_UNVERIFIED = 11,
  COS_E_STALE = 12,      /* a handle whose slot was freed or reused */
  COS_E_CORRUPT = 13,    /* stored data failed its hash or structure check */
  COS_E_IO = 14,         /* the block device failed */
  COS_E_RANGE = 15,      /* arithmetic or index out of range */
  COS_E_TOO_BIG = 16,
  COS_E_FORBIDDEN = 17,  /* input fell in the Forbidden Zone */
  COS_E_UNKNOWN = 18,    /* unknown method */
  COS_E_ALIGN = 19,      /* memory handed in is misaligned or too small */
  COS_E_QUARANTINED = 20 /* the method is quarantined until a person lifts it */
} CosStatus;

static inline const char *cos_status_name(CosStatus s) {
  switch (s) {
    case COS_OK: return "ok";
    case COS_E_DENIED: return "denied";
    case COS_E_EXPIRED: return "expired";
    case COS_E_REVOKED: return "revoked";
    case COS_E_NOT_FOUND: return "not_found";
    case COS_E_EXISTS: return "exists";
    case COS_E_FULL: return "full";
    case COS_E_CLOSED: return "closed";
    case COS_E_INVALID: return "invalid";
    case COS_E_FROZEN: return "frozen";
    case COS_E_DUPLICATE: return "duplicate";
    case COS_E_UNVERIFIED: return "unverified";
    case COS_E_STALE: return "stale";
    case COS_E_CORRUPT: return "corrupt";
    case COS_E_IO: return "io";
    case COS_E_RANGE: return "range";
    case COS_E_TOO_BIG: return "too_big";
    case COS_E_FORBIDDEN: return "forbidden";
    case COS_E_UNKNOWN: return "unknown";
    case COS_E_ALIGN: return "align";
    case COS_E_QUARANTINED: return "quarantined";
  }
  return "?";
}

#ifdef __cplusplus
}
#endif
#endif
