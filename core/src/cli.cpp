// saem_cli: the core as a process. One JSON request per line on stdin,
// one JSON answer per line on stdout. A malformed line is refused WITH
// its id recovered, so the caller's ledger never breaks.
#include <cstdio>
#include <iostream>
#include <string>

#include "api.hpp"

#ifndef SAEM_SOURCE_ID
#define SAEM_SOURCE_ID "dev"
#endif

namespace {
// Best-effort id recovery without a full parse (for malformed lines).
saem::Json id_of(const std::string& line) {
  size_t k = line.find("\"id\"");
  if (k == std::string::npos) return saem::Json();
  k = line.find(':', k);
  if (k == std::string::npos) return saem::Json();
  ++k;
  while (k < line.size() && (line[k] == ' ' || line[k] == '\t')) ++k;
  size_t s = k;
  if (k < line.size() && (line[k] == '-' || line[k] == '+')) ++k;
  while (k < line.size() && line[k] >= '0' && line[k] <= '9') ++k;
  if (k == s) return saem::Json();
  return saem::Json(std::strtod(line.substr(s, k - s).c_str(), nullptr));
}
}  // namespace

int main(int argc, char** argv) {
  if (argc > 1 && std::string(argv[1]) == "--source-id") {
    std::printf("%s\n", SAEM_SOURCE_ID);
    return 0;
  }
  std::ios::sync_with_stdio(false);
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
    saem::Json out = saem::Json::object();
    try {
      const saem::Json req = saem::Json::parse(line);
      out.set("id", req["id"]);
      const std::string body = saem::call_json(
          req["method"].asStr(), req.has("args") ? req["args"].dump() : "{}");
      const saem::Json r = saem::Json::parse(body);
      out.set("ok", r["ok"]);
      if (r["ok"].asBool()) out.set("result", r["result"]);
      else out.set("error", r["error"]);
    } catch (const std::exception& e) {
      out.set("id", id_of(line));  // recover, never orphan the caller
      out.set("ok", false);
      out.set("error", std::string(e.what()));
    }
    std::cout << out.dump() << "\n";
    std::cout.flush();
  }
  return 0;
}
