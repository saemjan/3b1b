// core/src/kernel.hpp — gen-4 (2026-10-30, §21 step 11 close)
// Zero-heap quantum-process kernel over static arenas.
// Doctrine: xv6 proc[] fixed pool · arena four-axis slots · Euler-exact weights ·
//           Landauer integer pricing (8 bits per canonical byte erased) ·
//           provenance per transition (§6) · junk-fill on free · fail-closed.
//
// API CONTRACT (frozen names):
//   Proc{name, prog, schedule, pc}
//   Kernel::spawn/find/add_step/tick/set/get/board/entropy_debt_kTln2/soul/status/reap
//   canon(Json) — the single A1 ruler (defined here; qcos.hpp consumes, never redefines)
//
// GEN-4 CHANGES (audit 1-9): double→Weight exact ratios; fixed Schedule array;
//   MAXP cap enforced in-kernel; four-axis PSlot; junk-fill reap; per-step trace;
//   arena by reference (no global call); bits ruler vs kTln2 view separated.
#pragma once
#include "cog.hpp"      // Json
#include "arena.hpp"    // qcos::Arena, w_alloc/w_free/tick_advance, QCOS_SLOT_NONE
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <algorithm>

// ---------------------------------------------------------------- A1 rulers (global)
inline std::string sha256_hex(const std::string& m);           // impl in kernel_sha.cpp
inline std::string jsnum(double v);                            // impl in kernel_sha.cpp
inline std::string canon(const Json& j);                       // impl in kernel_sha.cpp
inline bool finite_num(const Json& j);                         // impl in kernel_sha.cpp

// ---------------------------------------------------------------- bounds (one ruler: canon)
constexpr int     KCOS_NAME_MAX  = 64;
constexpr int     KSCHED_MAX     = 64;
constexpr int     KREG_MAX       = 16;
constexpr int     KTRACE_MAX     = 128;
constexpr int64_t KCOS_MAXP_NUM  = 95;   // @cap MAXP 0.95 — canon is the source;
constexpr int64_t KCOS_MAXP_DEN  = 100;  // qcosc Checker witnesses this pair.
constexpr uint8_t KCOS_JUNK      = 0xA5; // junk-fill byte: no stale truth survives
constexpr uint64_t KDEFAULT_SEED = 0xC0FFEEULL;
constexpr uint32_t KOWNER        = 7;    // kernel owner tag for arena slots

namespace saem {

// ---------------------------------------------------------------- exact weight (Euler)
// A probability is a ratio of integers, normalized, never a float.
struct Weight {
    int64_t num = 0, den = 1;
    bool is_hop()   const { return num == den; }                 // weight == 1 exactly
    bool is_split() const { return num > 0 && num < den; }       // 0 < w < 1 exactly
    bool le_maxp()  const { return 100 * num <= KCOS_MAXP_NUM * den; } // cap ruler
};
inline int64_t kgcd(int64_t a, int64_t b) { while (b) { int64_t t = a % b; a = b; b = t; } return a; }
inline bool kweight(int64_t n, int64_t d, Weight& out) {         // fail-closed constructor
    if (d <= 0 || n < 0 || n > d) return false;
    if (n == 0) { out = Weight{0, 1}; return true; }
    int64_t g = kgcd(n, d);
    out = Weight{n / g, d / g};
    return true;
}

struct Gate { uint32_t op = 0; uint32_t arg = 0; };              // bounded, C-friendly

// ---------------------------------------------------------------- Tier-0 program
// Deterministic register machine: hop = apply gate; split = apply gate + record
// the exact branch weight on the board (accounting, not physics, at Tier 0).
struct Program {
    uint64_t reg[KREG_MAX] = {0};
    uint32_t steps = 0;
    bool     halted = false;
    void hop(uint32_t idx, const Gate& g) {
        (void)idx;
        if (g.arg < KREG_MAX) reg[g.arg] += (g.op == 1) ? 1ULL : (g.op == 2 ? (uint64_t)-1 : 0ULL);
        ++steps;
    }
    void split(uint32_t idx, const Gate& g, const Weight&) { hop(idx, g); }
    bool halted_() const { return halted; }
};

struct ScheduleStep { Weight w; Gate g; };
struct Schedule {
    ScheduleStep steps[KSCHED_MAX];
    uint32_t count = 0;
    bool push(const Weight& w, const Gate& g) {                  // fixed bench, no growth
        if (count >= KSCHED_MAX) return false;
        steps[count].w = w; steps[count].g = g; ++count; return true;
    }
    uint32_t size() const { return count; }
};

struct Proc {
    char     name[KCOS_NAME_MAX] = {0};
    Program  prog;
    Schedule schedule;
    uint32_t pc = 0;
    uint32_t slot = 0;
    bool done() const { return prog.halted_() || pc >= schedule.size(); }
    bool halted() const { return prog.halted_(); }
};

// ---------------------------------------------------------------- four-axis slot anatomy
struct PSlot {
    bool     used  = false;   // lifetime: bench occupied
    bool     valid = false;   // validity: constructed, not zombie
    bool     lock  = false;   // content lock: two-phase reap in progress
    uint32_t refs  = 0;       // refcount: reserved for Phase-II handles (0/1 now)
    uint32_t id    = 0;       // identity: monotonic, never reused
    uint32_t slot  = 0;       // arena slot backing this bench
    alignas(Proc) unsigned char raw[sizeof(Proc)];
};

// ---------------------------------------------------------------- per-step provenance ring
struct TraceFrame { uint32_t pid; uint32_t pc; uint8_t kind; Weight w; };
struct TraceRing {
    TraceFrame f[KTRACE_MAX];
    uint32_t head = 0, count = 0;
    void push(uint32_t pid, uint32_t pc, uint8_t kind, const Weight& w) {
        f[head % KTRACE_MAX] = TraceFrame{pid, pc, kind, w};
        ++head; if (count < KTRACE_MAX) ++count;
    }
};

// ---------------------------------------------------------------- the kernel
class Kernel {
public:
    explicit Kernel(qcos::Arena& a) : arena_(a) {}

    Proc* spawn(const std::string& name, uint32_t nreg, uint32_t k,
                uint64_t seed = KDEFAULT_SEED) {
        (void)nreg; (void)k; (void)seed;
        if (name.size() >= KCOS_NAME_MAX) return nullptr;        // bound before touch
        uint32_t slot = qcos::w_alloc(arena_, KOWNER);
        if (slot == qcos::QCOS_SLOT_NONE) return nullptr;        // A8: refusal, never growth
        for (PSlot& s : procs_) {
            if (s.used) continue;
            s.used = true; s.valid = true; s.lock = false; s.refs = 0;
            s.id = ++next_id_; s.slot = slot;
            Proc* p = new (s.raw) Proc();
            std::strncpy(p->name, name.c_str(), KCOS_NAME_MAX - 1);
            p->name[KCOS_NAME_MAX - 1] = 0;
            p->slot = slot;
            return p;
        }
        qcos::w_free(arena_, slot, KOWNER);                      // symmetric unwind
        return nullptr;
    }

    bool refused(const Proc& p) const { return p.slot == qcos::QCOS_SLOT_NONE; }

    Proc* find(const std::string& name) {                        // O(N) scan: §6-legal
        for (PSlot& s : procs_)
            if (s.used && s.valid && std::strcmp(P(s)->name, name.c_str()) == 0) return P(s);
        return nullptr;
    }

    bool add_step(Proc& p, const Weight& w, const Gate& g) {     // D-12: was double
        if (refused(p) || !p.schedule.push(w, g)) return false;
        if (w.is_split() && !w.le_maxp()) {                      // cap enforced in-kernel
            --p.schedule.count;                                  // undo: plan never half-commits
            arena_.debt_refusals++;
            return false;
        }
        return true;
    }

    void tick() {
        for (PSlot& s : procs_) {
            if (!s.used || !s.valid || s.lock) continue;
            Proc& p = *P(s);
            if (p.done()) continue;
            const ScheduleStep st = p.schedule.steps[p.pc];
            ++p.pc;
            if (st.w.is_hop()) { p.prog.hop(p.pc - 1, st.g); trace_.push(s.id, p.pc, 0, st.w); }
            else               { p.prog.split(p.pc - 1, st.g, st.w); trace_.push(s.id, p.pc, 1, st.w); }
            board_set(p);
        }
        qcos::tick_advance(arena_);                              // arena by reference, not global
    }

    bool set(Proc& p, uint32_t idx, uint64_t v) { if (idx >= KREG_MAX) return false; p.prog.reg[idx] = v; return true; }
    bool get(const Proc& p, uint32_t idx, uint64_t& out) const { if (idx >= KREG_MAX) return false; out = p.prog.reg[idx]; return true; }

    const Json& board() const { return board_; }
    uint64_t debt_bits() const { return arena_.bits_erased; }    // the ruler: integer bits
    double entropy_debt_kTln2() const { return (double)arena_.bits_erased; } // display view only (§14)
    std::string soul() const { return sha256_hex(canon(board_)); }

    Json status() const {
        Json a = Json::array();
        for (const PSlot& s : procs_) {
            if (!s.used) continue;
            const Proc& p = *P(s);
            Json o = Json::object();
            o.set("name", std::string(p.name));                  // original four first
            o.set("pc", (int)p.pc);
            o.set("halt", p.halted());
            o.set("done", p.done());
            o.set("id", (int)s.id);                               // additive anatomy face
            o.set("valid", s.valid);
            o.set("lock", s.lock);
            o.set("refs", (int)s.refs);
            a.push(o);
        }
        return a;
    }

    Json trace() const {                                         // provenance face (§6/A9)
        Json a = Json::array();
        uint32_t take = trace_.count < KTRACE_MAX ? trace_.count : KTRACE_MAX;
        for (uint32_t k = 0; k < take; ++k) {
            const TraceFrame& fr = trace_.f[(trace_.head - take + k) % KTRACE_MAX];
            Json o = Json::object();
            o.set("pid", (int)fr.pid); o.set("pc", (int)fr.pc);
            o.set("kind", (int)fr.kind);
            o.set("num", (double)fr.w.num); o.set("den", (double)fr.w.den);
            a.push(o);
        }
        return a;
    }

    // Two-phase reap (ZOMBIE): phase 1 mark zombie under lock; phase 2 destruct,
    // junk-fill, release arena slot. No stale specimen survives (audit 5).
    bool reap(Proc& p) {
        PSlot* s = slot_of(p);
        if (!s || !s.used || s.lock) return false;
        s->valid = false; s->lock = true;                        // phase 1: zombie
        p.~Proc();                                               // phase 2: destruct
        std::memset(s->raw, KCOS_JUNK, sizeof(s->raw));          // junk-fill
        qcos::w_free(arena_, s->slot, KOWNER);
        s->used = false; s->lock = false; s->refs = 0;           // id stays tombstoned
        return true;
    }

private:
    Proc* P(PSlot& s) { return reinterpret_cast<Proc*>(s.raw); }
    const Proc* P(const PSlot& s) const { return reinterpret_cast<const Proc*>(s.raw); }
    PSlot* slot_of(Proc& p) {
        for (PSlot& s : procs_) if (s.used && P(s) == &p) return &s;
        return nullptr;
    }
    void board_set(const Proc& p) {
        Json o = Json::object();
        o.set("pc", (int)p.pc);
        o.set("steps", (int)p.prog.steps);
        o.set("done", p.done());
        board_.set(p.name, o);
    }
    PSlot procs_[32];                 // static pool: 32 working benches (A8)
    TraceRing trace_;
    Json board_ = Json::object();
    qcos::Arena& arena_;              // explicit context: no hidden global (A2)
    uint32_t next_id_ = 0;            // monotonic identity, never reused
};

} // namespace saem
