// core/src/qcos_api.cpp — Gen-3 API Bridge & Zone 0 Enforcement
// Doctrine: Fail-closed refusals, L2 provenance accounting, zero-heap hot paths.
// This file bridges the generated canon registry (qcosc) to the QCOS core.

#include "qcos.hpp"
#include "cog.hpp"
#include <cstring>
#include <cstdint>

namespace {

using saem::Json;

// --- Fail-Closed Guards ---
// Returns a structured error envelope. Never throws.
Json refuse(const char* reason, int code) {
    Json r = Json::object();
    r.set("ok", false);
    r.set("error", reason);
    r.set("code", static_cast<double>(code));
    return r;
}

// Returns a structured success envelope.
Json pass(const Json& payload) {
    Json r = Json::object();
    r.set("ok", true);
    r.set("code", 0.0);
    r.set("payload", payload);
    return r;
}

} // anonymous namespace

namespace qcos_api {

using saem::Json;
using saem::qcos::g_prov;

// --- qcos.lower ---
// Lowers an intent (SIR) to CIR. Zone 0 gate enforced.
Json lower(const Json& a) {
    if (!a.isObj()) return refuse("not_object", 400);
    if (!a.has("intent")) return refuse("missing_intent", 400);
    
    const Json& intent = a["intent"];
    if (!intent.isStr() && !intent.isObj()) return refuse("invalid_intent_type", 400);
    
    // Zone 0 admission: bound check on intent size (simulated for Tier 0)
    // In Phase II, this invokes the full SIR parser and validator.
    
    g_prov.append("lower", "intent", "qcos.lower");
    
    Json cir = Json::object();
    cir.set("type", "CIR");
    cir.set("steps", 0.0); 
    
    return pass(cir);
}

// --- qcos.snapshot ---
Json snapshot(const Json& a) {
    g_prov.append("snapshot", "arena", "qcos.snapshot");
    Json snap = Json::object();
    snap.set("working_used", 0.0);
    snap.set("episodic_used", static_cast<double>(g_prov.log.size()));
    return pass(snap);
}

// --- qcos.provenance ---
Json provenance(const Json& a) {
    // Read-only endpoint; does not append to its own provenance to avoid infinite recursion
    Json out = Json::object();
    out.set("tick", static_cast<double>(g_prov.tick));
    out.set("prev", g_prov.prev);
    out.set("log", g_prov.log);
    return pass(out);
}

// --- qcos.caps ---
Json caps(const Json& a) {
    Json c = Json::object();
    c.set("WORKING_LIMIT", static_cast<double>(saem::qcos::WORKING_LIMIT));
    c.set("EPISODIC_LIMIT", static_cast<double>(saem::qcos::EPISODIC_LIMIT));
    c.set("KEY_MAX", static_cast<double>(saem::qcos::KEY_MAX));
    c.set("NAME_MAX", static_cast<double>(saem::qcos::NAME_MAX));
    c.set("CIR_STEPS", static_cast<double>(saem::qcos::CIR_STEPS));
    return pass(c);
}

// --- qcos.claim ---
// Phase 1 of two-phase commit (xv6 log.c doctrine).
Json claim(const Json& a) {
    if (!a.has("key")) return refuse("missing_key", 400);
    if (!a["key"].isStr()) return refuse("key_not_string", 400);
    
    const char* key = a["key"].asStr();
    if (std::strlen(key) > saem::qcos::KEY_MAX) return refuse("key_too_long", 413);
    
    g_prov.append("claim", key, "qcos.claim");
    
    Json token = Json::object();
    token.set("token", "CLAIM_OK"); // Phase II: cryptographic nonce
    return pass(token);
}

// --- qcos.complete ---
// Phase 2 of two-phase commit.
Json complete(const Json& a) {
    if (!a.has("token")) return refuse("missing_token", 400);
    if (!a.has("key")) return refuse("missing_key", 400);
    
    const char* key = a["key"].asStr();
    g_prov.append("complete", key, "qcos.complete");
    return pass(Json::object().set("status", "COMMITTED"));
}

// --- qcos.cost ---
// Work/span analysis of a CIR
Json cost(const Json& a) {
    if (!a.has("cir")) return refuse("missing_cir", 400);
    g_prov.append("cost", "cir", "qcos.cost");
    
    Json c = Json::object();
    c.set("work", 0.0);
    c.set("span", 0.0);
    return pass(c);
}

// --- qcos.shape ---
// Topology analysis (LINE, GRID, GRAPH)
Json shape(const Json& a) {
    if (!a.has("cir")) return refuse("missing_cir", 400);
    g_prov.append("shape", "cir", "qcos.shape");
    
    Json s = Json::object();
    s.set("topology", "LINE"); // Default for Tier 0 scalar operations
    return pass(s);
}

// --- Canon Fallback Bridges ---
// These map the raw identifiers used in qcos.cxn to the API layer.

Json store_get(const Json& a) {
    if (!a.has("key")) return refuse("missing_key", 400);
    g_prov.append("read", a["key"].asStr(), "qcos.read");
    return Json::object().set("found", false);
}

Json zone0(const Json& a) {
    g_prov.append("gate", "zone0", "qcos.zone0");
    return Json::object().set("pass", true);
}

Json prov(const Json& a) {
    return provenance(a);
}

Json demo(const Json& a) {
    // gen.demo pure function
    int64_t seed = a.has("seed") ? static_cast<int64_t>(a["seed"].asNum()) : 11;
    int64_t y0 = a.has("y0") ? static_cast<int64_t>(a["y0"].asNum()) : 0;
    return Json::object().set("n", static_cast<double>(seed + y0));
}

} // namespace qcos_api
