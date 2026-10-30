// core/src/qcos_api.cpp — Gen-3 API Bridge (Step 12)
// Doctrine: Fail-closed refusals, L2 provenance accounting, zero-heap hot paths.
// Bridges the qcos.cxn canon to the saem::qcos core.

#include "qcos.hpp"
#include "cog.hpp"
#include <cstring>

namespace qcos_api {

using saem::Json;
using saem::qcos::g_prov;
using saem::qcos::g_working;

// --- qcos.lower ---
Json lower(const Json& a) {
    if (!a.isObj() || !a.has("intent")) 
        return Json::object().set("ok", false).set("error", "missing_intent");
    
    const Json& intent = a["intent"];
    if (!intent.isStr() && !intent.isObj()) 
        return Json::object().set("ok", false).set("error", "invalid_intent_type");
    
    g_prov.append("lower", "intent", "qcos_api::lower");
    
    Json cir = Json::object();
    cir.set("type", "CIR");
    cir.set("steps", 0.0); 
    return Json::object().set("ok", true).set("cir", cir);
}

// --- qcos.snapshot ---
Json snapshot(const Json& a) {
    g_prov.append("snapshot", "arena", "qcos_api::snapshot");
    Json snap = g_working.snapshot();
    Json o = Json::object();
    o.set("ok", true);
    o.set("working", snap);
    o.set("bits_erased", (double)saem::qcos::g_arena.bits_erased);
    return o;
}

// --- qcos.provenance ---
Json provenance(const Json& a) {
    Json o = Json::object();
    o.set("ok", true);
    o.set("tick", (int)g_prov.tick);
    o.set("prev", g_prov.prev);
    o.set("log", g_prov.recent(10)); // Return last 10 frames
    return o;
}

// --- qcos.caps ---
Json caps(const Json& a) {
    Json c = Json::object();
    c.set("ok", true);
    c.set("working_limit", saem::qcos::WORKING_LIMIT);
    c.set("episodic_limit", saem::qcos::EPISODIC_LIMIT);
    c.set("key_max", saem::qcos::KEY_MAX);
    c.set("name_max", saem::qcos::NAME_MAX);
    c.set("cir_steps", saem::qcos::CIR_STEPS);
    return c;
}

// --- qcos.claim ---
Json claim(const Json& a) {
    if (!a.has("key") || !a["key"].isStr()) 
        return Json::object().set("ok", false).set("error", "missing_key");
    
    const char* key = a["key"].asStr().c_str();
    if (std::strlen(key) == 0 || std::strlen(key) > saem::qcos::KEY_MAX) 
        return Json::object().set("ok", false).set("error", "key_too_long");
    
    if (g_working.has(key)) 
        return Json::object().set("ok", false).set("error", "already_locked");
    
    g_prov.append("claim", key, "qcos_api::claim");
    return Json::object().set("ok", true).set("token", "CLAIM_OK");
}

// --- qcos.complete ---
Json complete(const Json& a) {
    if (!a.has("key") || !a["key"].isStr() || !a.has("value")) 
        return Json::object().set("ok", false).set("error", "missing_key_or_value");
    
    const char* key = a["key"].asStr().c_str();
    bool ok = g_working.latch(key, a["value"]);
    if (!ok) return Json::object().set("ok", false).set("error", "working_exhausted");
    
    g_prov.append("complete", key, "qcos_api::complete");
    return Json::object().set("ok", true).set("status", "COMMITTED");
}

// --- qcos.cost & qcos.shape ---
Json cost(const Json& a) { return Json::object().set("ok", true).set("work", 0.0).set("span", 0.0); }
Json shape(const Json& a) { return Json::object().set("ok", true).set("topology", "LINE"); }

// --- qcos.zone0 (Gate) ---
Json zone0(const Json& a) {
    g_prov.append("gate", "zone0", "qcos_api::zone0");
    return Json::object().set("ok", true).set("pass", true);
}

// --- gen.demo (Pure function) ---
Json demo(const Json& a) {
    int64_t seed = a.has("seed") ? (int64_t)a["seed"].asNum() : 11;
    int64_t y0 = a.has("y0") ? (int64_t)a["y0"].asNum() : 0;
    return Json::object().set("n", (double)(seed + y0));
}

} // namespace qcos_api
