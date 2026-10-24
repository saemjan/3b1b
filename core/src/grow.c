/* grow.c — the growth substrate in plain C11 (corrected).
   Learning  = append-only case store (Bernoulli: expectation from cases).
   Writing   = distillation of witnessed cases into a QUARANTINED C++ file.
   Reading   = recall of the newest witnessed case for a canonical key.
   Nothing here executes grown code. Witnesses and humans promote it.

   Case line (TSV, escaped): seq \t method \t key \t args \t out \t witness \t hash
   hash = sha256(prev_hash + 0x1f + line_without_hash); chain starts at 64 '0'.
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- SHA-256 (same canon as core/src/sha256.hpp) ---- */
static const uint32_t SK[64] = {
    0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
    0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
    0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
    0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
    0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
    0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
    0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
    0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u};

static uint32_t rr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }

void saem_sha256(const char* data, size_t len, char out[65]) {
    size_t pad = ((len + 8) / 64 + 1) * 64;
    unsigned char* m = (unsigned char*)calloc(pad, 1);
    if (!m) {
        memset(out, '0', 64);
        out[64] = 0;
        return;
    }
    memcpy(m, data, len);
    m[len] = 0x80;
    uint64_t bits = (uint64_t)len * 8;
    for (int i = 0; i < 8; ++i)
        m[pad - 1 - i] = (unsigned char)(bits >> (8 * i));

    uint32_t h[8] = {
        0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,
        0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u
    };

    for (size_t off = 0; off < pad; off += 64) {
        uint32_t w[64];
        for (int i = 0; i < 16; ++i)
            w[i] = ((uint32_t)m[off + i*4] << 24) | ((uint32_t)m[off + i*4 + 1] << 16) |
                   ((uint32_t)m[off + i*4 + 2] << 8)  | (uint32_t)m[off + i*4 + 3];
        for (int i = 16; i < 64; ++i) {
            uint32_t s0 = rr(w[i-15], 7) ^ rr(w[i-15], 18) ^ (w[i-15] >> 3);
            uint32_t s1 = rr(w[i-2], 17) ^ rr(w[i-2], 19)  ^ (w[i-2] >> 10);
            w[i] = w[i-16] + s0 + w[i-7] + s1;
        }
        uint32_t a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],hh=h[7];
        for (int i = 0; i < 64; ++i) {
            uint32_t S1 = rr(e,6)^rr(e,11)^rr(e,25);
            uint32_t ch = (e&f)^(\~e&g);
            uint32_t t1 = hh + S1 + ch + SK[i] + w[i];
            uint32_t S0 = rr(a,2)^rr(a,13)^rr(a,22);
            uint32_t mj = (a&b)^(a&c)^(b&c);
            uint32_t t2 = S0 + mj;
            hh=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
        }
        h[0]+=a; h[1]+=b; h[2]+=c; h[3]+=d;
        h[4]+=e; h[5]+=f; h[6]+=g; h[7]+=hh;
    }

    static const char* hx = "0123456789abcdef";
    for (int i = 0; i < 8; ++i)
        for (int s = 28; s >= 0; s -= 4)
            out[i*8 + (28-s)/4] = hx[(h[i] >> s) & 0xF];
    out[64] = 0;
    free(m);
}

/* ---- escaping for the TSV store ---- */
static int esc(const char* s, char* buf, size_t cap) {
    size_t j = 0;
    for (size_t i = 0; s && s[i] && j + 3 < cap; ++i) {
        char c = s[i];
        if (c == '\\')      { buf[j++] = '\\'; buf[j++] = '\\'; }
        else if (c == '\t') { buf[j++] = '\\'; buf[j++] = 't';  }
        else if (c == '\n') { buf[j++] = '\\'; buf[j++] = 'n';  }
        else if (c == '\r') { buf[j++] = '\\'; buf[j++] = 'r';  }
        else                { buf[j++] = c; }
    }
    if (j >= cap) return -1;
    buf[j] = 0;
    return 0;
}

static void unesc(const char* s, char* buf, size_t cap) {
    size_t j = 0;
    for (size_t i = 0; s && s[i] && j + 1 < cap; ++i) {
        if (s[i] == '\\' && s[i+1]) {
            char n = s[++i];
            buf[j++] = (n=='t') ? '\t' : (n=='n') ? '\n' : (n=='r') ? '\r' : n;
        } else {
            buf[j++] = s[i];
        }
    }
    buf[j] = 0;
}

/* split a line into up to 7 fields on unescaped tabs; returns field count */
static int split7(char* line, char* f[7]) {
    int n = 0;
    f[n++] = line;
    for (char* p = line; *p && n < 7; ++p) {
        if (*p == '\\') { if (p[1]) ++p; continue; }
        if (*p == '\t') { *p = 0; f[n++] = p + 1; }
    }
    return n;
}

static void last_hash(const char* store, char prev[65]) {
    memset(prev, '0', 64);
    prev[64] = 0;
    FILE* fp = fopen(store, "rb");
    if (!fp) return;

    char* line = NULL;
    size_t len = 0;
    ssize_t nread;
    while ((nread = getline(&line, &len, fp)) != -1) {
        if (nread < 65) continue;
        /* last field is the 64-hex hash */
        char* h = strrchr(line, '\t');
        if (h && h[1]) {
            size_t i = 0;
            for (++h; i < 64 && h[i] && h[i] != '\n' && h[i] != '\r'; ++i)
                prev[i] = h[i];
            prev[i] = 0;
        }
    }
    free(line);
    fclose(fp);
}

int saem_learn(const char* store, const char* method, const char* key,
               const char* args, const char* out, const char* witness) {
    if (!store || !method || !key || !args || !out)
        return -1;

    char prev[65];
    last_hash(store, prev);

    /* count existing lines to get next seq */
    int seq = 0;
    FILE* fp = fopen(store, "rb");
    if (fp) {
        char* line = NULL;
        size_t len = 0;
        while (getline(&line, &len, fp) != -1) ++seq;
        free(line);
        fclose(fp);
    }
    ++seq;

    /* escape fields (dynamic, large enough for normal cases) */
    size_t ecap = 1 << 20;
    char* e0 = (char*)malloc(ecap);
    char* e1 = (char*)malloc(ecap);
    char* e2 = (char*)malloc(ecap);
    char* e3 = (char*)malloc(ecap);
    if (!e0 || !e1 || !e2 || !e3) {
        free(e0); free(e1); free(e2); free(e3);
        return -1;
    }
    if (esc(method, e0, ecap) || esc(key, e1, ecap) ||
        esc(args, e2, ecap)   || esc(out, e3, ecap)) {
        free(e0); free(e1); free(e2); free(e3);
        return -1;
    }

    size_t body_cap = ecap * 4 + 256;
    char* body = (char*)malloc(body_cap);
    char* payload = (char*)malloc(body_cap + 128);
    if (!body || !payload) {
        free(e0); free(e1); free(e2); free(e3);
        free(body); free(payload);
        return -1;
    }

    snprintf(body, body_cap, "%d\t%s\t%s\t%s\t%s\t%s",
             seq, e0, e1, e2, e3, witness ? witness : "");
    snprintf(payload, body_cap + 128, "%s\x1f%s", prev, body);

    char h[65];
    saem_sha256(payload, strlen(payload), h);

    fp = fopen(store, "ab");
    if (!fp) {
        free(e0); free(e1); free(e2); free(e3);
        free(body); free(payload);
        return -1;
    }
    fprintf(fp, "%s\t%s\n", body, h);
    fclose(fp);

    free(e0); free(e1); free(e2); free(e3);
    free(body); free(payload);
    return seq;
}

int saem_recall(const char* store, const char* method, const char* key,
                char* out, size_t cap) {
    if (!store || !method || !key || !out || cap < 2) return 0;

    FILE* fp = fopen(store, "rb");
    if (!fp) return 0;

    char* line = NULL;
    size_t len = 0;
    int found = 0;
    char* keep = (char*)malloc(1 << 20);
    if (!keep) { fclose(fp); return 0; }

    while (getline(&line, &len, fp) != -1) {
        char* tmp = strdup(line);
        if (!tmp) continue;
        char* f[7];
        if (split7(tmp, f) == 7 &&
            strcmp(f[1], method) == 0 &&
            strcmp(f[2], key) == 0) {
            unesc(f[4], keep, 1 << 20);
            found = 1;
        }
        free(tmp);
    }
    free(line);
    fclose(fp);

    if (found) {
        strncpy(out, keep, cap - 1);
        out[cap - 1] = 0;
    }
    free(keep);
    return found;
}

int saem_count(const char* store, const char* method) {
    if (!store || !method) return 0;
    FILE* fp = fopen(store, "rb");
    if (!fp) return 0;

    char* line = NULL;
    size_t len = 0;
    int n = 0;
    while (getline(&line, &len, fp) != -1) {
        char* tmp = strdup(line);
        if (!tmp) continue;
        char* f[7];
        if (split7(tmp, f) == 7 && strcmp(f[1], method) == 0) ++n;
        free(tmp);
    }
    free(line);
    fclose(fp);
    return n;
}

/* ---- writing: distill cases into a quarantined C++ method file ---- */
int saem_write_lib(const char* qdir, const char* name, const char* store, int min_cases) {
    if (!qdir || !name || !store || min_cases < 1) return -1;
    if (strstr(name, ")SAEM(")) return -2;   /* refuse dangerous names */

    FILE* fp = fopen(store, "rb");
    if (!fp) return -1;

    /* collect up to a reasonable number of cases */
    enum { MAX_CASES = 4096 };
    char** keys = (char**)calloc(MAX_CASES, sizeof(char*));
    char** outs = (char**)calloc(MAX_CASES, sizeof(char*));
    int*   seqs = (int*)calloc(MAX_CASES, sizeof(int));
    if (!keys || !outs || !seqs) {
        free(keys); free(outs); free(seqs);
        fclose(fp);
        return -1;
    }

    int n = 0;
    char* line = NULL;
    size_t len = 0;
    while (getline(&line, &len, fp) != -1 && n < MAX_CASES) {
        char* tmp = strdup(line);
        if (!tmp) continue;
        char* f[7];
        if (split7(tmp, f) == 7 && strcmp(f[1], name) == 0) {
            if (strstr(f[2], ")SAEM(") || strstr(f[4], ")SAEM(")) {
                free(tmp); free(line);
                for (int i = 0; i < n; ++i) { free(keys[i]); free(outs[i]); }
                free(keys); free(outs); free(seqs);
                fclose(fp);
                return -2;
            }
            seqs[n] = atoi(f[0]);
            keys[n] = (char*)malloc(1 << 20);
            outs[n] = (char*)malloc(1 << 20);
            if (!keys[n] || !outs[n]) {
                free(keys[n]); free(outs[n]);
                free(tmp); free(line);
                for (int i = 0; i < n; ++i) { free(keys[i]); free(outs[i]); }
                free(keys); free(outs); free(seqs);
                fclose(fp);
                return -1;
            }
            unesc(f[2], keys[n], 1 << 20);
            unesc(f[4], outs[n], 1 << 20);
            ++n;
        }
        free(tmp);
    }
    free(line);
    fclose(fp);

    if (n < min_cases) {
        for (int i = 0; i < n; ++i) { free(keys[i]); free(outs[i]); }
        free(keys); free(outs); free(seqs);
        return -3;   /* not enough cases: refuse to guess */
    }

    char path[512], mpath[512];
    snprintf(path,  sizeof path,  "%s/%s.cpp",      qdir, name);
    snprintf(mpath, sizeof mpath, "%s/%s.manifest", qdir, name);

    FILE* g = fopen(path, "wb");
    if (!g) {
        for (int i = 0; i < n; ++i) { free(keys[i]); free(outs[i]); }
        free(keys); free(outs); free(seqs);
        return -1;
    }

    /* unique delimiter derived from the name + case count to avoid collisions */
    char delim[32];
    snprintf(delim, sizeof delim, "SAEM%u", (unsigned)(n * 2654435761u));

    fprintf(g, "// grown/%s.cpp — distilled by saem_write_lib from %d witnessed cases.\n", name, n);
    fprintf(g, "// QUARANTINED: joins core/src only after tools/grow.py promote.\n");
    fprintf(g, "#include \"api.hpp\"\nnamespace saem { namespace {\n");
    fprintf(g, "const Registrar gr_%s(\"%s\", [](const Json& a) {\n", name, name);
    fprintf(g, "  const std::string k = canon(a);\n");

    for (int i = 0; i < n; ++i) {
        fprintf(g, "  if (k == R\"%s(%s)%s\") return Json::parse(R\"%s(%s)%s\");\n",
                delim, keys[i], delim, delim, outs[i], delim);
    }
    fprintf(g, "  throw std::runtime_error(\"ungrown input: not in witnessed table\");\n");
    fprintf(g, "});\n} }  // namespaces\n");
    fclose(g);

    /* body hash of the emitted file */
    FILE* r = fopen(path, "rb");
    if (!r) {
        for (int i = 0; i < n; ++i) { free(keys[i]); free(outs[i]); }
        free(keys); free(outs); free(seqs);
        return -1;
    }
    fseek(r, 0, SEEK_END);
    long fsz = ftell(r);
    fseek(r, 0, SEEK_SET);
    char* buf = (char*)malloc((size_t)fsz + 1);
    if (!buf) {
        fclose(r);
        for (int i = 0; i < n; ++i) { free(keys[i]); free(outs[i]); }
        free(keys); free(outs); free(seqs);
        return -1;
    }
    size_t got = fread(buf, 1, (size_t)fsz, r);
    fclose(r);
    buf[got] = 0;

    char h[65];
    saem_sha256(buf, got, h);
    free(buf);

    FILE* mf = fopen(mpath, "wb");
    if (!mf) {
        for (int i = 0; i < n; ++i) { free(keys[i]); free(outs[i]); }
        free(keys); free(outs); free(seqs);
        return -1;
    }
    fprintf(mf, "name=%s\nbody=%s\ncases=", name, h);
    for (int i = 0; i < n; ++i)
        fprintf(mf, "%d%s", seqs[i], i + 1 < n ? "," : "\n");
    fclose(mf);

    for (int i = 0; i < n; ++i) { free(keys[i]); free(outs[i]); }
    free(keys); free(outs); free(seqs);
    return 0;
}

int saem_read_lib(const char* qdir, const char* name, char hash_out[65]) {
    if (!qdir || !name || !hash_out) return 0;
    char mpath[512];
    snprintf(mpath, sizeof mpath, "%s/%s.manifest", qdir, name);
    FILE* fp = fopen(mpath, "rb");
    if (!fp) return 0;

    char line[256];
    int ok = 0;
    while (fgets(line, sizeof line, fp)) {
        if (strncmp(line, "body=", 5) == 0) {
            size_t i = 0;
            for (; i < 64 && line[5+i] && line[5+i] != '\n' && line[5+i] != '\r'; ++i)
                hash_out[i] = line[5+i];
            hash_out[i] = 0;
            ok = 1;
            break;
        }
    }
    fclose(fp);
    return ok;
}

#ifdef __cplusplus
}  /* extern "C" */
#endif
