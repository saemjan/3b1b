// Minimal JSON for the Saem core. No dependencies. Objects keep insertion
// order, strings are UTF-8, numbers print in their shortest round-trip
// form through jsnum, missing fields never throw.
#pragma once
#include <cstdio>   // for snprintf used in esc_to
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "numfmt.hpp"

namespace saem {

class Json {
 public:
  enum Type : uint8_t { Null, Bool, Num, Str, Array, Object };
  using Arr = std::vector<Json>;
  using Obj = std::vector<std::pair<std::string, Json>>;

  Json() = default;
  Json(std::nullptr_t) {}
  Json(bool v) : t_(Bool), b_(v) {}
  template <class T, typename std::enable_if<
                         std::is_arithmetic<T>::value &&
                         !std::is_same<T, bool>::value, int>::type = 0>
  Json(T v) : t_(Num), n_(static_cast<double>(v)) {}
  Json(const char* v) : t_(Str), s_(v) {}
  Json(std::string v) : t_(Str), s_(std::move(v)) {}

  static Json array() { Json j; j.t_ = Array; return j; }
  static Json object() { Json j; j.t_ = Object; return j; }

  Type type() const { return t_; }
  bool isNull() const { return t_ == Null; }
  bool isBool() const { return t_ == Bool; }
  bool isNum() const { return t_ == Num; }
  bool isStr() const { return t_ == Str; }
  bool isArr() const { return t_ == Array; }
  bool isObj() const { return t_ == Object; }

  bool asBool(bool d = false) const { return t_ == Bool ? b_ : d; }
  double asNum(double d = 0) const { return t_ == Num ? n_ : d; }
  int asInt(int d = 0) const {
    return t_ == Num ? static_cast<int>(std::llround(n_)) : d;
  }
  const std::string& asStr() const { return t_ == Str ? s_ : empty_str(); }
  std::string str(const std::string& d) const { return t_ == Str ? s_ : d; }
  const Arr& arr() const { return t_ == Array ? a_ : empty_arr(); }
  const Obj& obj() const { return t_ == Object ? o_ : empty_obj(); }
  size_t size() const {
    return t_ == Array ? a_.size() : t_ == Object ? o_.size() : 0;
  }
  const Json& operator[](const std::string& k) const {
    if (t_ == Object)
      for (const auto& kv : o_)
        if (kv.first == k) return kv.second;
    return null_json();
  }
  const Json& operator[](size_t i) const {
    return (t_ == Array && i < a_.size()) ? a_[i] : null_json();
  }
  bool has(const std::string& k) const {
    if (t_ == Object)
      for (const auto& kv : o_)
        if (kv.first == k) return true;
    return false;
  }
  bool truthy() const {
    switch (t_) {
      case Null: return false;
      case Bool: return b_;
      case Num: return n_ != 0 && !std::isnan(n_);
      case Str: return !s_.empty();
      default: return true;
    }
  }

  Json& push(Json v) {
    if (t_ != Array) { t_ = Array; a_.clear(); }
    a_.push_back(std::move(v));
    return *this;
  }
  Json& set(const std::string& k, Json v) {
    if (t_ != Object) { t_ = Object; o_.clear(); }
    for (auto& kv : o_)
      if (kv.first == k) { kv.second = std::move(v); return *this; }
    o_.emplace_back(k, std::move(v));
    return *this;
  }

  std::string dump() const {
    std::string out;
    dump_to(out);
    return out;
  }
  static Json parse(const std::string& s);

 private:
  Type t_ = Null;
  bool b_ = false;
  double n_ = 0;
  std::string s_;
  Arr a_;
  Obj o_;

  static const std::string& empty_str() { static const std::string e; return e; }
  static const Arr& empty_arr() { static const Arr e; return e; }
  static const Obj& empty_obj() { static const Obj e; return e; }
  static const Json& null_json() { static const Json e; return e; }

  static void esc_to(std::string& out, const std::string& s) {
    out += '"';
    for (unsigned char c : s) {
      if (c == '"' || c == '\\') { out += '\\'; out += static_cast<char>(c); }
      else if (c == '\n') out += "\\n";
      else if (c == '\t') out += "\\t";
      else if (c == '\r') out += "\\r";
      else if (c < 0x20) {
        char b[8];
        std::snprintf(b, sizeof b, "\\u%04x", c);
        out += b;
      } else out += static_cast<char>(c);
    }
    out += '"';
  }
  void dump_to(std::string& out) const {
    switch (t_) {
      case Null: out += "null"; break;
      case Bool: out += b_ ? "true" : "false"; break;
      case Num: out += jsnum(n_); break;
      case Str: esc_to(out, s_); break;
      case Array: {
        out += '[';
        for (size_t i = 0; i < a_.size(); ++i) {
          if (i) out += ',';
          a_[i].dump_to(out);
        }
        out += ']';
        break;
      }
      case Object: {
        out += '{';
        for (size_t i = 0; i < o_.size(); ++i) {
          if (i) out += ',';
          esc_to(out, o_[i].first);
          out += ':';
          o_[i].second.dump_to(out);
        }
        out += '}';
        break;
      }
    }
  }
};

namespace json_parse {
struct P {
  const std::string& s;
  size_t i = 0;
  explicit P(const std::string& v) : s(v) {}
  void ws() {
    while (i < s.size() && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) ++i;
  }
  void expect(char c) {
    if (i >= s.size() || s[i] != c) throw std::runtime_error("json: expected char");
    ++i;
  }
  std::string str() {
    expect('"');
    std::string out;
    while (i < s.size() && s[i] != '"') {
      char c = s[i++];
      if (c != '\\') { out += c; continue; }
      if (i >= s.size()) throw std::runtime_error("json: bad escape");
      char e = s[i++];
      switch (e) {
        case '"': out += '"'; break;
        case '\\': out += '\\'; break;
        case '/': out += '/'; break;
        case 'b': out += '\b'; break;
        case 'f': out += '\f'; break;
        case 'n': out += '\n'; break;
        case 'r': out += '\r'; break;
        case 't': out += '\t'; break;
        case 'u': {
          if (i + 4 > s.size()) throw std::runtime_error("json: bad \\u");
          unsigned cp = std::stoul(s.substr(i, 4), nullptr, 16);
          i += 4;
          if (cp >= 0xD800 && cp <= 0xDBFF && i + 6 <= s.size() &&
              s[i] == '\\' && s[i + 1] == 'u') {
            unsigned lo = std::stoul(s.substr(i + 2, 4), nullptr, 16);
            if (lo >= 0xDC00 && lo <= 0xDFFF) {
              cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
              i += 6;
            }
          }
          if (cp < 0x80) out += static_cast<char>(cp);
          else if (cp < 0x800) {
            out += static_cast<char>(0xC0 | (cp >> 6));
            out += static_cast<char>(0x80 | (cp & 0x3F));
          } else if (cp < 0x10000) {
            out += static_cast<char>(0xE0 | (cp >> 12));
            out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (cp & 0x3F));
          } else {
            out += static_cast<char>(0xF0 | (cp >> 18));
            out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
            out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (cp & 0x3F));
          }
          break;
        }
        default: throw std::runtime_error("json: bad escape");
      }
    }
    expect('"');
    return out;
  }
  Json value() {
    ws();
    if (i >= s.size()) throw std::runtime_error("json: unexpected end");
    char c = s[i];
    if (c == '{') {
      Json o = Json::object();
      ++i; ws();
      if (i < s.size() && s[i] == '}') { ++i; return o; }
      while (true) {
        ws();
        std::string k = str();
        ws(); expect(':');
        o.set(k, value());
        ws();
        if (i < s.size() && s[i] == ',') { ++i; continue; }
        expect('}');
        return o;
      }
    }
    if (c == '[') {
      Json a = Json::array();
      ++i; ws();
      if (i < s.size() && s[i] == ']') { ++i; return a; }
      while (true) {
        a.push(value());
        ws();
        if (i < s.size() && s[i] == ',') { ++i; continue; }
        expect(']');
        return a;
      }
    }
    if (c == '"') return Json(str());
    if (s.compare(i, 4, "true") == 0) { i += 4; return Json(true); }
    if (s.compare(i, 5, "false") == 0) { i += 5; return Json(false); }
    if (s.compare(i, 4, "null") == 0) { i += 4; return Json(); }
    char* end = nullptr;
    double d = std::strtod(s.c_str() + i, &end);
    if (end == s.c_str() + i) throw std::runtime_error("json: bad number");
    i = static_cast<size_t>(end - s.c_str());
    return Json(d);
  }
};
}  // namespace json_parse

inline Json Json::parse(const std::string& s) {
  json_parse::P p(s);
  Json v = p.value();
  p.ws();
  if (p.i != s.size()) throw std::runtime_error("json: trailing garbage");
  return v;
}

}  // namespace saem
