// core/src/qcos_reg.cpp
//
// QCOS session registry.
//
// This file provides the qcos.* methods used by qcos_shell.py and Bridge.cs.
// It is intentionally process-local: one saem_cli process is one OS session.
// The persistent ledger belongs to the caller, as required by the constitution.

#include "api.hpp"
#include "kernel.hpp"
#include "qcos.hpp"
#include "sha256.hpp"

#include <string>

namespace saem {

// ---- Helper functions ----

namespace {

Json error_obj(const std::string& msg) {
  Json o = Json::object();
  o.set("ok", false);
  o.set("error", Json(msg));
  return o;
}

Json verdict_obj(const qcos::Verdict& v) {
  Json o = Json::object();
  o.set("ok", v.ok);
  o.set("reasons", v.reasons);
  if (!v.ok) {
    o.set("error", Json("constitutional gate denied"));
  }
  return o;
}

Json constitution_json() {
  Json arr = Json::array();
  auto add = [&](const char* id, const char* text) {
    Json o = Json::object();
    o.set("id", Json(std::string(id)));
    o.set("text", Json(std::string(text)));
    arr.push(o);
  };
  add("A0", "every answer is computed from the numbers in the question, never guessed");
  add("A1", "every number leaving the core prints exactly as the reference engine prints it");
  add("A2", "the door holds no hidden state; state travels in the JSON, in the caller's ledger");
  add("A3", "measurement and overwrite are the only irreversible acts; the core reports the debt");
  add("A4", "no belief is declared without moral certainty, 1000:1");
  add("A5", "the ledger is append-only; rules without machine checks remain hypotheses");
  add("A6", "the JavaScript bridge is a ruler, never a fallback; the shipped product runs the core alone");
  return arr;
}

// Compiler pipeline stubs (Phase II implementation)
Json lower_sir(const Json& a) {
  Json o = Json::object();
  o.set("ok", true);
  o.set("nodes", Json::array());
  return o;
}

Json lower_dir(const Json& sir) {
  Json o = Json::object();
  o.set("ok", true);
  o.set("shapes", Json::array());
  return o;
}

Json lower_cir(const Json& sir, const Json& dir) {
  Json o = Json::object();
  o.set("ok", true);
  o.set("steps", Json::array());
  return o;
}

Json lower_mir(const Json& cir, const std::string& target) {
  Json o = Json::object();
  o.set("ok", true);
  o.set("instructions", Json::array());
  o.set("target", Json(target));
  return o;
}

struct ExecResult {
  bool ok = true;
  Json trace;
};

ExecResult exec_cir(qcos::Working& w, const Json& cir) {
  ExecResult er;
  er.ok = true;
  er.trace = Json::object();
  er.trace.set("executed", true);
  return er;
}

}  // anonymous namespace

// ---- Process-local session state ----
// The caller's ledger remains the persistent truth.

qcos::Working g_working;
qcos::Provenance g_prov;
qcos::Episodic g_episodic;

// ---- Registrars ----

const Registrar qcos_boot_reg("qcos.boot", [](const Json&) {
  Json self = qcos::self_test();
  Json o = Json::object();
  o.set("ok", self["ok"]);
  o.set("self", self);
  o.set("constitution", constitution_json());
  return o;
});

const Registrar qcos_gate_reg("qcos.gate", [](const Json& a) {
  const std::string op = a["op"].asStr();
  const Json args = a.has("args") ? a["args"] : Json::object();
  qcos::Verdict v = qcos::gate(op, args);
  return verdict_obj(v);
});

const Registrar qcos_latch_reg("qcos.latch", [](const Json& a) {
  if (!a.has("key") || !a.has("value")) {
    return error_obj("qcos.latch: missing key or value");
  }
  qcos::Verdict v = qcos::gate("latch", a);
  if (!v.ok) {
    return verdict_obj(v);
  }
  const std::string key = a["key"].asStr();
  const Json value = a["value"];
  if (!g_working.latch(key, value)) {
    return error_obj("qcos.latch: working memory full or key out of bounds");
  }
  const std::string hash = sha256_hex(canon(value));
  g_prov.append("latch", key, "qcos.latch");
  Json o = Json::object();
  o.set("ok", true);
  o.set("key", Json(key));
  o.set("hash", Json(hash));
  return o;
});

const Registrar qcos_read_reg("qcos.read", [](const Json& a) {
  if (!a.has("key")) {
    return error_obj("qcos.read: missing key");
  }
  const std::string key = a["key"].asStr();
  const Json value = g_working.read(key);
  Json o = Json::object();
  o.set("ok", true);
  o.set("key", Json(key));
  o.set("value", value);
  return o;
});

const Registrar qcos_lower_reg("qcos.lower", [](const Json& a) {
  qcos::Verdict v = qcos::gate("lower", a);
  if (!v.ok) {
    return verdict_obj(v);
  }
  const Json sir = lower_sir(a);
  const Json dir = lower_dir(sir);
  const Json cir = lower_cir(sir, dir);
  const std::string target = a.has("target") ? a["target"].asStr() : "cpp";
  const Json mir = lower_mir(cir, target);
  Json o = Json::object();
  o.set("ok", true);
  o.set("sir", sir);
  o.set("dir", dir);
  o.set("cir", cir);
  o.set("mir", mir);
  return o;
});

const Registrar qcos_exec_reg("qcos.exec", [](const Json& a) {
  if (!a.has("cir")) {
    return error_obj("qcos.exec: missing cir");
  }
  qcos::Verdict v = qcos::gate("exec", a);
  if (!v.ok) {
    return verdict_obj(v);
  }
  const Json cir = a["cir"];
  ExecResult er = exec_cir(g_working, cir);
  Json o = Json::object();
  o.set("ok", er.ok);
  o.set("trace", er.trace);
  if (!er.ok) {
    o.set("error", Json("execution failed"));
    return o;
  }
  const std::string hash = sha256_hex(canon(er.trace));
  g_prov.append("exec", "cir", "qcos.exec");
  o.set("hash", Json(hash));
  return o;
});

const Registrar qcos_snapshot_reg("qcos.snapshot", [](const Json&) {
  Json o = Json::object();
  o.set("ok", true);
  o.set("working", g_working.snapshot());
  o.set("prov", g_prov.log);
  o.set("prev", Json(g_prov.prev));
  o.set("tick", g_prov.tick);
  return o;
});

const Registrar qcos_restore_reg("qcos.restore", [](const Json& a) {
  if (!a.has("snapshot")) {
    return error_obj("qcos.restore: missing snapshot");
  }
  qcos::Verdict v = qcos::gate("restore", a);
  if (!v.ok) {
    return verdict_obj(v);
  }
  const bool ok = g_working.restore(a["snapshot"]);
  if (ok) {
    g_prov.append("restore", "l1", "qcos.restore");
  }
  Json o = Json::object();
  o.set("ok", ok);
  if (!ok) {
    o.set("error", Json("restore failed"));
  }
  return o;
});

const Registrar qcos_episode_reg("qcos.episode", [](const Json& a) {
  qcos::Verdict v = qcos::gate("episode", a);
  if (!v.ok) {
    return verdict_obj(v);
  }
  if (a.has("event")) {
    g_episodic.push(a["event"]);
  }
  int n = a.has("n") ? a["n"].asInt(8) : 8;
  if (n < 0) n = 0;
  Json o = Json::object();
  o.set("ok", true);
  o.set("recent", g_episodic.recent(n));
  return o;
});

const Registrar qcos_provenance_reg("qcos.provenance", [](const Json&) {
  Json o = Json::object();
  o.set("ok", true);
  o.set("verify", g_prov.verify());
  o.set("log", g_prov.log);
  o.set("prev", Json(g_prov.prev));
  o.set("tick", g_prov.tick);
  return o;
});

const Registrar qcos_cost_reg("qcos.cost", [](const Json&) {
  Json o = Json::object();
  o.set("ok", true);
  o.set("debt_bits", 0.0);
  o.set("unit", Json("kT ln 2"));
  return o;
});

}  // namespace saem
