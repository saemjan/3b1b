// core/src/cos_api.cpp
#include "api.hpp"
#include <string>
#include <vector>
#include "cos.hpp"
#include "ef.hpp"
#include "gen.hpp"
#include "qreg.hpp"
#include "util.hpp"

namespace saem {
namespace {
Json rows_of(const Json& a) { return a; }

// Fixed: Added `[](const Json& a)` signatures
const Registrar c1("core.methods", [](const Json& a) {
  Json o = Json::array();
  for (const std::string& m : methods()) o.push(Json(m));
  return o;
});
const Registrar c2("core.info", [](const Json& a) {
  Json o = cos::core_object();
  o.set("id", Json(cos::coreHash()));
  o.set("templates", (int)gen::templates().size());
  Json tp = Json::array();
  for (const std::string& t : gen::topics()) tp.push(Json(t));
  o.set("topics", tp);
  return o;
});
const Registrar c3("core.hash", [](const Json& a) { return Json(cos::coreHash()); });
const Registrar c4("core.sha256", [](const Json& a) { return Json(sha256_hex(a["s"].asStr())); });
const Registrar c5("core.receipt", [](const Json& a) {
  return cos::receipt(a["core"].asStr(), a["items"], a["K"].asInt(0), a["notes"]);
});
const Registrar c6("core.audit", [](const Json& a) { return cos::audit(a); });
const Registrar c7("core.selfTest", [](const Json& a) {
  Json failed = Json::array(); int checks = 0;
  // Fixed: Lambda capture syntax
  auto want = [&](bool ok, const char* name) {
    ++checks; if (!ok) failed.push(Json(std::string(name)));
  };
  want(sha256_hex("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "sha256_empty");
  QReg r(2, 7); r.h(0); r.cnot(0, 1);
  want(std::fabs(r.norm() - 1.0) < 1e-12 && std::fabs(r.prob1(0) - 0.5) < 1e-12, "bell");
  want(jsnum(0.1 + 0.2) == "0.30000000000000004", "jsnum_half");
  Bits b = {1, 1, 0, 0};
  std::vector<Gate> adder = {gccnot(0, 1, 2), gcnot(0, 3), gcnot(1, 3)};
  run(b, adder);
  want(b[2] == 1 && b[3] == 0, "adder");
  Json o = Json::object();
  o.set("ok", failed.size() == 0); o.set("checks", checks); o.set("failed", failed);
  return o;
});

const Registrar f1("forecast.fitLR", [](const Json& a) {
  std::vector<std::vector<double>> rows;
  for (const Json& r : a["rows"].arr()) {
    std::vector<double> v;
    for (const Json& x : r.arr()) v.push_back(x.asNum());
    rows.push_back(v);
  }
  std::vector<double> ys;
  for (const Json& y : a["ys"].arr()) ys.push_back(y.asNum());
  return ef::model_json(ef::fitLR(rows, ys, a["lam"].asNum(0.0)));
});
const Registrar f2("forecast.predictLR", [](const Json& a) {
  std::vector<double> x;
  for (const Json& v : a["x"].arr()) x.push_back(v.asNum());
  return Json(ef::predictLR(ef::model_of(a["model"]), x));
});
const Registrar f3("forecast.calibrate", [](const Json& a) { return ef::calibrate(a["logits"], a["ys"]); });
const Registrar f4("forecast.chooseMethod", [](const Json& a) { return ef::chooseMethod(a["prior"].asNum(0), a["lr"].asNum(0)); });
const Registrar f5("forecast.analyze", [](const Json& a) {
  Json ex = a.has("excluded") ? a["excluded"] : Json::array();
  return ef::analyze(a["items"], a["K"].asInt(0), a["tau"].asNum(1.0), a["T"].asNum(0.0), ex);
});
const Registrar f6("forecast.verdict", [](const Json& a) { return ef::verdict(a["fc"]); });

const Registrar t1("text.normKey", [](const Json& a) {
  const u32 u = to_u32(a["s"].asStr()); u32 o; bool prev = true;
  for (char32_t c : u) {
    if (js_space(c)) { if (!prev) { o += u32(1, U' '); prev = true; } }
    else { o += (c >= U'A' && c <= U'Z') ? char32_t(c + 32) : c; prev = false; }
  }
  if (!o.empty() && o.back() == U' ') o.pop_back();
  return Json(to_u8(o));
});
const Registrar t2("text.yearFromHeader", [](const Json& a) {
  const std::string s = a["line"].asStr();
  for (size_t i = 0; i + 3 < s.size(); ++i) {
    // Fixed: Lambda capture syntax
    auto isd = [](char c) { return is_digit(static_cast<char32_t>(c)); };
    if ((s[i] == '1' || s[i] == '2') && isd(s[i]) && isd(s[i+1]) && isd(s[i+2]) && isd(s[i+3])) {
      return Json(std::atoi(s.c_str() + static_cast<long>(i)));
    }
  }
  return Json();
});
const Registrar t3("text.parseDelimited", [](const Json& a) {
  Json out = Json::array();
  const std::string s = a["text"].asStr();
  size_t pos = 0;
  while (pos <= s.size()) {
    size_t nl = s.find('\n', pos);
    const std::string line = s.substr(pos, nl == std::string::npos ? std::string::npos : nl - pos);
    if (!line.empty()) {
      Json row = Json::array();
      const char d = line.find('\t') != std::string::npos ? '\t' : ',';
      size_t p = 0;
      while (p <= line.size()) {
        size_t cut = line.find(d, p);
        row.push(Json(line.substr(p, cut == std::string::npos ? std::string::npos : cut - p)));
        if (cut == std::string::npos) break;
        p = cut + 1;
      }
      out.push(row);
    }
    if (nl == std::string::npos) break;
    pos = nl + 1;
  }
  return out;
});

struct Stubs {
  Stubs() {
    for (const char* n : {"papers.parse", "papers.fromRows", "papers.splitMCQ",
                          "papers.normAnswer", "papers.keyMap", "papers.autoTag",
                          "papers.script", "bank.stats", "bank.rows",
                          "bank.isTestable", "paper.rows"}) {
      // Fixed: Lambda capture syntax
      Registrar(n, [](const Json&) -> Json {
        throw std::runtime_error("spec not extracted: fixture-gated");
      });
    }
  }
};
const Stubs stubs_;
}}
