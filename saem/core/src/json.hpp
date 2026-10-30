// Minimal JSON for the Saem core. No dependencies.
// Objects keep insertion order, strings are UTF-8, numbers print in their shortest round-trip form.
#pragma once
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <type_traits>
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
  template <class T, typename std::enable_if<std::is_arithmetic<T>::value && !std::is_same<T, bool>::value, int>::type = 0>
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

  // ---- reading: every accessor has a safe default, so a missing field never throws
  bool asBool(bool d = false) const { return t_ == Bool ? b_ : d; }
  double asNum(double d = 0) const { return t_ == Num ? n_ : d; }
  int asInt(int d = 0) const { return t_ == Num ? static_cast<int>(std::llround(n_)) : d; }
  const std::string& asStr() const { return t_ == Str ? s_ : empty_str(); }
  std::string str(const std::string& d) const { return t_ == Str ? s_ : d; }
  const Arr& arr() const { return t_ == Array ? a_ : empty_arr(); }
  const Obj& obj() const { return t_ == Object ? o_ : empty_obj(); }
  size_t size() const { return t_ == Array ? a_.size() : t_ == Object ? o_.size() : 0; }

  const Json& operator[](const std::string& key) const {
    if (t_ == Object) for (const auto& kv : o_) if (kv.first == key) return kv.second;
    return null_json();
  }
  const Json& operator[](size_t i) const { return (t_ == Array && i < a_.size()) ? a_[i] : null_json(); }
  bool has(const std::string& key) const {
    if (t_ == Object) for (const auto& kv : o_) if (kv.first == key) return true;
    return false;
  }
  // true when the field exists and is neither null nor false/0/"" (JavaScript truthiness)
  bool truthy() const {
    switch (t_) {
      case Null: return false;
      case Bool: return b_;
      case Num: return n_ != 0 && !std::isnan(n_);
      case Str: return !s_.empty();
      default: return true;
    }
  }

  // ---- building
  Json& push(Json v) { if (t_ != Array) { t_ = Array; a_.clear(); } a_.push_back(std::move(v)); return *this; }
  Json& set(const std::string& key, Json v) {
    if (t_ != Object) { t_ = Object; o_.clear(); }
    for (auto& kv : o_) if (kv.first == key) { kv.second = std::move(v); return *this; }
    o_.emplace_back(key, std::move(v));
    return *this;
  }
  Json* find(const std::string& key) {
    if (t_ == Object) for (auto& kv : o_) if (kv.first == key) return &kv.second;
    return nullptr;
  }
  Arr& arrMut() { if (t_ != Array) { t_ = Array; a_.clear(); } return a_; }
  Obj& objMut() { if (t_ != Object) { t_ = Object; o_.clear(); } return o_; }

  std::string dump() const { std::string out; dumpTo(out); return out; }
  static Json parse(const std::string& text);

 private:
  Type t_ = Null;
  bool b_ = false;
  double n_ = 0;
  std::string s_;
  Arr a_;
  Obj o_;

  static const Json& null_json() { static const Json j; return j; }
  static const std::string& empty_str() { static const std::string s; return s; }
  static const Arr& empty_arr() { static const Arr a; return a; }
  static const Obj& empty_obj() { static const Obj o; return o; }

  static void dumpString(std::string& out, const std::string& s) {
    out += '"';
    for (unsigned char c : s) {
      switch (c) {
        case '"': out += "\\\""; break;
        case '\\': out += "\\\\"; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        case '\t': out += "\\t"; break;
        case '\b': out += "\\b"; break;
        case '\f': out += "\\f"; break;
        default:
          if (c < 0x20) { static const char* hex = "0123456789abcdef"; out += "\\u00"; out += hex[c >> 4]; out += hex[c & 15]; }
          else out += static_cast<char>(c);
      }
    }
    out += '"';
  }
  void dumpTo(std::string& out) const {
    switch (t_) {
      case Null: out += "null"; break;
      case Bool: out += b_ ? "true" : "false"; break;
      case Num: out += std::isfinite(n_) ? jsnum(n_) : std::string("null"); break;
      case Str: dumpString(out, s_); break;
      case Array: {
        out += '[';
        for (size_t i = 0; i < a_.size(); ++i) { if (i) out += ','; a_[i].dumpTo(out); }
        out += ']';
        break;
      }
      case Object: {
        out += '{';
        for (size_t i = 0; i < o_.size(); ++i) { if (i) out += ','; dumpString(out, o_[i].first); out += ':'; o_[i].second.dumpTo(out); }
        out += '}';
        break;
      }
    }
  }
  friend class JsonParser;
};

// ---------------------------------------------------------------- parser
class JsonParser {
 public:
  explicit JsonParser(const std::string& s) : s_(s) {}
  Json run() {
    skip();
    Json v = value(0);
    skip();
    if (i_ != s_.size()) fail("unexpected trailing characters");
    return v;
  }

 private:
  const std::string& s_;
  size_t i_ = 0;

  [[noreturn]] void fail(const char* msg) const {
    throw std::runtime_error(std::string("json: ") + msg + " at byte " + std::to_string(i_));
  }
  void skip() { while (i_ < s_.size() && (s_[i_] == ' ' || s_[i_] == '\t' || s_[i_] == '\n' || s_[i_] == '\r')) ++i_; }
  bool lit(const char* w) {
    size_t n = 0; while (w[n]) ++n;
    if (s_.compare(i_, n, w) == 0) { i_ += n; return true; }
    return false;
  }
  Json value(int depth) {
    if (depth > 200) fail("nesting too deep");
    if (i_ >= s_.size()) fail("unexpected end");
    char c = s_[i_];
    if (c == '{') return object(depth);
    if (c == '[') return array(depth);
    if (c == '"') return Json(string());
    if (c == 't') { if (lit("true")) return Json(true); fail("bad literal"); }
    if (c == 'f') { if (lit("false")) return Json(false); fail("bad literal"); }
    if (c == 'n') { if (lit("null")) return Json(); fail("bad literal"); }
    return number();
  }
  Json number() {
    size_t st = i_;
    if (i_ < s_.size() && (s_[i_] == '-' || s_[i_] == '+')) ++i_;
    while (i_ < s_.size() && ((s_[i_] >= '0' && s_[i_] <= '9') || s_[i_] == '.' || s_[i_] == 'e' || s_[i_] == 'E' || s_[i_] == '-' || s_[i_] == '+')) ++i_;
    if (i_ == st) fail("unexpected character");
    return Json(parse_double(s_.substr(st, i_ - st)));
  }
  static int hexv(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
  }
  uint32_t hex4() {
    if (i_ + 4 > s_.size()) fail("bad \\u escape");
    uint32_t v = 0;
    for (int k = 0; k < 4; ++k) { int h = hexv(s_[i_ + k]); if (h < 0) fail("bad \\u escape"); v = v * 16 + static_cast<uint32_t>(h); }
    i_ += 4;
    return v;
  }
  static void put(std::string& out, uint32_t cp) {
    if (cp < 0x80) out += static_cast<char>(cp);
    else if (cp < 0x800) { out += static_cast<char>(0xC0 | (cp >> 6)); out += static_cast<char>(0x80 | (cp & 0x3F)); }
    else if (cp < 0x10000) { out += static_cast<char>(0xE0 | (cp >> 12)); out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F)); out += static_cast<char>(0x80 | (cp & 0x3F)); }
    else { out += static_cast<char>(0xF0 | (cp >> 18)); out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F)); out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F)); out += static_cast<char>(0x80 | (cp & 0x3F)); }
  }
  std::string string() {
    ++i_;  // opening quote
    std::string out;
    while (true) {
      if (i_ >= s_.size()) fail("unterminated string");
      char c = s_[i_++];
      if (c == '"') break;
      if (c != '\\') { out += c; continue; }
      if (i_ >= s_.size()) fail("bad escape");
      char e = s_[i_++];
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
          uint32_t cp = hex4();
          if (cp >= 0xD800 && cp < 0xDC00 && i_ + 1 < s_.size() && s_[i_] == '\\' && s_[i_ + 1] == 'u') {
            size_t save = i_; i_ += 2;
            uint32_t lo = hex4();
            if (lo >= 0xDC00 && lo < 0xE000) cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
            else i_ = save;
          }
          put(out, cp);
          break;
        }
        default: fail("bad escape");
      }
    }
    return out;
  }
  Json array(int depth) {
    ++i_;
    Json a = Json::array();
    skip();
    if (i_ < s_.size() && s_[i_] == ']') { ++i_; return a; }
    while (true) {
      skip();
      a.arrMut().push_back(value(depth + 1));
      skip();
      if (i_ >= s_.size()) fail("unterminated array");
      if (s_[i_] == ',') { ++i_; continue; }
      if (s_[i_] == ']') { ++i_; break; }
      fail("expected , or ]");
    }
    return a;
  }
  Json object(int depth) {
    ++i_;
    Json o = Json::object();
    skip();
    if (i_ < s_.size() && s_[i_] == '}') { ++i_; return o; }
    while (true) {
      skip();
      if (i_ >= s_.size() || s_[i_] != '"') fail("expected a key");
      std::string k = string();
      skip();
      if (i_ >= s_.size() || s_[i_] != ':') fail("expected :");
      ++i_;
      skip();
      o.set(k, value(depth + 1));
      skip();
      if (i_ >= s_.size()) fail("unterminated object");
      if (s_[i_] == ',') { ++i_; continue; }
      if (s_[i_] == '}') { ++i_; break; }
      fail("expected , or }");
    }
    return o;
  }
};

inline Json Json::parse(const std::string& text) { return JsonParser(text).run(); }

}  // namespace saem
