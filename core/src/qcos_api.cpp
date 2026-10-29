// core/src/qcos_api.cpp
// Defines the global QCOS state and the API entry points.
#pragma once
#include <string>
#include <vector>
#include "qcos.hpp"
#include "kernel.hpp"
#include "json.hpp"

namespace saem {
namespace qcos {

// Global state instances
Working g_working;
Episodic g_episodic;

// Provenance log (defined here if not fully in qcos.hpp)
struct Provenance {
  Json log = Json::array();
  void append(const std::string& op, const std::string& key, const std::string& why) {
    Json e = Json::object();
    e.set("op", op);
    e.set("key", key);
    e.set("why", why);
    log.push(e);
  }
  bool verify() const { return true; }
};
Provenance g_prov;

// Compiler pipeline stubs (Phase II implementation)
inline Json lower_sir(const Json& a) { return Json::object(); }
inline Json lower_dir(const Json& a) { return Json::object(); }
inline Json lower_cir(const Json& a, const Json& dir) { return Json::object(); }
inline Json lower_mir(const Json& a, const std::string& target) { return Json::object(); }

struct ExecResult { bool ok = true; };
inline ExecResult exec_cir(Working& w, const Json& cir) { return ExecResult{true}; }

} // namespace qcos
} // namespace saem

// API functions called by the generated registry
namespace qcos_api {

using namespace saem;
using namespace saem::qcos;

Json latch(const Json& a) {
  Verdict v = gate("latch", a);
  if (!v.ok) return Json(v.reasons);
  const std::string key = a["key"].asStr();
  const Json& val = a["value"];
  bool ok = g_working.latch(key, val);
  Json o = Json::object();
  o.set("ok", ok);
  if (ok) g_prov.append("latch", key, "qcos.latch");
  return o;
}

Json read(const Json& a) {
  Verdict v = gate("read", a);
  if (!v.ok) return Json(v.reasons);
  const std::string key = a["key"].asStr();
  Json o = Json::object();
  Json val = g_working.read(key);
  o.set("found", !val.isNull());
  if (!val.isNull()) o.set("value", val);
  return o;
}

Json snapshot(const Json&) {
  return g_working.snapshot();
}

Json restore(const Json& a) {
  Verdict v = gate("restore", a);
  if (!v.ok) return Json(v.reasons);
  bool ok = g_working.restore(a["snapshot"]);
  Json o = Json::object();
  o.set("ok", ok);
  if (ok) g_prov.append("restore", "l1", "qcos.restore");
  return o;
}

Json episode(const Json& a) {
  Verdict v = gate("episode", a);
  if (!v.ok) return Json(v.reasons);
  g_episodic.push(a["event"]);
  Json o = Json::object();
  o.set("ok", true);
  return o;
}

Json recent(const Json& a) {
  int n = a.has("n") ? a["n"].asInt(0) : 10;
  Json o = Json::object();
  o.set("recent", g_episodic.recent(n));
  return o;
}

Json provenance(const Json&) {
  Json o = Json::object();
  o.set("verify", g_prov.verify());
  o.set("log", g_prov.log);
  return o;
}

Json gate_op(const Json& a) {
  std::string op = a.has("op") ? a["op"].asStr() : "";
  Json args = a.has("args") ? a["args"] : Json::object();
  Verdict v = gate(op, args);
  Json o = Json::object();
  o.set("ok", v.ok);
  o.set("reasons", v.reasons);
  return o;
}

Json lower(const Json& a) {
  Verdict v = gate("lower", a);
  if (!v.ok) return Json(v.reasons);
  Json sir = lower_sir(a);
  Json dir = lower_dir(sir);
  Json cir = lower_cir(sir, dir);
  std::string target = a.has("target") ? a["target"].asStr() : "cpp";
  Json mir = lower_mir(cir, target);
  Json o = Json::object();
  o.set("ok", true);
  o.set("mir", mir);
  return o;
}

Json exec(const Json& a) {
  Verdict v = gate("exec", a);
  if (!v.ok) return Json(v.reasons);
  Json cir = a.has("cir") ? a["cir"] : Json::object();
  ExecResult er = exec_cir(g_working, cir);
  Json o = Json::object();
  o.set("ok", er.ok);
  g_prov.append("exec", "cir", "qcos.exec");
  return o;
}

Json cost(const Json&) {
  Json o = Json::object();
  o.set("cost", 0);
  return o;
}

Json boot(const Json&) {
  Json o = Json::object();
  o.set("ok", true);
  o.set("working_limit", WORKING_LIMIT);
  o.set("episodic_limit", EPISODIC_LIMIT);
  return o;
}

} // namespace qcos_api
