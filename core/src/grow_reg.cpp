// Growth methods on the one door. Corrected: dynamic buffer + error propagation.
#include "api.hpp"
#include <string>
#include <vector>
#include <stdexcept>

extern "C" {
int saem_learn(const char*, const char*, const char*, const char*, const char*, const char*);
int saem_recall(const char*, const char*, const char*, char*, size_t);
int saem_count(const char*, const char*);
int saem_write_lib(const char*, const char*, const char*, int);
int saem_read_lib(const char*, const char*, char*);
}

namespace saem {
namespace {

const char* STORE = "knowledge/cases.tsv";
const char* QDIR  = "grown";

const Registrar w30("grow.learn", [](const Json& a) {
  const std::string m = a["method"].asStr();
  const std::string k = canon(a["args"]);
  const std::string o = canon(a["result"]);
  const std::string args = a["args"].dump();
  const std::string w = a["witness"].str("");
  const int seq = saem_learn(STORE, m.c_str(), k.c_str(), args.c_str(), o.c_str(), w.c_str());
  if (seq < 0)
    throw std::runtime_error("grow.learn failed (I/O or memory)");
  Json r = Json::object();
  r.set("seq", seq);
  return r;
});

const Registrar w31("grow.recall", [](const Json& a) {
  std::vector<char> buf(1 << 20);
  if (saem_recall(STORE, a["method"].asStr().c_str(),
                  canon(a["args"]).c_str(),
                  buf.data(), buf.size())) {
    return Json::parse(buf.data());
  }
  return Json();  // null = ungrown (honest)
});

const Registrar w32("grow.distill", [](const Json& a) {
  const std::string n = a["name"].asStr();
  const int rc = saem_write_lib(QDIR, n.c_str(), STORE, a["min"].asInt(3));
  Json r = Json::object();
  r.set("ok", rc == 0);
  r.set("rc", rc);
  if (rc == 0) {
    char h[65] = {0};
    if (saem_read_lib(QDIR, n.c_str(), h))
      r.set("body", Json(std::string(h)));
  }
  return r;
});

const Registrar w33("grow.cases", [](const Json& a) {
  Json r = Json::object();
  r.set("n", saem_count(STORE, a["method"].asStr().c_str()));
  return r;
});

}  // namespace
}  // namespace saem
