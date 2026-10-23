// saemcli — JSON CLI over the Math Brain core (saem::gen).
// Commands: topics | templates | known <id> | make <id> <seed>
//           question_with <id> <seed> [paramsJson] | solve <id> [paramsJson]
//           bank <seed> <y0> <y1> | vectors | soul
#include "gen.hpp"
#include "sha256.hpp"
#include "util.hpp"
#include "json.hpp"
#include <iostream>
#include <string>

using namespace saem;

static Json J_parse(const std::string& s) {
    return Json::parse(s);            // nlohmann-style; swap to json_parse(s) if custom
}
static void emit(const Json& j) {
    std::cout << j.dump(2) << "\n";   // swap to json_to_string(j) if custom
}

int main(int argc, char** argv) {
    if (argc < 2) { std::cerr << "usage: saemcli <cmd> [args]\n"; return 2; }
    std::string cmd = argv[1];

    if (cmd == "topics") {
        Json a = Json::array();
        for (const auto& t : gen::topics()) a.push_back(Json(t));
        emit(a); return 0;
    }
    if (cmd == "templates") {
        Json a = Json::array();
        for (const auto& t : gen::templates()) {
            Json o; o["id"] = t.id; o["topic"] = t.topic; a.push_back(o);
        }
        emit(a); return 0;
    }
    if (cmd == "vectors") { emit(gen::vectors()); return 0; }
    if (cmd == "known") {
        if (argc < 3) return 2;
        Json o; o["id"] = argv[2]; o["known"] = gen::known(argv[2]); emit(o); return 0;
    }
    if (cmd == "make") {
        if (argc < 4) return 2;
        Rng R(static_cast<uint32_t>(std::stoul(argv[3])));
        emit(gen::question_json(gen::make(argv[2], R))); return 0;
    }
    if (cmd == "question_with") {
        if (argc < 4) return 2;
        Json params = (argc > 4) ? J_parse(argv[4]) : Json::object();
        emit(gen::question_json(gen::question_with(
            argv[2], params, static_cast<uint32_t>(std::stoul(argv[3])))));
        return 0;
    }
    if (cmd == "solve") {
        if (argc < 3) return 2;
        Json params = (argc > 3) ? J_parse(argv[3]) : Json::object();
        emit(gen::solve(argv[2], params)); return 0;
    }
    if (cmd == "bank") {
        if (argc < 5) return 2;
        emit(gen::demo_bank(static_cast<uint32_t>(std::stoul(argv[2])),
                            std::stoi(argv[3]), std::stoi(argv[4])));
        return 0;
    }
    if (cmd == "soul") {
        std::string acc = "saem-mathbrain-v1";
        for (const auto& t : gen::templates()) { acc += "|"; acc += t.id; acc += ","; acc += t.topic; }
        for (const auto& t : gen::topics())    { acc += ";"; acc += t; }
        Json o; o["soul"] = sha256_hex(acc); o["version"] = 1; emit(o); return 0;
    }
    std::cerr << "unknown command: " << cmd << "\n";
    return 2;
}
