// Small helpers shared by every part of the Saem core.
// The goal is JavaScript-exact behaviour where the reference
// engine relies on it: string whitespace, UTF-16 lengths,
// the seeded random stream, the 32-bit hash, Math.round,
// and Map iteration order.
#pragma once
#include <sstream>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "numfmt.hpp"

namespace saem {

using u32 = std::u32string;

// ---------- UTF-8 <-> UTF-32 ----------
inline u32 to_u32(const std::string& s) {
    u32 out;
    out.reserve(s.size());
    const size_t n = s.size();
    size_t i = 0;
    while (i < n) {
        const unsigned char c = static_cast<unsigned char>(s[i]);
        char32_t cp = 0;
        size_t len = 0;
        if (c < 0x80) { cp = c; len = 1; }
        else if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; len = 2; }
        else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; len = 3; }
        else if ((c & 0xF8) == 0xF0) { cp = c & 0x07; len = 4; }
        else { out.push_back(0xFFFD); ++i; continue; }
        if (i + len > n) { out.push_back(0xFFFD); ++i; continue; }
        bool ok = true;
        for (size_t k = 1; k < len; ++k) {
            const unsigned char d = static_cast<unsigned char>(s[i + k]);
            if ((d & 0xC0) != 0x80) { ok = false; break; }
            cp = (cp << 6) | (d & 0x3F);
        }
        if (!ok || (len == 2 && cp < 0x80) ||
            (len == 3 && cp < 0x800) ||
            (len == 4 && cp < 0x10000) || cp > 0x10FFFF ||
            (cp >= 0xD800 && cp <= 0xDFFF)) {
            out.push_back(0xFFFD); ++i; continue;
        }
        out.push_back(cp);
        i += len;
    }
    return out;
}

inline void put_u8(std::string& out, char32_t cp) {
    if (cp < 0x80) out += static_cast<char>(cp);
    else if (cp < 0x800) {
        out += static_cast<char>(0xC0 | (cp >> 6));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    }
    else if (cp < 0x10000) {
        out += static_cast<char>(0xE0 | (cp >> 12));
        out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    }
    else {
        out += static_cast<char>(0xF0 | (cp >> 18));
        out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
        out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    }
}

inline std::string to_u8(const u32& s) {
    std::string out;
    out.reserve(s.size());
    for (char32_t c : s) put_u8(out, c);
    return out;
}

inline u32 U(const char* ascii_or_utf8) { return to_u32(ascii_or_utf8); }

// ---------- JavaScript character classes ----------
// \s and String.prototype.trim: white space plus line terminators.
inline bool js_space(char32_t c) {
    switch (c) {
        case 9: case 10: case 11: case 12: case 13: case 32:
        case 0xA0: case 0x1680: case 0x2028: case 0x2029:
        case 0x202F: case 0x205F: case 0x3000: case 0xFEFF:
            return true;
        default:
            return c >= 0x2000 && c <= 0x200A;
    }
}

inline bool js_lineterm(char32_t c) {
    return c == 10 || c == 13 || c == 0x2028 || c == 0x2029;
}

inline bool is_digit(char32_t c) { return c >= '0' && c <= '9'; }

// ---------- trim / split (your existing functions) ----------
inline std::string trim(const std::string& s) {
    auto b = s.find_first_not_of(" \t\n\r");
    auto e = s.find_last_not_of(" \t\n\r");
    return (b == std::string::npos) ? "" : s.substr(b, e - b + 1);
}

inline std::vector<std::string> split(const std::string& s, char delim) {
    std::vector<std::string> out; std::stringstream ss(s); std::string item;
    while (std::getline(ss, item, delim)) out.push_back(item);
    return out;
}

}  // namespace saem
