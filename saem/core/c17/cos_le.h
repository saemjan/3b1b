/* Explicit little-endian field access, so stored bytes are the same on every machine. */
#ifndef COS_LE_H
#define COS_LE_H
#include <stdint.h>

static inline void cos_put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static inline void cos_put32(uint8_t *p, uint32_t v) { for (unsigned i = 0; i < 4; ++i) p[i] = (uint8_t)(v >> (8u * i)); }
static inline void cos_put64(uint8_t *p, uint64_t v) { for (unsigned i = 0; i < 8; ++i) p[i] = (uint8_t)(v >> (8u * i)); }
static inline uint16_t cos_get16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static inline uint32_t cos_get32(const uint8_t *p) { uint32_t v = 0; for (unsigned i = 0; i < 4; ++i) v |= (uint32_t)p[i] << (8u * i); return v; }
static inline uint64_t cos_get64(const uint8_t *p) { uint64_t v = 0; for (unsigned i = 0; i < 8; ++i) v |= (uint64_t)p[i] << (8u * i); return v; }

#endif
