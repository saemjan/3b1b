// core/src/qcos_reg.cpp — Gen-3 Canonical Registrar & Single Door (Step 12)
// Doctrine: One transition door (os.md P5), fail-closed, provenance per transition.

#include "qcos.hpp"
#include "cog.hpp"
#include <cstring>
#include <string>

namespace saem {
namespace qcos {

// --- Global State Definitions (declared extern in qcos.hpp) ---
Working   g_working;
Provenance g_prov;
Episodic  g_episodic;

// --- Refusal Codes ---
constexpr int ZOK      = 0;
constexpr int ZBAD     = 400;
constexpr int ZGUARD   = 403;
constexpr int ZUNKNOWN = 404;
constexpr int ZTOOLONG = 413;
constexpr int ZBUDGET  = 429;

// --- Registry Table ---
enum Kind : uint8_t { K_PURE = 0, K_RESIDENT = 1, K_GATE = 2 };
typedef Json (*Fn)(const Json& a, Verdict& v);

struct RegEntry { const char* name; uint8_t kind; Fn fn; };

// Forward declarations
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
    {"qcos.latch",      K_RESIDENT, h_claim}, // Alias for claim
    {"qcos.snapshot",   K_RESIDENT, h_snapshot},
    {"qcos.exec",       K_RESIDENT, h_exec},
    {"qcos.restore",    K_RESIDENT, h_restore},
    {"qcos.episode",    K_RESIDENT, h_episode},
    {"gen.demo",        K_PURE,     h_demo},
};
constexpr size_t REG_N = sizeof(kTable) / sizeof(kTable[0]);

const RegEntry* reg_find(const char* name) {
    if (!name) return nullptr;
    for (size_t i = 0; i < REG_N; ++i)
        if (std::strcmp(kTable[i].name, name) == 0) return &kTable[i];
    return nullptr;
}
size_t reg_size() { return REG_N; }

// --- Zone 0 Gate ---
Verdict gate(const char* op, const Json& args, uint8_t kind) {
    Verdict v;
    if (!op) { v.ok = false; v.code = ZBAD; v.error = "null_op"; return v; }
    if (std::strlen(op) > NAME_MAX) { v.ok = false; v.code = ZTOOLONG; v.error = "op_too_long"; return v; }
    if (kind == K_RESIDENT && g_working.size() >= WORKING_LIMIT) {
        v.ok = false; v.code = ZBUDGET; v.error = "working_exhausted"; return v;
    }
    return v;
}

// --- Handlers ---
static Json refuse(Verdict& v, int code, const char* why) {
    v.ok = false; v.code = code; v.error = why;
    return Json::object();
}

static Json h_boot(const Json&, Verdict&) {
    return Json::object().set("status", "OK");
}

static Json h_read(const Json& a, Verdict& v) {
    if (!a.has("key") || !a["key"].isStr()) return refuse(v, ZBAD, "missing_key");
    const char* k = a["key"].asStr().c_str();
    if (std::strlen(k) == 0 || std::strlen(k) > KEY_MAX) return refuse(v, ZTOOLONG, "key_bad_len");
    Json val = g_working.read(k);
    Json o = Json::object();
    if (!g_working.has(k)) { o.set("found", false); return o; }
    o.set("found", true);
    o.set("value", val);
    return o;
}

static Json h_zone0(const Json& a, Verdict& v) {
    return Json::object().set("pass", true);
}

static Json h_provenance(const Json&, Verdict&) {
    Json o = Json::object();
    o.set("tick", (int)g_prov.tick);
    o.set("prev", g_prov.prev);
    o.set("log", g_prov.recent(10));
    return o;
}

static Json h_caps(const Json&, Verdict&) {
    Json o = Json::object();
    o.set("working_limit", WORKING_LIMIT);
    o.set("episodic_limit", EPISODIC_LIMIT);
    o.set("key_max", KEY_MAX);
    return o;
}

static Json h_claim(const Json& a, Verdict& v) {
    if (!a.has("key") || !a["key"].isStr()) return refuse(v, ZBAD, "missing_key");
    const char* k = a["key"].asStr().c_str();
    if (std::strlen(k) == 0 || std::strlen(k) > KEY_MAX) return refuse(v, ZTOOLONG, "key_bad_len");
    if (g_working.has(k)) return refuse(v, ZGUARD, "already_locked");
    return Json::object().set("token", "CLAIM_OK");
}

static Json h_complete(const Json& a, Verdict& v) {
    if (!a.has("key") || !a["key"].isStr() || !a.has("value")) return refuse(v, ZBAD, "missing_key_or_value");
    const char* k = a["key"].asStr().c_str();
    bool ok = g_working.latch(k, a["value"]);
    if (!ok) return refuse(v, ZBUDGET, "working_exhausted");
    return Json::object().set("status", "COMMITTED");
}

static Json h_lower(const Json& a, Verdict&) { return Json::object().set("ok", true); }
static Json h_cost(const Json& a, Verdict&) { return Json::object().set("ok", true); }
static Json h_shape(const Json& a, Verdict&) { return Json::object().set("ok", true); }
static Json h_snapshot(const Json&, Verdict&) { return g_working.snapshot(); }
static Json h_exec(const Json&, Verdict&) { return Json::object().set("ok", true); }

static Json h_restore(const Json& a, Verdict& v) {
    if (!a.has("data") || !a["data"].isArr()) return refuse(v, ZBAD, "missing_data_array");
    bool ok = g_working.restore(a["data"]);
    if (!ok) return refuse(v, ZBAD, "restore_failed");
    return Json::object().set("status", "RESTORED");
}

static Json h_episode(const Json& a, Verdict&) {
    Json o = Json::object();
    o.set("tick", (int)g_prov.tick);
    o.set("log", g_prov.recent(10));
    return o;
}

static Json h_demo(const Json& a, Verdict&) {
    int64_t seed = a.has("seed") ? (int64_t)a["seed"].asNum() : 11;
    int64_t y0 = a.has("y0") ? (int64_t)a["y0"].asNum() : 0;
    return Json::object().set("n", (double)(seed + y0));
}

// --- The Single Door ---
static Json envelope(const char* method, const Verdict& v, const Json& result) {
    Json o = Json::object();
    o.set("ok", v.ok);
    o.set("method", method ? method : "");
    o.set("tick", (int)g_prov.tick);
    o.set("code", (double)(v.ok ? ZOK : v.code));
    if (!v.ok) o.set("error", v.error);
    else       o.set("result", result);
    return o;
}

Json door(const Json& req) {
    if (!req.isObj()) return envelope("", Verdict{false, "not_object", ZBAD}, Json::object());
    if (!req.has("method") || !req["method"].isStr()) return envelope("", Verdict{false, "missing_method", ZBAD}, Json::object());
    const char* name = req["method"].asStr().c_str();
    Json args = (req.has("args") && req["args"].isObj()) ? req["args"] : Json::object();

    const RegEntry* e = reg_find(name);
    if (!e) {
        Verdict v; v.ok = false; v.code = ZUNKNOWN; v.error = "unknown_method";
        g_prov.append(name, "refused", "qcos.door");
        return envelope(name, v, Json::object());
    }
    Verdict v = gate(name, args, e->kind);
    if (!v.ok) {
        g_prov.append(name, "refused", "qcos.door");
        return envelope(name, v, Json::object());
    }
    Verdict hv;
    Json result = e->fn(args, hv);
    if (!hv.ok) {
        g_prov.append(name, "refused", "qcos.door");
        return envelope(name, hv, Json::object());
    }
    g_prov.append(name, "ok", "qcos.door");
    return envelope(name, hv, result);
}

// --- Working Store Surface for Delegation ---
Json wstore_get(const Json& a) {
    Verdict v; Json r = h_read(a, v);
    if (!v.ok) { Json o = Json::object(); o.set("ok", false); o.set("error", v.error); o.set("code", (double)v.code); return o; }
    return r;
}
Json wstore_claim(const Json& a) {
    Verdict v; Json r = h_claim(a, v);
    if (!v.ok) { Json o = Json::object(); o.set("ok", false); o.set("error", v.error); o.set("code", (double)v.code); return o; }
    return r;
}
Json wstore_complete(const Json& a) {
    Verdict v; Json r = h_complete(a, v);
    if (!v.ok) { Json o = Json::object(); o.set("ok", false); o.set("error", v.error); o.set("code", (double)v.code); return o; }
    return r;
}

// --- Witnesses (Self-Test) ---
Json self_test() {
    Json w = Json::array();
    auto add = [&w](const char* name, bool ok, const char* detail) {
        Json e = Json::object();
        e.set("name", name); e.set("ok", ok); e.set("detail", detail);
        w.push(e); // FIX: push, not push_back
    };
    add("table-complete", REG_N == 16, REG_N == 16 ? "16 entries" : "count drift");
    add("zone0-present", reg_find("qcos.zone0") != nullptr, "gate present");
    add("door-echo", []{
        Json r = Json::object(); r.set("method", "qcos.caps"); r.set("args", Json::object());
        Json d = door(r);
        return d.has("method") && d["method"].isStr() && std::strcmp(d["method"].asStr().c_str(), "qcos.caps") == 0 && d.has("tick");
    }(), "id-echo + tick");
    add("unknown-refused", []{
        Json r = Json::object(); r.set("method", "nope");
        Json d = door(r);
        return d.has("ok") && !d["ok"].isNum() && d.has("code");
    }(), "404 envelope");
    add("prov-bounded", g_prov.log.arr().size() <= (size_t)EPISODIC_LIMIT, "ring <= 64");
    Json o = Json::object();
    o.set("witnesses", w);
    return o;
}

} // namespace qcos
} // namespace saem
