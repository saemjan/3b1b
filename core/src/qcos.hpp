// core/src/qcos.hpp — Gen-4 Constitutional Core Header
// LAW: MEANING != REPRESENTATION != EXECUTION != HARDWARE.
// Doctrine: Zero-heap fixed arenas, fail-closed gates, Landauer pricing, provenance per transition.
#pragma once
#include "cog.hpp" // Your JSON library
#include <cstdint>
#include <cstring>
#include <string>
#include <algorithm>

namespace saem {
namespace qcos {

// --- Caps (One Ruler: qcos.cxn @cap) ---
constexpr int WORKING_LIMIT  = 32;
constexpr int EPISODIC_LIMIT = 64;
constexpr int KEY_MAX        = 23;
constexpr int NAME_MAX       = 64;
constexpr int CIR_STEPS      = 4096;
constexpr int PROV_LIMIT     = 64;
constexpr int SOUL_HEX       = 64;

// --- Refusal Codes ---
constexpr int ZPASS    = 0;
constexpr int ZBAD     = 400;
constexpr int ZGUARD   = 403;
constexpr int ZUNKNOWN = 404;
constexpr int ZTOOLONG = 413;
constexpr int ZBUDGET  = 429;

// --- A1 Rulers (Inline for header stability) ---
inline std::string jsnum(double v) {
    char b[64];
    if (v == (double)(long long)v && v < 1e15 && v > -1e15) {
        std::snprintf(b, sizeof b, "%lld", (long long)v);
        return std::string(b);
    }
    std::snprintf(b, sizeof b, "%.17g", v);
    return std::string(b);
}

inline bool finite_num(const Json& j) {
    if (j.isNum()) { double v = j.asNum(); return v == v && v != 1.0/0.0 && v != -1.0/0.0; }
    if (j.isArr()) { for (size_t i = 0; i < j.arr().size(); ++i) if (!finite_num(j.arr()[i])) return false; return true; }
    if (j.isObj()) { for (size_t i = 0; i < j.obj().size(); ++i) if (!finite_num(j.obj()[i].second)) return false; return true; }
    return true;
}

// --- Landauer Arena ---
struct ArenaRec { uint8_t op; uint32_t idx; uint32_t id; };
struct Arena {
    uint64_t bits_erased = 0;      // A3: Priced erasure
    uint64_t debt_refusals = 0;    // A8: Exhaustion is refusal
    uint32_t next_id = 0;          // Identity, never reused
    uint32_t rec_head = 0, rec_count = 0;
    ArenaRec recs[256];
    void init() { bits_erased = 0; debt_refusals = 0; next_id = 0; rec_head = 0; rec_count = 0; }
    void record(uint8_t op, uint32_t idx, uint32_t id) {
        recs[rec_head % 256] = ArenaRec{op, idx, id};
        ++rec_head; if (rec_count < 256) ++rec_count;
    }
};

// --- Verdict ---
struct Verdict { bool ok = true; std::string error; int code = ZPASS; };

// --- L1 Working Store ---
struct WSlot {
    bool used = false;
    char key[KEY_MAX + 1] = {0};
    char soul[SOUL_HEX + 1] = {0}; // SHA-256 fingerprint of the value
    uint32_t id = 0;
    Json value;
};

struct Working {
    WSlot s[WORKING_LIMIT];

    // Priced overwrite (A3)
    bool latch(const char* key, const Json& v) {
        if (!key || std::strlen(key) == 0 || std::strlen(key) > KEY_MAX) return false;
        if (!finite_num(v)) return false; // Fail-closed on non-finite
        
        Arena& a = g_arena;
        // Overwrite path
        for (int i = 0; i < WORKING_LIMIT; i++) {
            if (s[i].used && std::strcmp(s[i].key, key) == 0) {
                a.bits_erased += 8ull * (uint64_t)std::string(s[i].key).size(); // Price the erasure
                a.record(2, (uint32_t)i, s[i].id); // OP_FREE
                s[i].value = v;
                // set_soul(i, v); // Deferred to full SHA integration
                a.record(1, (uint32_t)i, s[i].id); // OP_ALLOC
                return true;
            }
        }
        // Fresh slot path
        for (int i = 0; i < WORKING_LIMIT; i++) {
            if (!s[i].used) {
                s[i].used = true;
                std::strncpy(s[i].key, key, KEY_MAX);
                s[i].key[KEY_MAX] = 0;
                s[i].value = v;
                s[i].id = ++a.next_id;
                a.record(1, (uint32_t)i, s[i].id);
                return true;
            }
        }
        a.debt_refusals++; // A8: Refusal, never growth
        return false;
    }

    Json read(const char* key) const {
        for (int i = 0; i < WORKING_LIMIT; i++)
            if (s[i].used && std::strcmp(s[i].key, key) == 0) return s[i].value;
        return Json();
    }

    bool has(const char* key) const {
        for (int i = 0; i < WORKING_LIMIT; i++)
            if (s[i].used && std::strcmp(s[i].key, key) == 0) return true;
        return false;
    }

    size_t size() const {
        size_t n = 0;
        for (int i = 0; i < WORKING_LIMIT; i++) n += s[i].used ? 1 : 0;
        return n;
    }

    Json snapshot() const {
        Json a = Json::array();
        for (int i = 0; i < WORKING_LIMIT; i++) {
            if (!s[i].used) continue;
            Json e = Json::object();
            e.set("key", std::string(s[i].key));
            e.set("value", s[i].value);
            a.push(e);
        }
        return a;
    }
};

// --- L2 Episodic Ring ---
struct Episodic {
    Json r[EPISODIC_LIMIT];
    uint64_t head = 0, count = 0;
    void push(const Json& e) {
        uint32_t idx = (uint32_t)(head % EPISODIC_LIMIT);
        r[idx] = e;
        ++head; ++count;
    }
    Json recent(int n) const {
        Json out = Json::array();
        if (count == 0 || n <= 0) return out;
        uint64_t take = (uint64_t)n < count ? (uint64_t)n : count;
        for (uint64_t k = 0; k < take; k++)
            out.push(r[(head - 1 - k) % EPISODIC_LIMIT]);
        return out;
    }
};

// --- Provenance Chain (A9) ---
struct Provenance {
    uint32_t tick = 0;
    std::string prev = std::string(64, '0');
    Json log = Json::array();

    void append(const char* op, const char* key, const char* method) {
        ++tick;
        Json f = Json::object();
        f.set("tick", (int)tick);
        f.set("op", op ? op : "");
        f.set("key", key ? key : "");
        f.set("method", method ? method : "");
        f.set("prev", prev);
        
        // Bounded ring with priced rotation
        if ((int)log.arr().size() >= PROV_LIMIT) {
            g_arena.bits_erased += 8ull * 128; // Price the dropped frame
            Json nl = Json::array();
            for (size_t i = 1; i < log.arr().size(); ++i) nl.push(log.arr()[i]);
            log = nl;
        }
        log.push(f);
        // prev = sha256_hex(canon(f)); // Deferred to Phase II hash integration
    }
};

// --- Globals (Defined in qcos_reg.cpp) ---
extern Arena g_arena;
extern Working g_working;
extern Episodic g_episodic;
extern Provenance g_prov;

// --- Zone 0 Gate ---
inline Verdict gate(const char* op, const Json& args, uint8_t kind) {
    Verdict v;
    if (!op) { v.ok = false; v.code = ZBAD; v.error = "null_op"; return v; }
    if (std::strlen(op) > NAME_MAX) { v.ok = false; v.code = ZTOOLONG; v.error = "op_too_long"; return v; }
    if (!finite_num(args)) { v.ok = false; v.code = ZBAD; v.error = "non_finite_args"; return v; }
    if (kind == 1 && g_working.size() >= WORKING_LIMIT) { // K_RESIDENT == 1
        v.ok = false; v.code = ZBUDGET; v.error = "working_exhausted"; return v;
    }
    return v;
}

} // namespace qcos
} // namespace saem
