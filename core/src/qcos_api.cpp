// core/src/qcos_api.cpp — Step 12: The Door (vision-first).
// Wires the generated api_registry.g.cpp to the static arenas in qcos.hpp
// and the process kernel in kernel.hpp. 
// Fail-closed: bad JSON or missing fields return empty objects or ok:false.
// No exceptions escape this file.

#include "qcos.hpp"
#include "kernel.hpp"
#include "arena.hpp"
#include <string>

namespace qcos_api {
using namespace saem;

// Singletons for the door's state (backed by the static arrays in qcos.hpp)
static Working  g_working;
static Episodic g_episodic;
static Kernel   g_kernel;

// --- Helpers (fail-closed extraction) ---
static bool get_str(const Json& a, const char* k, std::string& out) {
  if (!a.has(k) || !a[k].isStr()) return false;
  out = a[k].asStr();
  return true;
}

// --- Door Methods (called by Registrar in api_registry.g.cpp) ---

Json boot(const Json&) {
  qcos::g_arena.init();
  Json res = Json::object();
  res.set("ok", Json(true));
  res.set("working_limit", Json(WORKING_LIMIT));
  res.set("episodic_limit", Json(EPISODIC_LIMIT));
  
  Json evt = Json::object();
  evt.set("type", Json("boot"));
  g_episodic.push(evt);
  return res;
}

Json gate(const Json& a) {
  std::string op;
  Json res = Json::object();
  if (!get_str(a, "op", op)) {
    res.set("ok", Json(false));
    res.set("error", Json("missing op"));
    return res;
  }
  
  Json args = a.has("args") ? a["args"] : Json::object();
  GateResult gr = saem::gate(op, args);
  
  res.set("ok", Json(gr.ok));
  if (!gr.ok) {
    res.set("error", Json(gr.error));
    res.set("verdict", Json(gr.verdict));
  }
  return res;
}

Json latch(const Json& a) {
  std::string key;
  Json res = Json::object();
  if (!get_str(a, "key", key) || !a.has("value")) {
    res.set("ok", Json(false));
    return res;
  }
  
  bool ok = g_working.latch(key, a["value"]);
  res.set("ok", Json(ok));
  if (ok) {
    res.set("hash", Json(sha256_hex(canon(a["value"]))));
  }
  return res;
}

Json read(const Json& a) {
  std::string key;
  Json res = Json::object();
  if (!get_str(a, "key", key)) {
    res.set("found", Json(false));
    return res;
  }
  
  bool has = g_working.has(key);
  res.set("found", Json(has));
  if (has) {
    res.set("value", g_working.read(key));
  }
  return res;
}

Json snapshot(const Json&) {
  return g_working.snapshot();
}

Json provenance(const Json&) {
  return saem::provenance();
}

Json caps(const Json&) {
  return saem::caps_report();
}

Json claim(const Json& a) {
  std::string name;
  Json res = Json::object();
  // Using 'id' as the proc name for this basic lifecycle stub
  if (!get_str(a, "id", name)) {
    res.set("found", Json(false)); 
    return res;
  }
  Proc* p = g_kernel.find(name);
  res.set("found", Json(p != nullptr));
  return res;
}

Json complete(const Json& a) {
  std::string name;
  Json res = Json::object();
  if (!get_str(a, "id", name)) {
    res.set("ok", Json(false)); 
    return res;
  }
  Proc* p = g_kernel.find(name);
  if (p) {
    g_kernel.reap(p);
    res.set("ok", Json(true));
  } else {
    res.set("ok", Json(false));
  }
  return res;
}

Json exec(const Json& a) {
  Json res = Json::object();
  if (!a.has("cir") || !a["cir"].isObj()) {
    res.set("ok", Json(false)); 
    return res;
  }
  // Basic CIR executor: record the schedule in episodic memory
  g_episodic.push(a["cir"]);
  res.set("ok", Json(true));
  res.set("hash", Json(sha256_hex(canon(a["cir"]))));
  return res;
}

Json lower(const Json& a) {
  Json res = Json::object();
  res.set("target", a.has("target") ? a["target"] : Json("cpp"));
  res.set("ok", Json(true));
  return res;
}

Json cost(const Json& a) {
  Json res = Json::object();
  res.set("steps", Json(0)); // Stub for now, real cost analysis comes in Phase G
  return res;
}

Json shape(const Json& a) {
  Json res = Json::object();
  res.set("topo", a.has("topo") ? a["topo"] : Json("LINE"));
  res.set("n", a.has("n") ? a["n"] : Json(0));
  return res;
}

} // namespace qcos_api
