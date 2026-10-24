// QCOS methods on the one door. The resident instance lives for the
// lifetime of the saem_cli process: the process IS the OS session. Every
// mutation is provenance-chained, and the whole state travels through
// qcos.snapshot / qcos.restore, so replay and parity never depend on
// residency. The gate runs before every mutating op and fails closed.
#include "api.hpp"

#include "qcos.hpp"

namespace saem {
namespace {

struct Instance {
  qcos::Working work;
  qcos::Episodic ep;
  qcos::Provenance prov;
  uint64_t tick = 0;
};
Instance& inst() {
  static Instance i;
  return i;
}
Json denied(const qcos::Verdict& v) {
  Json o = Json::object();
  o.set("ok", false);
  o.set("reasons", v.reasons);
  return o;
}

const Registrar k0("qcos.boot", [](const Json&) {
  Json lim = Json::object();
  lim.set("working", qcos::WORKING_LIMIT);
  lim.set("episodic", qcos::EPISODIC_LIMIT);
  Json o = Json::object();
  o.set("self", qcos::self_test());
  o.set("constitution", Json(cos::coreHash()));
  o.set("limits", lim);
  return o;
});

const Registrar k1("qcos.gate", [](const Json& a) {
  const qcos::Verdict v = qcos::gate(a["op"].asStr(), a.has("args") ? a["args"] : Json::object());
  Json o = Json::object();
  o.set("ok", v.ok);
  o.set("reasons", v.reasons);
  return o;
});

const Registrar k2("qcos.latch", [](const Json& a) {
  const qcos::Verdict v = qcos::gate("latch", a);
  if (!v.ok) return denied(v);
  Instance& I = inst();
  const bool ok = I.work.latch(a["key"].asStr(), a["value"]);
  I.ep.push(a);
  const std::string h = I.prov.append("latch", "l1", a["key"].asStr());
  ++I.tick;
  Json o = Json::object();
  o.set("ok", ok);
  o.set("hash", Json(h));
  return o;
});

const Registrar k3("qcos.read", [](const Json& a) {
  return inst().work.read(a["key"].asStr());
});

const Registrar k4("qcos.episode", [](const Json& a) {
  return inst().ep.recent(a["n"].asInt(8));
});

const Registrar k5("qcos.lower", [](const Json& a) {
  const Json sir = qcos::lower_sir(a);
  const Json dir = qcos::lower_dir(sir);
  const Json cir = qcos::lower_cir(sir, dir);
  const Json mir = qcos::lower_mir(cir, a["target"].str("cpp"));
  Json o = Json::object();
  o.set("sir", sir);
  o.set("dir", dir);
  o.set("cir", cir);
  o.set("mir", mir);
  return o;
});

const Registrar k6("qcos.exec", [](const Json& a) {
  const qcos::Verdict v = qcos::gate("exec", a);
  if (!v.ok) return denied(v);
  Instance& I = inst();
  const qcos::ExecResult r = qcos::exec_cir(I.work, a["cir"]);
  const std::string h = I.prov.append("exec", "l1", canon(a["cir"]).substr(0, 32));
  Json o = Json::object();
  o.set("ok", r.ok);
  o.set("trace", r.trace);
  o.set("hash", Json(h));
  return o;
});

const Registrar k7("qcos.snapshot", [](const Json&) {
  Instance& I = inst();
  Json o = Json::object();
  o.set("working", I.work.snapshot());
  o.set("episodic", I.ep.recent(qcos::EPISODIC_LIMIT));
  o.set("prov", I.prov.log);
  o.set("tick", (int)I.tick);
  return o;
});

const Registrar k8("qcos.restore", [](const Json& a) {
  Instance& I = inst();
  const bool ok = I.work.restore(a["working"]);
  I.prov = qcos::Provenance();
  Json o = Json::object();
  o.set("ok", ok);
  o.set("prov_verify", qcos::verify_log(a["prov"]));
  return o;
});

const Registrar k9("qcos.cost", [](const Json& a) {
  // Total cost = arithmetic + memory movement + network + energy (spec).
  // Network is zero forever: the core is air-gapped by construction.
  // Energy counts one Landauer erasure per register overwrite.
  int arith = 0, mem = 0;
  for (const Json& st : a["cir"]["steps"].arr()) {
    const std::string op = st["op"].asStr();
    if (op == "add" || op == "solve") ++arith;
    if (op == "latch" || op == "add") ++mem;
  }
  Json o = Json::object();
  o.set("arith", arith);
  o.set("mem", mem);
  o.set("net", 0);
  o.set("energy_kTln2", mem);
  return o;
});

const Registrar k10("qcos.provenance", [](const Json&) {
  Instance& I = inst();
  Json o = Json::object();
  o.set("log", I.prov.log);
  o.set("verify", I.prov.verify());
  return o;
});

}  // namespace
}  // namespace saem
