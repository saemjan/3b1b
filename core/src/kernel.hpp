// core/src/kernel.hpp — Gen-4 Process Kernel
// Doctrine: Zero-heap static arenas, exact rational weights (Euler), four-axis slot anatomy, junk-fill reap.
#pragma once
#include "qcos.hpp"
#include "cog.hpp"
#include <cstdint>
#include <cstring>
#include <string>

namespace saem {

// --- Exact Weight (Euler Discipline) ---
// No floats. A probability is a ratio of integers.
struct Weight {
    int64_t num = 0, den = 1;
    bool is_hop() const { return num == den; }       // Weight == 1 exactly
    bool is_split() const { return num > 0 && num < den; } // 0 < w < 1 exactly
};

// --- Gate & Program ---
struct Gate { uint32_t op = 0; uint32_t arg = 0; };
struct Program {
    uint64_t reg[16] = {0};
    uint32_t steps = 0;
    bool halted = false;
    void hop(uint32_t idx, const Gate& g) {
        if (g.arg < 16) reg[g.arg] += (g.op == 1) ? 1ULL : (g.op == 2 ? (uint64_t)-1 : 0ULL);
        ++steps;
    }
    void split(uint32_t idx, const Gate& g, const Weight&) { hop(idx, g); }
    bool halted_() const { return halted; }
};

// --- Schedule (Fixed Bench, Zero-Heap) ---
constexpr int KSCHED_MAX = 64;
struct ScheduleStep { Weight w; Gate g; };
struct Schedule {
    ScheduleStep steps[KSCHED_MAX];
    uint32_t count = 0;
    bool push(const Weight& w, const Gate& g) {
        if (count >= KSCHED_MAX) return false; // A8: Refusal
        steps[count].w = w; steps[count].g = g; ++count; return true;
    }
    uint32_t size() const { return count; }
};

// --- Process ---
constexpr int KCOS_NAME_MAX = 64;
struct Proc {
    char name[KCOS_NAME_MAX] = {0};
    Program prog;
    Schedule schedule;
    uint32_t pc = 0;
    uint32_t slot = 0;
    bool done() const { return prog.halted_() || pc >= schedule.size(); }
    bool halted() const { return prog.halted_; }
};

// --- Four-Axis Slot Anatomy ---
struct PSlot {
    bool used = false;   // Lifetime: bench occupied
    bool valid = false;  // Validity: constructed, not zombie
    bool lock = false;   // Content lock: two-phase reap in progress
    uint32_t refs = 0;   // Refcount
    uint32_t id = 0;     // Identity: monotonic, never reused
    alignas(Proc) unsigned char raw[sizeof(Proc)];
};

// --- The Kernel ---
class Kernel {
public:
    Kernel() { qcos::g_arena.init(); }

    Proc* spawn(const char* name) {
        if (!name || std::strlen(name) >= KCOS_NAME_MAX) return nullptr;
        for (PSlot& s : procs_) {
            if (s.used) continue;
            s.used = true; s.valid = true; s.lock = false; s.refs = 0;
            s.id = ++next_id_;
            Proc* p = new (s.raw) Proc();
            std::strncpy(p->name, name, KCOS_NAME_MAX - 1);
            p->name[KCOS_NAME_MAX - 1] = 0;
            p->slot = s.id;
            return p;
        }
        return nullptr; // A8: Refusal
    }

    Proc* find(const char* name) {
        if (!name) return nullptr;
        for (PSlot& s : procs_)
            if (s.used && s.valid && std::strcmp(P(s)->name, name) == 0) return P(s);
        return nullptr;
    }

    bool add_step(Proc& p, const Weight& w, const Gate& g) {
        if (!p.schedule.push(w, g)) return false;
        return true;
    }

    void tick() {
        for (PSlot& s : procs_) {
            if (!s.used || !s.valid || s.lock) continue;
            Proc& p = *P(s);
            if (p.done()) continue;
            const ScheduleStep st = p.schedule.steps[p.pc];
            ++p.pc;
            if (st.w.is_hop()) p.prog.hop(p.pc - 1, st.g);
            else p.prog.split(p.pc - 1, st.g, st.w);
        }
    }

    bool set(Proc& p, uint32_t idx, uint64_t v) { if (idx >= 16) return false; p.prog.reg[idx] = v; return true; }
    bool get(const Proc& p, uint32_t idx, uint64_t& out) const { if (idx >= 16) return false; out = p.prog.reg[idx]; return true; }

    Json status() const {
        Json a = Json::array();
        for (const PSlot& s : procs_) {
            if (!s.used) continue;
            const Proc& p = *P(s);
            Json o = Json::object();
            o.set("name", std::string(p.name));
            o.set("pc", (int)p.pc);
            o.set("halt", p.halted());
            o.set("done", p.done());
            o.set("id", (int)s.id);
            a.push(o);
        }
        return a;
    }

    // Two-phase reap (ZOMBIE): Phase 1 mark zombie, Phase 2 destruct & junk-fill.
    bool reap(Proc& p) {
        PSlot* s = slot_of(p);
        if (!s || !s.used || s.lock) return false;
        s->valid = false; s->lock = true; // Phase 1: zombie
        p.~Proc();                        // Phase 2: destruct
        std::memset(s->raw, 0xA5, sizeof(s->raw)); // Junk-fill: no stale truth
        s->used = false; s->lock = false; s->refs = 0;
        return true;
    }

private:
    Proc* P(PSlot& s) { return reinterpret_cast<Proc*>(s.raw); }
    const Proc* P(const PSlot& s) const { return reinterpret_cast<const Proc*>(s.raw); }
    PSlot* slot_of(Proc& p) {
        for (PSlot& s : procs_) if (s.used && P(s) == &p) return &s;
        return nullptr;
    }
    PSlot procs_[32]; // Static pool: 32 working benches (A8)
    uint32_t next_id_ = 0;
};

} // namespace saem
