// core/src/qcos_reg.cpp — Gen-3 canonical registrar & the single door (2026-10-30)
// Layer: core (execution edge). Stance: C++17, zero-heap, fail-closed,
//        provenance per transition, ONE door (os.md P5).
// Doctrine: xv6 syscall.c single dispatch table + log.c two-phase commit;
//           A2 door holds no hidden state; A8 exhaustion is refusal;
//           A3/A5 erasure is priced; A9 every transition testifies.
//
// API CONTRACT (frozen):
//   saem::qcos::g_prov              — L2 episodic ring (definition)
//   saem::qcos::gate(op,args,kind)  — Zone 0 admission
//   saem::qcos::door(req)           — the single transition door
//   saem::qcos::reg_find / reg_size — table probes (witnesses, tests)
//   saem::qcos::self_test()         — frozen witness set
//   saem::qcos::wstore_get/claim/complete — working-store surface (32 slots)

#include "qcos.hpp"
#include "kernel.hpp"
#include "cog.hpp"
#include <cstring>

namespace saem {
namespace qcos {

// --- refusal codes: one ruler across the core (§14) ---
constexpr int ZOK      = 0;
constexpr int ZBAD     = 400;
constexpr int ZGUARD   = 403;
constexpr int ZUNKNOWN = 404;
constexpr int ZTOOLONG = 413;
constexpr int ZBUDGET  = 429;

// --- Landauer rulers: canonical bytes per erased frame / value (§14).
//     Changing either requires a §24 amendment; they price every erasure.
constexpr uint32_t FRAME_CANON_BYTES = 128;
constexpr uint32_t VALUE_CANON_BYTES = 64;

// --- L2 episodic ring definition (extern in qcos.hpp) ---
Provenance g_prov;

// --- kernel instance: static, zero-heap, deterministic init ---
static Kernel g_kernel;

// ---------------------------------------------------------------- working store
// 32 static slots, four-axis anatomy (identity / lifetime / validity / lock),
// monotonic ids, junk-fill on release (step 11 discipline).
struct WSlot {
    uint32_t id;
    uint8_t  used;
    uint8_t  valid;
    uint8_t  lock;
    char     key[KEY_MAX + 1];
    Json     val;
};
static WSlot   g_work[WORKING_LIMIT];
static uint32_t g_next_id = 1;

static void w_junk(WSlot& s) {           // junk-fill: no stale truth survives
    s.used = 0; s.valid = 0; s.lock = 0;
    std::memset(s.key, 0, sizeof(s.key));
    s.val = Json();
}
static WSlot* w_find(const char* k) {
    for (uint32_t i = 0; i < WORKING_LIMIT; ++i)
        if (g_work[i].used && std::strcmp(g_work[i].key, k) == 0) return &g_work[i];
    return nullptr;
}
static WSlot* w_byid(uint32_t id) {
    for (uint32_t i = 0; i < WORKING_LIMIT; ++i)
        if (g_work[i].used && g_work[i].id == id) return &g_work[i];
    return nullptr;
}
static WSlot* w_alloc() {
    for (uint32_t i = 0; i < WORKING_LIMIT; ++i)
        if (!g_work[i].used) { w_junk(g_work[i]); g_work[i].used = 1;
                               g_work[i].id = g_next_id++; return &g_work[i]; }
    return nullptr;                        // A8: exhaustion is refusal
}
static uint32_t w_locks() {
    uint32_t n = 0;
    for (uint32_t i = 0; i < WORKING_LIMIT; ++i)
        if (g_work[i].used && g_work[i].lock) ++n;
    return n;
}

// ---------------------------------------------------------------- registry
enum Kind : uint8_t { K_PURE = 0, K_RESIDENT = 1, K_GATE = 2 };
typedef Json (*Fn)(const Json& a, Verdict& v);

struct RegEntry { const char* name; uint8_t kind; Fn fn; };

// forward handlers
static Json h_boot(const Json&, Verdict&);
static Json h_read(const Json&, Verdict&);
static Json h_zone0(const Json&, Verdict&);
static Json h_provenance(const Json&, Verdict&);
static Json h_caps(const Json&, Verdict&);
static Json h_claim(const Json&, Verdict&);
static Json h_complete(const Json&, Verdict&);
static Json h_lower(const Json&, Verdict&);
static Json h_cost(const Json&, Verdict&);
static Json h_shape(const Json&, Verdict&);
static Json h_snapshot(const Json&, Verdict&);
static Json h_exec(const Json&, Verdict&);
static Json h_restore(const Json&, Verdict&);
static Json h_episode(const Json&, Verdict&);
static Json h_demo(const Json&, Verdict&);

static const RegEntry kTable[] = {
    {"qcos.boot",       K_PURE,     h_boot},
    {"qcos.read",       K_RESIDENT, h_read},
    {"qcos.zone0",      K_GATE,     h_zone0},
    {"qcos.provenance", K_RESIDENT, h_provenance},
    {"qcos.caps",       K_PURE,     h_caps},
    {"qcos.claim",      K_RESIDENT, h_claim},
    {"qcos.complete",   K_RESIDENT, h_complete},
    {"qcos.lower",      K_PURE,     h_lower},
    {"qcos.cost",       K_PURE,     h_cost},
    {"qcos.shape",      K_RESIDENT, h_shape},
    {"qcos.latch",      K_RESIDENT, h_claim},   // latch == claim (one ruler)
    {"qcos.snapshot",   K_RESIDENT, h_snapshot},
    {"qcos.exec",       K_RESIDENT, h_exec},
    {"qcos.restore",    K_RESIDENT, h_restore},
    {"qcos.episode",    K_RESIDENT, h_episode},
    {"gen.demo",        K_PURE,     h_demo},
};
constexpr size_t REG_N = sizeof(kTable) / sizeof(kTable[0]);

const RegEntry* reg_find(const char* name) {
    if (!name) return nullptr;
    for (size_t i = 0; i < REG_N; ++i)                 // O(N) scan: §6-legal
        if (std::strcmp(kTable[i].name, name) == 0) return &kTable[i];
    return nullptr;
}
size_t reg_size() { return REG_N; }

// ---------------------------------------------------------------- Zone 0 gate
Verdict gate(const char* op, const Json& args, uint8_t kind) {
    Verdict v;
    (void)args;
    if (!op) { v.ok = false; v.code = ZBAD; v.error = "null_op"; return v; }
    if (std::strlen(op) > NAME_MAX) { v.ok = false; v.code = ZTOOLONG;
                                      v.error = "op_too_long"; return v; }
    if (kind == K_RESIDENT && w_locks() >= WORKING_LIMIT) {
        v.ok = false; v.code = ZBUDGET; v.error = "working_exhausted"; return v;
    }
    return v;
}

// ---------------------------------------------------------------- handlers
static Json refuse(Verdict& v, int code, const char* why) {
    v.ok = false; v.code = code; v.error = why;
    return Json::object();
}

// qcos_api bridges (step 12 file); header extraction deferred to step 23 (D-9)
namespace qcos_api_bridge {
Json lower(const Json&); Json cost(const Json&); Json shape(const Json&);
Json snapshot(const Json&); Json caps(const Json&); Json provenance(const Json&);
Json zone0(const Json&); Json demo(const Json&);
}

static Json h_boot(const Json&, Verdict&) {
    Json o = Json::object();
    o.set("status", "OK");
    o.set("board", static_cast<double>(g_kernel.board()));
    o.set("entropy_kTln2", static_cast<double>(g_kernel.entropy_debt_kTln2()));
    o.set("reg_n", static_cast<double>(REG_N));
    return o;
}
static Json h_read(const Json& a, Verdict& v) {
    if (!a.has("key") || !a["key"].isStr()) return refuse(v, ZBAD, "missing_key");
    const char* k = a["key"].asStr();
    if (std::strlen(k) == 0 || std::strlen(k) > KEY_MAX)
        return refuse(v, ZTOOLONG, "key_bad_len");
    const WSlot* s = w_find(k);
    Json o = Json::object();
    if (!s || !s->valid) { o.set("found", false); return o; }
    o.set("found", true);
    o.set("value", s->val);
    o.set("id", static_cast<double>(s->id));
    return o;
}
static Json h_zone0(const Json& a, Verdict& v) {
    return qcos_api_bridge::zone0(a), (void)v, Json::object();
}
static Json h_provenance(const Json& a, Verdict&) { return qcos_api_bridge::provenance(a); }
static Json h_caps(const Json& a, Verdict&)       { return qcos_api_bridge::caps(a); }
static Json h_lower(const Json& a, Verdict&)      { return qcos_api_bridge::lower(a); }
static Json h_cost(const Json& a, Verdict&)       { return qcos_api_bridge::cost(a); }
static Json h_shape(const Json& a, Verdict&)      { return qcos_api_bridge::shape(a); }
static Json h_demo(const Json& a, Verdict&)       { return qcos_api_bridge::demo(a); }

static Json h_claim(const Json& a, Verdict& v) {
    if (!a.has("key") || !a["key"].isStr()) return refuse(v, ZBAD, "missing_key");
    const char* k = a["key"].asStr();
    if (std::strlen(k) == 0 || std::strlen(k) > KEY_MAX)
        return refuse(v, ZTOOLONG, "key_bad_len");
    WSlot* s = w_find(k);
    if (s && s->lock) return refuse(v, ZGUARD, "already_locked");
    if (!s) { s = w_alloc(); if (!s) return refuse(v, ZBUDGET, "working_exhausted");
              std::strncpy(s->key, k, KEY_MAX); s->key[KEY_MAX] = '\0'; }
    s->lock = 1;                                       // phase 1: claim
    Json o = Json::object();
    o.set("token", static_cast<double>(s->id));
    return o;
}
static Json h_complete(const Json& a, Verdict& v) {
    if (!a.has("token") || !a["token"].isNum()) return refuse(v, ZBAD, "missing_token");
    uint32_t id = static_cast<uint32_t>(a["token"].asNum());
    WSlot* s = w_byid(id);
    if (!s || !s->lock) return refuse(v, ZGUARD, "not_locked");
    if (!a.has("value")) return refuse(v, ZBAD, "missing_value");
    const uint32_t erased = s->valid ? 1u : 0u;        // A3: overwrite is erasure
    s->val = a["value"];
    s->valid = 1; s->lock = 0;                         // phase 2: commit
    Json o = Json::object();
    o.set("status", "COMMITTED");
    o.set("erased", static_cast<double>(erased));
    o.set("erased_bits", static_cast<double>(erased * VALUE_CANON_BYTES * 8u));
    return o;
}
static Json h_snapshot(const Json&, Verdict&) {
    Json slots = Json::array();
    for (uint32_t i = 0; i < WORKING_LIMIT; ++i) {
        const WSlot& s = g_work[i];
        if (!s.used) continue;
        Json e = Json::object();
        e.set("id", static_cast<double>(s.id));
        e.set("key", s.key);
        e.set("valid", s.valid != 0);
        e.set("lock", s.lock != 0);
        slots.push_back(e);
    }
    Json o = Json::object();
    o.set("slots", slots);
    o.set("board", static_cast<double>(g_kernel.board()));
    o.set("entropy_kTln2", static_cast<double>(g_kernel.entropy_debt_kTln2()));
    return o;
}
static Json h_exec(const Json&, Verdict& v) {
    uint32_t steps = 0;
    while (steps < CIR_STEPS && g_kernel.board() > 0) { g_kernel.tick(); ++steps; }
    Json o = Json::object();
    o.set("steps", static_cast<double>(steps));
    o.set("board", static_cast<double>(g_kernel.board()));
    o.set("entropy_kTln2", static_cast<double>(g_kernel.entropy_debt_kTln2()));
    if (steps == CIR_STEPS && g_kernel.board() > 0)
        o.set("horizon", true);                        // degradation recorded, not hidden
    else
        o.set("horizon", false);
    (void)v;
    return o;
}
static Json h_restore(const Json& a, Verdict& v) {
    if (!a.has("name") || !a["name"].isStr()) return refuse(v, ZBAD, "missing_name");
    const char* nm = a["name"].asStr();
    if (std::strlen(nm) == 0 || std::strlen(nm) > NAME_MAX)
        return refuse(v, ZTOOLONG, "name_bad_len");
    Proc* p = g_kernel.find(std::string(nm));
    if (!p) return refuse(v, ZUNKNOWN, "no_such_proc");
    g_kernel.reap(*p);                                 // two-phase completion (ZOMBIE)
    Json o = Json::object();
    o.set("reaped", nm);
    return o;
}
static Json h_episode(const Json& a, Verdict&) {
    Json o = Json::object();
    const bool rot = a.has("rotate") && a["rotate"].isNum() && a["rotate"].asNum() != 0.0;
    if (rot) {                                         // priced rotation (A5)
        size_t n = g_prov.log.size() > EPISODIC_LIMIT
                 ? g_prov.log.size() - EPISODIC_LIMIT : 0;
        for (size_t i = 0; i < n; ++i) g_prov.log.erase(0, 1);
        g_prov.append("episode.rotate", "l2", ZOK);
        o.set("debt_frames", static_cast<double>(n));
        o.set("debt_bits", static_cast<double>(n * FRAME_CANON_BYTES * 8u));
    }
    o.set("tick", static_cast<double>(g_prov.tick));
    o.set("prev", g_prov.prev);
    o.set("log", g_prov.log);
    o.set("dropped_frames", static_cast<double>(g_prov.dropped_frames));
    return o;
}

// ---------------------------------------------------------------- the door
static Json envelope(const char* method, const Verdict& v, const Json& result) {
    Json o = Json::object();
    o.set("ok", v.ok);
    o.set("method", method);                           // id-echo (§6)
    o.set("tick", static_cast<double>(g_prov.tick));
    o.set("code", static_cast<double>(v.ok ? ZOK : v.code));
    if (!v.ok) o.set("error", v.error.c_str());
    else       o.set("result", result);
    o.set("dropped_frames", static_cast<double>(g_prov.dropped_frames));
    return o;
}

Json door(const Json& req) {
    if (!req.isObj())
        return envelope("", Verdict{false, "not_object", ZBAD}, Json::object());
    if (!req.has("method") || !req["method"].isStr())
        return envelope("", Verdict{false, "missing_method", ZBAD}, Json::object());
    const char* name = req["method"].asStr();
    Json args = (req.has("args") && req["args"].isObj()) ? req["args"] : Json::object();

    const RegEntry* e = reg_find(name);
    if (!e) {
        Verdict v; v.ok = false; v.code = ZUNKNOWN; v.error = "unknown_method";
        g_prov.append(name, "refused", ZUNKNOWN);      // A9: refusals testify
        return envelope(name, v, Json::object());
    }
    Verdict v = gate(name, args, e->kind);
    if (!v.ok) {
        g_prov.append(name, "refused", v.code);
        return envelope(name, v, Json::object());
    }
    Verdict hv;
    Json result = e->fn(args, hv);
    if (!hv.ok) {
        g_prov.append(name, "refused", hv.code);
        return envelope(name, hv, Json::object());
    }
    g_prov.append(name, "ok", ZOK);
    return envelope(name, hv, result);
}

// working-store surface for qcos_api delegation (integration patch below)
Json wstore_get(const Json& a)      { Verdict v; Json r = h_read(a, v);
                                      if (!v.ok) { Json o = Json::object();
                                        o.set("ok", false); o.set("error", v.error.c_str());
                                        o.set("code", static_cast<double>(v.code)); return o; }
                                      return r; }
Json wstore_claim(const Json& a)    { Verdict v; Json r = h_claim(a, v);
                                      if (!v.ok) { Json o = Json::object();
                                        o.set("ok", false); o.set("error", v.error.c_str());
                                        o.set("code", static_cast<double>(v.code)); return o; }
                                      return r; }
Json wstore_complete(const Json& a) { Verdict v; Json r = h_complete(a, v);
                                      if (!v.ok) { Json o = Json::object();
                                        o.set("ok", false); o.set("error", v.error.c_str());
                                        o.set("code", static_cast<double>(v.code)); return o; }
                                      return r; }

// ---------------------------------------------------------------- witnesses
Json self_test() {
    Json w = Json::array();
    auto add = [&w](const char* name, bool ok, const char* detail) {
        Json e = Json::object();
        e.set("name", name); e.set("ok", ok); e.set("detail", detail);
        w.push_back(e);
    };
    add("table-complete", REG_N == 16, REG_N == 16 ? "16 entries" : "count drift");
    add("zone0-present", reg_find("qcos.zone0") != nullptr &&
        reg_find("qcos.zone0")->kind == K_GATE, "gate kind");
    add("door-echo", []{ Json r = Json::object(); r.set("method", "qcos.caps");
                        Json o = Json::object(); o.set("args", Json::object());
                        r.set("args", Json::object());
                        Json d = door(r);
                        return d.has("method") && d["method"].isStr() &&
                               std::strcmp(d["method"].asStr(), "qcos.caps") == 0 &&
                               d.has("tick"); }(), "id-echo + tick");
    add("unknown-refused", []{ Json r = Json::object(); r.set("method", "nope");
                               Json d = door(r);
                               return d.has("ok") && !d["ok"].isNum() &&
                                      d.has("code"); }(), "404 envelope");
    add("two-phase", []{ Json c = Json::object(); c.set("key", "w1");
                         Json t = door([&]{ Json r = Json::object();
                                            r.set("method", "qcos.claim");
                                            r.set("args", c); return r; }());
                         if (!t.has("result")) return false;
                         Json cc = Json::object();
                         cc.set("token", t["result"].has("token") ? t["result"]["token"] : Json(0.0));
                         cc.set("value", Json(7.0));
                         Json r2 = Json::object(); r2.set("method", "qcos.complete");
                         r2.set("args", cc);
                         Json d2 = door(r2);
                         Json r3 = Json::object(); r3.set("method", "qcos.read");
                         Json a3 = Json::object(); a3.set("key", "w1"); r3.set("args", a3);
                         Json d3 = door(r3);
                         return d3.has("result") && d3["result"].has("found") &&
                                d3["result"]["found"].isNum() && d3["result"]["found"].asNum() != 0.0;
                       }(), "claim->complete->read");
    add("prov-bounded", g_prov.log.size() <= EPISODIC_LIMIT, "ring <= 64");
    Json o = Json::object();
    o.set("witnesses", w);
    return o;
}

} // namespace qcos
} // namespace saem
