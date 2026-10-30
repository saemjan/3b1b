/* core/src/grow.c — Bounded Quarantine Store (Step 13)
 * Doctrine: Zero-heap, fixed bounds, fail-closed.
 * This module manages the in-memory quarantine slots. 
 * It does NOT touch the filesystem; that is the job of the edge tools.
 */
#include "grow.h"
#include <stdint.h>
#include <string.h>
#include <stdbool.h>

#define GROW_QUARANTINE_SLOTS 64
#define GROW_HASH_LEN 32
#define GROW_MAX_CASES 1024

typedef struct {
    uint8_t hash[GROW_HASH_LEN];
    uint32_t cases;
    bool promoted;
    bool used;
} grow_slot_t;

static grow_slot_t g_quarantine[GROW_QUARANTINE_SLOTS];
static uint32_t g_quarantine_count = 0;

void grow_init(void) {
    memset(g_quarantine, 0, sizeof(g_quarantine));
    g_quarantine_count = 0;
}

/* Learn: Record a new hypothesis hash. Returns slot index or -1 if full. */
int32_t grow_learn(const uint8_t *hash, uint32_t hash_len) {
    if (!hash || hash_len != GROW_HASH_LEN) return -1;
    
    /* Check if already exists */
    for (uint32_t i = 0; i < GROW_QUARANTINE_SLOTS; i++) {
        if (g_quarantine[i].used && memcmp(g_quarantine[i].hash, hash, GROW_HASH_LEN) == 0) {
            return (int32_t)i;
        }
    }
    
    /* Find empty slot */
    for (uint32_t i = 0; i < GROW_QUARANTINE_SLOTS; i++) {
        if (!g_quarantine[i].used) {
            memcpy(g_quarantine[i].hash, hash, GROW_HASH_LEN);
            g_quarantine[i].cases = 1;
            g_quarantine[i].promoted = false;
            g_quarantine[i].used = true;
            if (i >= g_quarantine_count) g_quarantine_count = i + 1;
            return (int32_t)i;
        }
    }
    
    return -1; /* Exhaustion: refusal (A8) */
}

/* Recall: Find a hypothesis by hash. Returns slot index or -1. */
int32_t grow_recall(const uint8_t *hash, uint32_t hash_len) {
    if (!hash || hash_len != GROW_HASH_LEN) return -1;
    for (uint32_t i = 0; i < GROW_QUARANTINE_SLOTS; i++) {
        if (g_quarantine[i].used && memcmp(g_quarantine[i].hash, hash, GROW_HASH_LEN) == 0) {
            return (int32_t)i;
        }
    }
    return -1;
}

/* Distill: Increment case count. If >= min_cases, mark ready for promotion. */
bool grow_distill(int32_t slot_idx, uint32_t min_cases) {
    if (slot_idx < 0 || slot_idx >= GROW_QUARANTINE_SLOTS) return false;
    if (!g_quarantine[slot_idx].used) return false;
    
    if (g_quarantine[slot_idx].cases < GROW_MAX_CASES) {
        g_quarantine[slot_idx].cases++;
    }
    
    if (g_quarantine[slot_idx].cases >= min_cases) {
        g_quarantine[slot_idx].promoted = true;
    }
    return true;
}

/* Get slot data for reporting */
bool grow_get_slot(int32_t slot_idx, uint8_t *out_hash, uint32_t *out_cases, bool *out_promoted) {
    if (slot_idx < 0 || slot_idx >= GROW_QUARANTINE_SLOTS) return false;
    if (!g_quarantine[slot_idx].used) return false;
    
    if (out_hash) memcpy(out_hash, g_quarantine[slot_idx].hash, GROW_HASH_LEN);
    if (out_cases) *out_cases = g_quarantine[slot_idx].cases;
    if (out_promoted) *out_promoted = g_quarantine[slot_idx].promoted;
    return true;
}

uint32_t grow_count(void) {
    return g_quarantine_count;
}
