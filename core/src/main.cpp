// core/src/main.cpp
//
// Legacy CLI body for saemcli. Speaks the same line protocol as saem_cli:
// one JSON request per line, one JSON answer per line.

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
    if (line.find_first_not_of(" \t\r\n") == std::string::npos) {
      continue;
    }

    saem::Json out = saem::Json::object();

    try {
      const saem::Json req = saem::Json::parse(line);
      out.set("id", req["id"]);

      const std::string method = req["method"].asStr();
      const std::string args_text =
          req.has("args") ? req["args"].dump() : "{}";

      const std::string body = saem::call_json(method, args_text);
      const saem::Json r = saem::Json::parse(body);

      out.set("ok", r["ok"]);

      if (r["ok"].asBool()) {
        out.set("result", r["result"]);
      } else {
        out.set("error", r["error"]);
      }
    } catch (const std::exception& e) {
      out.set("ok", false);
      out.set("error", std::string(e.what()));
    } catch (...) {
      out.set("ok", false);
      out.set("error", "unknown failure");
    }

    std::cout << out.dump() << "\n";
    std::cout.flush();
  }

  return 0;
}
