// core/src/arena.hpp — QCOS static arena + slot anatomy (os.md P2/P3, §21 step 11a)
// MEANING: caps from qcos.cxn v0.5.0. EXECUTION: linker/static storage only.
// Doctrine: kalloc.c (junk-fill, bounds panic, double-free detection),
// buddy.c (bitmap lineage), buf.h/proc.h (four-axis anatomy),
// sleeplock.h (ownership-recorded locks), Landauer (erasure = priced bits).
// Zero heap. Exhaustion = refusal (QCOS_SLOT_NONE -> caller prices the debt).
#ifndef QCOS_ARENA_HPP
#define QCOS_ARENA_HPP

#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>

// Caps MIRROR the canon; the ruler is qcos.cxn (Checker enforces the values;
// tests/test_caps.c at step 14 asserts these macros equal the canon caps).
#define QCOS_WORKING_LIMIT   32u
#define QCOS_EPISODIC_LIMIT  64u
#define QCOS_SLOT_PAYLOAD    64u
#define QCOS_PROV_RING       16u
#define QCOS_SLOT_NONE       0xFFFFFFFFu
#define QCOS_JUNK_FREE       0x01   // kalloc precedent: freed memory reads 01
#define QCOS_JUNK_ALLOC      0x05   // kalloc precedent: fresh memory reads 05

namespace qcos {

// Invariant 3: absolute node freeze. A test handler may longjmp out;
// if it returns, we abort anyway — a panic that continues is not a panic.
using panic_fn = void (*)(const char *);
inline panic_fn g_panic = nullptr;
[[noreturn]] inline void arena_panic(const char *why) {
    if (g_panic) g_panic(why);
    std::fprintf(stderr, "[arena] FREEZE: %s\n", why);
    std::abort();
}

// Four-axis object anatomy (xv6 proc.h / buf.h precedent).
struct Slot {
    uint32_t identity;                 // monotonic, never reused
    uint16_t refcount;                 // lifetime axis
    uint8_t  valid;                    // never consume invalid
    uint8_t  pad_;
    uint32_t lock_owner;               // content lock, ownership recorded (0 = free)
    uint32_t tick;                     // episodic clock at alloc
    uint8_t  payload[QCOS_SLOT_PAYLOAD];
};

struct Prov { uint32_t tick, op, slot, identity; };   // (step,op,keys,pre) ring, A9

struct Lock { uint8_t held; uint32_t owner; };        // structural lock
inline void lock_acquire(Lock &l, uint32_t who) {
    if (l.held) arena_panic("arena: double acquire (structural lock)");
    l.held = 1; l.owner = who;
}
inline void lock_release(Lock &l, uint32_t who) {
    if (!l.held || l.owner != who) arena_panic("arena: release by non-owner");
    l.held = 0; l.owner = 0;
}

struct Arena {
    Slot     w[QCOS_WORKING_LIMIT];    // L1 working store
    uint32_t w_occ;                    // bitmap lineage, one bit per slot
    Lock     w_lock;
    Slot     e[QCOS_EPISODIC_LIMIT];   // L2 episodic ring
    uint64_t e_occ;
    uint32_t e_head, e_tail;
    Lock     e_lock;
    uint32_t next_id;                  // monotonic identity source
    uint32_t tick;                     // episodic clock
    uint64_t bits_erased;              // Landauer ledger, INTEGER bits
    uint64_t debt_refusals;            // priced refusals (A3/A5)
    Prov     prov[QCOS_PROV_RING];
    uint32_t prov_head;

    void init() {
        std::memset(this, 0, sizeof *this);
        for (uint32_t i = 0; i < QCOS_WORKING_LIMIT; i++) junk(w[i]);
        for (uint32_t i = 0; i < QCOS_EPISODIC_LIMIT; i++) junk(e[i]);
    }
    static void junk(Slot &s) {
        s.valid = 0; s.refcount = 0; s.lock_owner = 0;
        std::memset(s.payload, QCOS_JUNK_FREE, sizeof s.payload);
    }
    void record(uint32_t op, uint32_t slot, uint32_t identity) {
        Prov &p = prov[prov_head % QCOS_PROV_RING];
        p.tick = tick; p.op = op; p.slot = slot; p.identity = identity;
        ++prov_head;
    }
};
inline Arena g_arena;                  // C++17 inline variable: one instance, no heap

enum : uint32_t { OP_ALLOC = 1, OP_FREE = 2, OP_EPI_PUSH = 3, OP_EVICTION = 4 };

// ---- L1 working store ------------------------------------------------------
inline uint32_t w_alloc(Arena &a, uint32_t who) {
    lock_acquire(a.w_lock, who);
    uint32_t idx = QCOS_SLOT_NONE;
    for (uint32_t i = 0; i < QCOS_WORKING_LIMIT; i++)          // O(N) literal scan
        if (!(a.w_occ & (1u << i))) { idx = i; break; }
    if (idx == QCOS_SLOT_NONE) {                               // refusal, never growth
        a.debt_refusals++;
        lock_release(a.w_lock, who);
        return QCOS_SLOT_NONE;
    }
    Slot &s = a.w[idx];
    a.w_occ |= 1u << idx;
    s.identity = ++a.next_id;
    s.refcount = 0; s.valid = 1; s.tick = a.tick; s.lock_owner = 0;
    std::memset(s.payload, QCOS_JUNK_ALLOC, sizeof s.payload);
    a.record(OP_ALLOC, idx, s.identity);
    lock_release(a.w_lock, who);
    return idx;
}

inline void w_free(Arena &a, uint32_t idx, uint32_t who) {
    if (idx >= QCOS_WORKING_LIMIT) arena_panic("arena: w_free out of bounds");
    lock_acquire(a.w_lock, who);
    if (!(a.w_occ & (1u << idx))) {                            // double-free detection
        lock_release(a.w_lock, who);
        arena_panic("arena: double free");
    }
    a.w_occ &= ~(1u << idx);
    uint32_t id = a.w[idx].identity;
    a.bits_erased += 8ull * QCOS_SLOT_PAYLOAD;                 // erasure is dissipation
    Arena::junk(a.w[idx]);
    a.record(OP_FREE, idx, id);
    lock_release(a.w_lock, who);
}

inline Slot *w_get(Arena &a, uint32_t idx) {                   // fail-closed read
    if (idx >= QCOS_WORKING_LIMIT) return nullptr;
    if (!(a.w_occ & (1u << idx))) return nullptr;
    if (!a.w[idx].valid) return nullptr;
    return &a.w[idx];
}

inline void slot_lock(Arena &a, uint32_t idx, uint32_t who) {
    Slot *s = w_get(a, idx);
    if (!s) arena_panic("arena: lock on dead slot");
    if (s->lock_owner) arena_panic("arena: content lock double acquire");
    s->lock_owner = who;
}
inline void slot_unlock(Arena &a, uint32_t idx, uint32_t who) {
    Slot *s = w_get(a, idx);
    if (!s || s->lock_owner != who) arena_panic("arena: content release by non-owner");
    s->lock_owner = 0;
}
inline void ref_inc(Arena &a, uint32_t idx) {
    Slot *s = w_get(a, idx);
    if (!s) arena_panic("arena: ref_inc on dead slot");
    ++s->refcount;
}
inline void ref_dec(Arena &a, uint32_t idx) {
    Slot *s = w_get(a, idx);
    if (!s) arena_panic("arena: ref_dec on dead slot");
    if (s->refcount == 0) arena_panic("arena: refcount underflow");
    --s->refcount;
}

// ---- L2 episodic ring (deterministic FIFO eviction) -------------------------
inline uint32_t e_push(Arena &a, uint32_t who) {
    lock_acquire(a.e_lock, who);
    uint32_t idx = QCOS_SLOT_NONE;
    if (a.e_head - a.e_tail < QCOS_EPISODIC_LIMIT) {
        idx = a.e_head % QCOS_EPISODIC_LIMIT;
        ++a.e_head;
    } else {
        for (uint32_t i = a.e_tail; i < a.e_head; i++) {       // oldest refcount-0 first
            Slot &s = a.e[i % QCOS_EPISODIC_LIMIT];
            if (s.refcount == 0) { idx = i % QCOS_EPISODIC_LIMIT; a.e_tail = i + 1; break; }
        }
        if (idx == QCOS_SLOT_NONE) {                           // all referenced: refuse
            a.debt_refusals++;
            lock_release(a.e_lock, who);
            return QCOS_SLOT_NONE;
        }
        a.bits_erased += 8ull * QCOS_SLOT_PAYLOAD;             // priced forgetting
        a.record(OP_EVICTION, idx, a.e[idx].identity);
    }
    Slot &s = a.e[idx];
    a.e_occ |= 1ull << idx;
    s.identity = ++a.next_id;
    s.refcount = 0; s.valid = 1; s.tick = a.tick; s.lock_owner = 0;
    std::memset(s.payload, QCOS_JUNK_ALLOC, sizeof s.payload);
    a.record(OP_EPI_PUSH, idx, s.identity);
    lock_release(a.e_lock, who);
    return idx;
}

inline Slot *e_get(Arena &a, uint32_t idx) {
    if (idx >= QCOS_EPISODIC_LIMIT) return nullptr;
    if (!(a.e_occ & (1ull << idx))) return nullptr;
    if (!a.e[idx].valid) return nullptr;
    return &a.e[idx];
}

inline void tick_advance(Arena &a) { ++a.tick; }

}  // namespace qcos
#endif  // QCOS_ARENA_HPP
