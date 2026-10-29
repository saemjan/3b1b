// core/src/qcos.hpp — Gen-4 constitutional core header (2026-10-30, step 11b)
// LAW: MEANING != REPRESENTATION != EXECUTION != HARDWARE.
// Frozen faces (never change): snapshot byte-shape, selftest frozen names,
// gate messages, jsnum ruler. Additions are append-only.
#pragma once
#include "cog.hpp"
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <algorithm>

// ---------------------------------------------------------------- sha256 (stdlib-only)
inline std::string sha256_hex(const std::string& m) {
    static const uint32_t K[64] = {
        0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
        0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
        0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
        0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
        0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
        0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
        0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
        0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u};
    uint32_t h[8] = {0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u};
    uint64_t bitlen = (uint64_t)m.size() * 8ull;
    std::string p = m; p.push_back((char)0x80);
    while (p.size() % 64 != 56) p.push_back((char)0);
    for (int i = 7; i >= 0; --i) p.push_back((char)(bitlen >> (i * 8)));
    for (size_t off = 0; off < p.size(); off += 64) {
        uint32_t w[64];
        for (int i = 0; i < 16; ++i)
            w[i] = ((uint32_t)(uint8_t)p[off + i * 4] << 24) | ((uint32_t)(uint8_t)p[off + i * 4 + 1] << 16)
                 | ((uint32_t)(uint8_t)p[off + i * 4 + 2] << 8) | ((uint32_t)(uint8_t)p[off + i * 4 + 3]);
        for (int i = 16; i < 64; ++i) {
            uint32_t s0 = ((w[i-15] >> 7) | (w[i-15] << 25)) ^ ((w[i-15] >> 18) | (w[i-15] << 14)) ^ (w[i-15] >> 3);
            uint32_t s1 = ((w[i-2] >> 17) | (w[i-2] << 15)) ^ ((w[i-2] >> 19) | (w[i-2] << 13)) ^ (w[i-2] >> 10);
            w[i] = w[i-16] + s0 + w[i-7] + s1;
        }
        uint32_t a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],hh=h[7];
        for (int i = 0; i < 64; ++i) {
            uint32_t S1 = ((e >> 6) | (e << 26)) ^ ((e >> 11) | (e << 21)) ^ ((e >> 25) | (e << 7));
            uint32_t ch = (e & f) ^ ((~e) & g);
            uint32_t t1 = hh + S1 + ch + K[i] + w[i];
            uint32_t S0 = ((a >> 2) | (a << 30)) ^ ((a >> 13) | (a << 19)) ^ ((a >> 22) | (a << 10));
            uint32_t mj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t t2 = S0 + mj;
            hh=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
        }
        h[0]+=a; h[1]+=b; h[2]+=c; h[3]+=d; h[4]+=e; h[5]+=f; h[6]+=g; h[7]+=hh;
    }
    char out[65];
    for (int i = 0; i < 8; ++i) std::snprintf(out + i * 8, 9, "%08x", h[i]);
    out[64] = 0;
    return std::string(out);
}

// ---------------------------------------------------------------- A1/A6 number ruler
// Numbers print as the bridge ruler prints (JS Number toString): shortest
// round-trip decimal. Frozen witness: jsnum(0.1+0.2) == "0.30000000000000004".
inline std::string jsnum(double v) {
    char b[64];
    if (v == (double)(long long)v && v < 1e15 && v > -1e15) {
        std::snprintf(b, sizeof b, "%lld", (long long)v);
        return std::string(b);
    }
    for (int prec = 1; prec < 17; ++prec) {
        std::snprintf(b, sizeof b, "%.*g", prec, v);
        if (std::strtod(b, nullptr) == v) break;
    }
    return std::string(b);
}

// ---------------------------------------------------------------- canonical JSON (sorted keys)
inline std::string canon(const Json& j);
inline std::string canon(const Json& j) {
    if (j.isStr())  return "\"" + j.asStr() + "\"";
    if (j.isNum())  return jsnum(j.asNum());
    if (j.isBool()) return j.asBool() ? "true" : "false";
    if (j.isNil())  return "null";
    if (j.isArr()) {
        std::string s = "[";
        const auto& a = j.arr();
        for (size_t i = 0; i < a.size(); ++i) { if (i) s += ","; s += canon(a[i]); }
        return s + "]";
    }
    const auto& o = j.obj();
    std::vector<std::string> ks;
    for (const auto& kv : o) ks.push_back(kv.first);
    std::sort(ks.begin(), ks.end());
    std::string s = "{"; bool first = true;
    for (const auto& k : ks)
        for (const auto& kv : o)
            if (kv.first == k) {
                if (!first) s += ",";
                first = false;
                s += "\"" + k + "\":" + canon(kv.second);
                break;
            }
    return s + "}";
}

inline bool finite_num(const Json& j) {
    if (j.isNum()) { double v = j.asNum(); return v == v && v != 1.0/0.0 && v != -1.0/0.0; }
    if (j.isArr()) { for (size_t i = 0; i < j.arr().size(); ++i) if (!finite_num(j.arr()[i])) return false; return true; }
    if (j.isObj()) { for (size_t i = 0; i < j.obj().size(); ++i) if (!finite_num(j.obj()[i].second)) return false; return true; }
    return true;
}

namespace qcos {

// caps: one ruler (qcos.cxn @cap, enforced by tools/qcosc.py Checker)
constexpr int WORKING_LIMIT  = 32;
constexpr int EPISODIC_LIMIT = 64;
constexpr int KEY_MAX        = 23;
constexpr int NAME_MAX       = 64;
constexpr int CIR_STEPS      = 4096;
constexpr int PROV_LIMIT     = 64;
constexpr int ARENA_REC      = 256;
constexpr int SOUL_HEX       = 64;

constexpr int ZPASS = 0, ZBAD = 400, ZGUARD = 403, ZUNKNOWN = 404, ZTOOLONG = 413, ZBUDGET = 429;

constexpr uint8_t OP_ALLOC = 1, OP_FREE = 2, OP_EVICTION = 3, OP_EPI_PUSH = 4, OP_ROTATE = 5;

struct ArenaRec { uint8_t op; uint32_t idx; uint32_t id; };

struct Arena {
    uint64_t bits_erased = 0;      // Landauer ledger (A3)
    uint64_t debt_refusals = 0;    // A8: exhaustion is refusal, never growth
    uint32_t next_id = 0;          // identity, never reused
    uint32_t rec_head = 0, rec_count = 0;
    ArenaRec recs[ARENA_REC];
    void init() { bits_erased = 0; debt_refusals = 0; next_id = 0; rec_head = 0; rec_count = 0; }
    void record(uint8_t op, uint32_t idx, uint32_t id) {
        recs[rec_head % ARENA_REC] = ArenaRec{op, idx, id};
        ++rec_head;
        if (rec_count < ARENA_REC) ++rec_count;
    }
};
inline Arena g_arena;

struct Verdict { bool ok = true; std::string error; int code = ZPASS; };

// ---------------------------------------------------------------- L1 working store
struct WSlot {
    bool used = false;
    char key[KEY_MAX + 1] = {0};
    char soul[SOUL_HEX + 1] = {0};
    uint32_t id = 0;
    Json value;
};

struct Working {
    WSlot s[WORKING_LIMIT];

    void set_soul(int i, const Json& v) {
        std::string d = sha256_hex(canon(v));
        std::strncpy(s[i].soul, d.c_str(), SOUL_HEX);
        s[i].soul[SOUL_HEX] = 0;
    }

    bool latch(const std::string& key, const Json& v) {
        if (key.empty() || (int)key.size() > KEY_MAX || !finite_num(v)) return false;
        Arena& a = g_arena;
        for (int i = 0; i < WORKING_LIMIT; i++) {                 // overwrite: priced erasure
            if (!s[i].used || key != s[i].key) continue;
            a.bits_erased += 8ull * (uint64_t)canon(s[i].value).size();
            a.record(OP_FREE, (uint32_t)i, s[i].id);
            s[i].value = v;
            set_soul(i, v);
            a.record(OP_ALLOC, (uint32_t)i, s[i].id);
            return true;
        }
        for (int i = 0; i < WORKING_LIMIT; i++) {                 // fresh slot
            if (s[i].used) continue;
            s[i].used = true;
            std::strncpy(s[i].key, key.c_str(), sizeof(s[i].key) - 1);
            s[i].key[KEY_MAX] = 0;
            s[i].value = v;
            s[i].id = ++a.next_id;
            set_soul(i, v);
            a.record(OP_ALLOC, (uint32_t)i, s[i].id);
            return true;
        }
        a.debt_refusals++;                                        // A8
        return false;
    }

    Json read(const std::string& key) const {
        for (int i = 0; i < WORKING_LIMIT; i++)
            if (s[i].used && key == s[i].key) return s[i].value;
        return Json();
    }
    bool has(const std::string& key) const {
        for (int i = 0; i < WORKING_LIMIT; i++)
            if (s[i].used && key == s[i].key) return true;
        return false;
    }
    void release(const std::string& key) {
        for (int i = 0; i < WORKING_LIMIT; i++) {
            if (!s[i].used || key != s[i].key) continue;
            g_arena.bits_erased += 8ull * (uint64_t)canon(s[i].value).size();
            g_arena.record(OP_FREE, (uint32_t)i, s[i].id);
            s[i].used = false; s[i].key[0] = 0; s[i].soul[0] = 0; s[i].value = Json();
            return;
        }
    }
    size_t size() const {
        size_t n = 0;
        for (int i = 0; i < WORKING_LIMIT; i++) n += s[i].used ? 1 : 0;
        return n;
    }
    // ORIGINAL byte shape: [{"key":..,"value":..}, ...] — do not add fields.
    Json snapshot() const {
        Json a = Json::array();
        for (int i = 0; i < WORKING_LIMIT; i++) {
            if (!s[i].used) continue;
            Json e = Json::object();
            e.set("key", Json(std::string(s[i].key)));
            e.set("value", s[i].value);
            a.push(e);
        }
        return a;
    }
    // ADDITIVE face for soul stamps (snapshot stays frozen).
    Json souls() const {
        Json a = Json::array();
        for (int i = 0; i < WORKING_LIMIT; i++) {
            if (!s[i].used) continue;
            Json e = Json::object();
            e.set("key", Json(std::string(s[i].key)));
            e.set("soul", Json(std::string(s[i].soul)));
            e.set("id", (int)s[i].id);
            a.push(e);
        }
        return a;
    }
    // Restore: wipe is erasure and is PRICED (A3); input shape validated fail-closed.
    bool restore(const Json& a) {
        if (!a.isArr()) return false;
        const auto& in = a.arr();
        for (size_t k = 0; k < in.size(); ++k) {
            const Json& e = in[k];
            if (!e.isObj() || !e.has("key") || !e["key"].isStr() || !e.has("value")) return false;
            const std::string key = e["key"].asStr();
            if (key.empty() || (int)key.size() > KEY_MAX) return false;
            if (!finite_num(e["value"])) return false;
        }
        for (int i = 0; i < WORKING_LIMIT; ++i) {                 // priced wipe
            if (!s[i].used) continue;
            g_arena.bits_erased += 8ull * (uint64_t)canon(s[i].value).size();
            g_arena.record(OP_FREE, (uint32_t)i, s[i].id);
            s[i].used = false; s[i].key[0] = 0; s[i].soul[0] = 0; s[i].value = Json();
        }
        for (size_t k = 0; k < in.size(); ++k) {
            int slot = -1;
            for (int i = 0; i < WORKING_LIMIT; ++i) if (!s[i].used) { slot = i; break; }
            if (slot < 0) { g_arena.debt_refusals++; return false; }
            const std::string key = in[k]["key"].asStr();
            s[slot].used = true;
            std::strncpy(s[slot].key, key.c_str(), KEY_MAX);
            s[slot].key[KEY_MAX] = 0;
            s[slot].value = in[k]["value"];
            s[slot].id = ++g_arena.next_id;
            set_soul(slot, s[slot].value);
            g_arena.record(OP_ALLOC, (uint32_t)slot, s[slot].id);
        }
        return true;
    }
};

// ---------------------------------------------------------------- L2 episodic ring
struct Episodic {
    Json r[EPISODIC_LIMIT];
    uint64_t head = 0, count = 0;
    void push(const Json& e) {
        uint32_t idx = (uint32_t)(head % EPISODIC_LIMIT);
        if (count >= EPISODIC_LIMIT) {                            // priced eviction
            g_arena.bits_erased += 8ull * (uint64_t)canon(r[idx]).size();
            g_arena.record(OP_EVICTION, idx, 0);
        }
        r[idx] = e;                                               // as-is, never rewrapped
        ++head; ++count;
        g_arena.record(OP_EPI_PUSH, idx, 0);
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

// ---------------------------------------------------------------- provenance chain (A9)
struct Provenance {
    uint32_t tick = 0;
    uint64_t dropped_frames = 0;
    std::string prev = std::string(64, '0');
    Json log = Json::array();

    void append(const std::string& op, const std::string& key, const std::string& method) {
        ++tick;
        Json f = Json::object();
        f.set("tick", (int)tick);
        f.set("op", op);
        f.set("key", key);
        f.set("method", method);
        f.set("prev", prev);
        if ((int)log.arr().size() >= PROV_LIMIT) {                // priced rotation (A5)
            g_arena.bits_erased += 8ull * (uint64_t)canon(log.arr()[0]).size();
            g_arena.record(OP_ROTATE, 0, tick);
            ++dropped_frames;
            Json nl = Json::array();
            for (size_t i = 1; i < log.arr().size(); ++i) nl.push(log.arr()[i]);
            log = nl;
        }
        log.push(f);
        prev = sha256_hex(canon(f));
    }
    std::string verify() const {
        std::string p = std::string(64, '0');
        const auto& a = log.arr();
        for (size_t i = 0; i < a.size(); ++i) {
            if (!a[i].has("prev") || a[i]["prev"].asStr() != p) return "CHAIN-BROKEN";
            p = sha256_hex(canon(a[i]));
        }
        return p == prev ? "OK" : "CHAIN-BROKEN";
    }
};

// process globals (defined in qcos_reg.cpp)
extern Working   g_working;
extern Provenance g_prov;
extern Episodic  g_episodic;

// ---------------------------------------------------------------- Zone 0 gate
inline constexpr const char* const kGateOps[] = {
    "boot","gate","latch","read","release","exec","restore",
    "snapshot","souls","episode","provenance","caps","lower","cost","shape","methods"};

inline Verdict gate(const std::string& op, const Json& args) {
    Verdict v;
    bool known = false;
    for (const char* k : kGateOps) if (op == k) { known = true; break; }
    if (!known) { v.ok = false; v.code = ZUNKNOWN; v.error = "gate: unknown op " + op; return v; }
    if (!finite_num(args)) { v.ok = false; v.code = ZBAD; v.error = "gate: non-finite number in args"; return v; }
    if (args.isObj() && args.has("key") && args["key"].isStr() &&
        (int)args["key"].asStr().size() > KEY_MAX) {
        v.ok = false; v.code = ZTOOLONG; v.error = "gate: key over bound"; return v;
    }
    return v;
}

// ---------------------------------------------------------------- CIR executor (bounded)
struct ExecResult { bool ok = true; Json trace = Json::array(); };

inline ExecResult exec_cir(Working& w, const Json& cir) {
    ExecResult er;
    if (!cir.isArr()) { er.ok = false; return er; }
    const auto& steps = cir.arr();
    if ((int)steps.size() > CIR_STEPS) { er.ok = false; g_arena.debt_refusals++; return er; }
    for (size_t i = 0; i < steps.size(); ++i) {
        const Json& st = steps[i];
        Json t = Json::object();
        t.set("i", (int)i);
        if (!st.isObj() || !st.has("op") || !st["op"].isStr()) {
            t.set("ok", false); er.trace.push(t); er.ok = false; break;
        }
        std::string op = st["op"].asStr();
        t.set("op", op);
        bool good = false;
        if (op == "set" && st.has("key") && st["key"].isStr() && st.has("value"))
            good = w.latch(st["key"].asStr(), st["value"]);
        else if (op == "get" && st.has("key") && st["key"].isStr()) {
            good = w.has(st["key"].asStr());
            if (good) t.set("value", w.read(st["key"].asStr()));
        } else if (op == "release" && st.has("key") && st["key"].isStr()) {
            good = w.has(st["key"].asStr());
            w.release(st["key"].asStr());
        } else if (op == "add" && st.has("key") && st["key"].isStr() &&
                   st.has("delta") && st["delta"].isNum() &&
                   w.has(st["key"].asStr()) && w.read(st["key"].asStr()).isNum()) {
            double nv = w.read(st["key"].asStr()).asNum() + st["delta"].asNum();
            good = finite_num(Json(nv)) && w.latch(st["key"].asStr(), Json(nv));
        }
        t.set("ok", good);
        er.trace.push(t);
        if (!good) { er.ok = false; break; }
    }
    return er;
}

// ---------------------------------------------------------------- constitution & caps
inline Json constitution_json() {
    Json arts = Json::object();
    arts.set("A0", "computed, never guessed");
    arts.set("A3", "measurement and overwrite are the only irreversible acts; they are priced");
    arts.set("A5", "the ledger is append-only; unwitnessed rules are hypotheses");
    arts.set("A7", "no execution without constitutional admission");
    arts.set("A8", "memory is static and bounded; exhaustion is refusal, never growth");
    arts.set("A9", "every transition records provenance; the ledger is the core's conscience");
    Json o = Json::object();
    o.set("articles", arts);
    o.set("hash", sha256_hex(canon(arts)));
    return o;
}

inline Json caps_report() {
    Json o = Json::object();
    o.set("working_limit", WORKING_LIMIT);
    o.set("episodic_limit", EPISODIC_LIMIT);
    o.set("bits_erased", (double)g_arena.bits_erased);
    o.set("refusals", (double)g_arena.debt_refusals);
    return o;
}

// ---------------------------------------------------------------- frozen witness suite
// ORIGINAL names first; additions append-only (never reorder, never delete).
inline int selftest() {
    int fails = 0, total = 0;
    auto want = [&](const char* n, bool ok) {
        ++total; if (!ok) ++fails;
        std::printf("[qcos-selftest] %-30s %s\n", n, ok ? "ok" : "DRIFT");
    };
    g_arena.init();
    Working w; Episodic ep;

    want("jsnum_half", jsnum(0.1 + 0.2) == "0.30000000000000004");
    want("l1_latch", w.latch("k", Json(1)) && w.read("k").asNum() == 1);
    want("l1_key_bound", !w.latch(std::string(30, 'x'), Json(1)));
    want("gate_allow", gate("latch", Json::object()).ok);
    Verdict vu = gate("nope", Json::object());
    want("gate_msg_unknown", !vu.ok && vu.error == "gate: unknown op nope");
    Json bad = Json::object(); bad.set("x", Json(1e999));
    Verdict vf = gate("latch", bad);
    want("gate_msg_nonfinite", !vf.ok && vf.error.rfind("gate: non-finite", 0) == 0);

    // ---- appended witnesses (step 11b) ----
    uint64_t before = g_arena.bits_erased;
    want("overwrite_priced", w.latch("k", Json(2)) && g_arena.bits_erased > before);
    uint32_t id1 = g_arena.next_id;
    want("id_monotonic", w.latch("k2", Json(5)) && g_arena.next_id == id1 + 1);
    Provenance pv;
    pv.append("a", "k", "m"); pv.append("b", "k", "m");
    want("prov_chain", pv.verify() == "OK");
    Json snap = w.snapshot();
    bool shape_ok = snap.isArr();
    for (size_t i = 0; shape_ok && i < snap.arr().size(); ++i)
        shape_ok = snap.arr()[i].isObj() && snap.arr()[i].obj().size() == 2 &&
                   snap.arr()[i].has("key") && snap.arr()[i].has("value");
    want("snapshot_shape_frozen", shape_ok);
    uint64_t rb = g_arena.bits_erased;
    want("restore_priced", w.restore(snap) && g_arena.bits_erased >= rb);
    for (int i = 0; i < EPISODIC_LIMIT + 8; ++i) ep.push(Json(i));
    want("episodic_bound", ep.count == (uint64_t)EPISODIC_LIMIT);
    want("episodic_eviction_priced", g_arena.bits_erased > rb);
    Json cir = Json::array();
    Json s1 = Json::object(); s1.set("op", "set"); s1.set("key", "z"); s1.set("value", Json(3));
    cir.push(s1);
    Json s2 = Json::object(); s2.set("op", "bogus"); cir.push(s2);
    ExecResult er = exec_cir(w, cir);
    want("exec_fail_closed", !er.ok);
    want("canon_determinism", canon(snap) == canon(w.snapshot()));
    (void)total;
    return fails;
}

inline Json self_test() {
    int fails = selftest();
    Json o = Json::object();
    o.set("ok", fails == 0);
    o.set("fails", fails);
    return o;
}

} // namespace qcos
