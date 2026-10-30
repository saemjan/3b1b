// core/src/grow_reg.cpp — Gen-3 Grow Registrar (Step 13)
// Doctrine: Single door, fail-closed, provenance per transition, bounded store.

#include "qcos.hpp"
#include "grow.h"
#include "cog.hpp"
#include <cstring>

namespace saem {
namespace qcos {

// --- Forward declarations ---
static Json h_grow_learn(const Json& a, Verdict& v);
static Json h_grow_recall(const Json& a, Verdict& v);
static Json h_grow_distill(const Json& a, Verdict& v);

// --- Registry Table Extension ---
// (In a real build, these are appended to the main kTable in qcos_reg.cpp. 
// For this file, we assume they are linked in.)
extern const RegEntry kTable[]; // Defined in qcos_reg.cpp

// --- Handlers ---

static Json refuse(Verdict& v, int code, const char* why) {
    v.ok = false; v.code = code; v.error = why;
    return Json::object();
}

static Json h_grow_learn(const Json& a, Verdict& v) {
    if (!a.has("hash") || !a["hash"].isStr()) return refuse(v, 400, "missing_hash");
    const std::string hash_str = a["hash"].asStr();
    if (hash_str.length() != 64) return refuse(v, 400, "hash_bad_len"); // SHA-256 hex is 64 chars
    
    // Convert hex to bytes (simplified for example; use a real hex decoder in prod)
    uint8_t hash_bytes[32] = {0}; 
    // ... hex decoding logic ...
    
    int32_t slot = grow_learn(hash_bytes, 32);
    if (slot < 0) return refuse(v, 429, "quarantine_exhausted");
    
    g_prov.append("grow.learn", hash_str, "grow_reg");
    Json o = Json::object();
    o.set("ok", true);
    o.set("slot", (int)slot);
    return o;
}

static Json h_grow_recall(const Json& a, Verdict& v) {
    if (!a.has("hash") || !a["hash"].isStr()) return refuse(v, 400, "missing_hash");
    const std::string hash_str = a["hash"].asStr();
    if (hash_str.length() != 64) return refuse(v, 400, "hash_bad_len");
    
    uint8_t hash_bytes[32] = {0};
    // ... hex decoding logic ...
    
    int32_t slot = grow_recall(hash_bytes, 32);
    g_prov.append("grow.recall", hash_str, "grow_reg");
    
    Json o = Json::object();
    if (slot < 0) {
        o.set("ok", true);
        o.set("found", false);
        return o;
    }
    
    uint32_t cases = 0;
    bool promoted = false;
    grow_get_slot(slot, nullptr, &cases, &promoted);
    
    o.set("ok", true);
    o.set("found", true);
    o.set("slot", (int)slot);
    o.set("cases", (int)cases);
    o.set("promoted", promoted);
    return o;
}

static Json h_grow_distill(const Json& a, Verdict& v) {
    if (!a.has("slot") || !a["slot"].isNum()) return refuse(v, 400, "missing_slot");
    int32_t slot = (int32_t)a["slot"].asNum();
    uint32_t min_cases = a.has("min_cases") ? (uint32_t)a["min_cases"].asNum() : 3;
    
    bool ok = grow_distill(slot, min_cases);
    if (!ok) return refuse(v, 400, "distill_failed");
    
    g_prov.append("grow.distill", "slot_" + std::to_string(slot), "grow_reg");
    
    Json o = Json::object();
    o.set("ok", true);
    o.set("status", "DISTILLED");
    return o;
}

} // namespace qcos
} // namespace saem
