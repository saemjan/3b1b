// saem_cli: the core as a process. One JSON request per line on stdin, one JSON answer per line on stdout.
//   {"id":1,"method":"gen.make","args":{"id":"K1","seed":7}}  ->  {"id":1,"ok":true,"result":{...}}
// Used by the tests (same protocol as tools/ref_bridge.js) and by anything that prefers a pipe to a library.
#include <cstdio>
#include <iostream>
#include <string>

#include "api.hpp"

#ifndef SAEM_SOURCE_ID
#define SAEM_SOURCE_ID "dev"
#endif

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
      const std::string body = saem::call_json(req["method"].asStr(), req.has("args") ? req["args"].dump() : "{}");
      const saem::Json r = saem::Json::parse(body);
      out.set("ok", r["ok"]);
      if (r["ok"].asBool()) out.set("result", r["result"]);
      else out.set("error", r["error"]);
    } catch (const std::exception& e) {
      out.set("ok", false);
      out.set("error", std::string(e.what()));
    }
    std::cout << out.dump() << "\n";
    std::cout.flush();
  }
  return 0;
}
