// saemcli v2 — JSON CLI over the Math Brain core (saem::gen).
// Depends ONLY on json.hpp's visible reading/building API + numfmt.hpp.
// Serialization & parsing live here, so the CLI never couples to internals.
// Commands: topics | templates | known <id> | make <id> <seed>
//           question_with <id> <seed> [paramsJson] | solve <id> [paramsJson]
//           bank <seed> <y0> <y1> | vectors | soul | numfmt <x> [precision]
#include "gen.hpp"
#include "sha256.hpp"
#include "util.hpp"
#include "json.hpp"
#include "numfmt.hpp"
#include <iostream>
#include <string>
#include <cmath>
#include <cstdio>
#include <cctype>
#include <stdexcept>

using namespace saem;

// ---------- serializer: standard JSON, JS-exact numbers via jsnum ----------
static void esc(std::string& out, const std::string& s) {
    out += '"';
    for (char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof buf, "\\u%04x", c);
                    out += buf;
                } else out += c;
        }
    }
    out += '"';
}

static void ser(std::string& out, const Json& j, int indent, int depth) {
    const std::string pad (indent ? static_cast<size_t>(indent * (depth + 1)), ' ') : std::string();
    const std::string pad0(indent ? static_cast<size_t>(indent * depth), ' ') : std::string();
    const char* nl = indent ? "\n" : "";
    const char* sp = indent ? " " : "";
    switch (j.type()) {
        case Json::Null:  out += "null"; break;
        case Json::Bool:  out += j.asBool() ? "true" : "false"; break;
        case Json::Num:   out += jsnum(j.asNum()); break;   // JS Number.toString parity
        case Json::Str:   esc(out, j.asStr()); break;
        case Json::Array: {
            out += '[';
            const auto& a = j.arr();
            for (size_t i = 0; i < a.size(); ++i) {
                if (i) out += ',';
                out += nl; out += pad;
                ser(out, a[i], indent, depth + 1);
            }
            if (!a.empty()) { out += nl; out += pad0; }
            out += ']'; break;
        }
        case Json::Object: {
            out += '{';
            const auto& o = j.obj();
            for (size_t i = 0; i < o.size(); ++i) {
                if (i) out += ',';
                out += nl; out += pad;
                esc(out, o[i].first);
                out += ':'; out += sp;
                ser(out, o[i].second, indent, depth + 1);
            }
            if (!o.empty()) { out += nl; out += pad0; }
            out += '}'; break;
        }
    }
}
static std::string dump(const Json& j, int indent = 2) {
    std::string out; ser(out, j, indent, 0); return out;
}
static void emit(const Json& j) { std::cout << dump(j, 2) << "\n"; }

// ---------- parser: standard JSON -> saem::Json (recursive descent) --------
struct Parser {
    const std::string& s; size_t i = 0;
    explicit Parser(const std::string& src) : s(src) {}
    [[noreturn]] static void fail(const std::string& m) { throw std::runtime_error("json: " + m); }
    void ws() { while (i < s.size() && (s[i]==' '||s[i]=='\t'||s[i]=='\n'||s[i]=='\r')) ++i; }
    char peek() { ws(); if (i >= s.size()) fail("unexpected end"); return s[i]; }
    void eat(char c) { if (peek() != c) fail(std::string("expected '") + c + "'"); ++i; }
    void lit(const char* w) { ws(); for (const char* p = w; *p; ++p, ++i)
                                  if (i >= s.size() || s[i] != *p) fail("literal"); }
    Json value() {
        char c = peek();
        if (c == '{') return object();
        if (c == '[') return array();
        if (c == '"') return Json(string());
        if (c == 't') { lit("true");  return Json(true); }
        if (c == 'f') { lit("false"); return Json(false); }
        if (c == 'n') { lit("null");  return Json(nullptr); }
        return number();
    }
    Json object() {
        Json o = Json::object();
        eat('{');
        if (peek() == '}') { ++i; return o; }
        for (;;) {
            std::string k = string();
            eat(':');
            o.set(k, value());
            ws();
            if (i < s.size() && s[i] == ',') { ++i; continue; }
            eat('}'); break;
        }
        return o;
    }
    Json array() {
        Json a = Json::array();
        eat('[');
        if (peek() == ']') { ++i; return a; }
        for (;;) {
            a.push(value());
            ws();
            if (i < s.size() && s[i] == ',') { ++i; continue; }
            eat(']'); break;
        }
        return a;
    }
    std::string string() {
        eat('"');
        std::string out;
        while (i < s.size() && s[i] != '"') {
            char c = s[i++];
            if (c != '\\') { out += c; continue; }
            if (i >= s.size()) fail("escape");
            char e = s[i++];
            switch (e) {
                case '"': out += '"'; break;
                case '\\': out += '\\'; break;
                case '/': out += '/'; break;
                case 'n': out += '\n'; break;
                case 'r': out += '\r'; break;
                case 't': out += '\t'; break;
                case 'b': out += '\b'; break;
                case 'f': out += '\f'; break;
                case 'u': {
                    if (i + 4 > s.size()) fail("unicode");
                    unsigned cp = std::stoul(s.substr(i, 4), nullptr, 16); i += 4;
                    if (cp >= 0xD800 && cp <= 0xDFFF) cp = 0xFFFD;
                    if (cp < 0x80) out += static_cast<char>(cp);
                    else if (cp < 0x800) {
                        out += static_cast<char>(0xC0 | (cp >> 6));
                        out += static_cast<char>(0x80 | (cp & 63));
                    } else {
                        out += static_cast<char>(0xE0 | (cp >> 12));
                        out += static_cast<char>(0x80 | ((cp >> 6) & 63));
                        out += static_cast<char>(0x80 | (cp & 63));
                    }
                    break;
                }
                default: fail("escape");
            }
        }
        if (i >= s.size()) fail("string");
        ++i;
        return out;
    }
    Json number() {
        ws();
        size_t b = i;
        if (i < s.size() && (s[i]=='-'||s[i]=='+')) ++i;
        while (i < s.size() && (std::isdigit(static_cast<unsigned char>(s[i]))
               || s[i]=='.' || s[i]=='e' || s[i]=='E' || s[i]=='+' || s[i]=='-')) ++i;
        if (b == i) fail("number");
        return Json(parse_double(s.substr(b, i - b)));
    }
};

// ------------------------------- commands ----------------------------------
int main(int argc, char** argv) {
    if (argc < 2) { std::cerr << "usage: saemcli <cmd> [args]\n"; return 2; }
    std::string cmd = argv[1];
    try {
        if (cmd == "topics") {
            Json a = Json::array();
            for (const auto& t : gen::topics()) a.push(Json(t));
            emit(a); return 0;
        }
        if (cmd == "templates") {
            Json a = Json::array();
            for (const auto& t : gen::templates()) {
                Json o; o.set("id", t.id); o.set("topic", t.topic); a.push(o);
            }
            emit(a); return 0;
        }
        if (cmd == "vectors") { emit(gen::vectors()); return 0; }
        if (cmd == "known") {
            if (argc < 3) return 2;
            Json o; o.set("id", std::string(argv[2]));
            o.set("known", gen::known(argv[2])); emit(o); return 0;
        }
        if (cmd == "make") {
            if (argc < 4) return 2;
            Rng R(static_cast<uint32_t>(std::stoul(argv[3])));
            emit(gen::question_json(gen::make(argv[2], R))); return 0;
        }
        if (cmd == "question_with") {
            if (argc < 4) return 2;
            Json params = (argc > 4) ? Parser(argv[4]).value() : Json::object();
            emit(gen::question_json(gen::question_with(
                argv[2], params, static_cast<uint32_t>(std::stoul(argv[3])))));
            return 0;
        }
        if (cmd == "solve") {
            if (argc < 3) return 2;
            Json params = (argc > 3) ? Parser(argv[3]).value() : Json::object();
            emit(gen::solve(argv[2], params)); return 0;
        }
        if (cmd == "bank") {
            if (argc < 5) return 2;
            emit(gen::demo_bank(static_cast<uint32_t>(std::stoul(argv[2])),
                                std::stoi(argv[3]), std::stoi(argv[4])));
            return 0;
        }
        if (cmd == "numfmt") {
            if (argc < 3) return 2;
            double x = parse_double(argv[2]);
            Json o; o.set("jsnum", jsnum(x));
            if (argc > 3) o.set("toPrecision", jsnum(round_sig(x, std::stoi(argv[3]))));
            emit(o); return 0;
        }
        if (cmd == "soul") {
            std::string acc = "saem-mathbrain-v1";
            for (const auto& t : gen::templates()) { acc += "|"; acc += t.id; acc += ","; acc += t.topic; }
            for (const auto& t : gen::topics())    { acc += ";"; acc += t; }
            Json o; o.set("soul", sha256_hex(acc)); o.set("version", 1); emit(o); return 0;
        }
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n"; return 1;
    }
    std::cerr << "unknown command: " << cmd << "\n";
    return 2;
}
