// tests/test_arena.cpp — Step 11a witness suite. Exit 0 = truth holds.
#include "../core/src/arena.hpp"
#include <csetjmp>
#include <cstdio>

static std::jmp_buf jb;
static const char *g_why = nullptr;
static void capture(const char *w) { g_why = w; std::longjmp(jb, 1); }

static int fails = 0, total = 0;
static void want(const char *name, bool ok, const char *detail = "") {
    ++total;
    if (!ok) ++fails;
    std::printf("[test_arena] %-34s %s %s\n", name, ok ? "ok" : "DRIFT", detail);
}
static bool panics(void (*fn)(void *)) {                 // panic-path probe
    static void *arg; arg = nullptr; (void)arg;
    if (setjmp(jb) == 0) { fn(nullptr); return false; }
    return true;
}
static void dbl_free(void *) { qcos::w_free(qcos::g_arena, 0, 7); qcos::w_free(qcos::g_arena, 0, 7); }
static void oob_free(void *) { qcos::w_free(qcos::g_arena, 99, 7); }
static void underflow(void *) { qcos::w_alloc(qcos::g_arena, 7); qcos::ref_dec(qcos::g_arena, 0); }
static void dbl_lock(void *) { qcos::Lock l{}; qcos::lock_acquire(l, 1); qcos::lock_acquire(l, 2); }
static void bad_rel(void *)  { qcos::Lock l{}; qcos::lock_acquire(l, 1); qcos::lock_release(l, 2); }

int main() {
    qcos::g_panic = capture;
    qcos::Arena &a = qcos::g_arena;
    a.init();
    want("init junk = 0x01", a.w[0].payload[0] == QCOS_JUNK_FREE && !a.w[0].valid);

    uint32_t ids[32];
    for (int i = 0; i < 32; i++) ids[i] = qcos::w_alloc(a, 1);
    bool distinct = true;
    for (int i = 0; i < 32; i++) for (int j = i + 1; j < 32; j++) if (ids[i] == ids[j]) distinct = false;
    want("32 allocs, distinct ids", distinct && a.w_occ == 0xFFFFFFFFu);

    want("33rd alloc refused", qcos::w_alloc(a, 1) == QCOS_SLOT_NONE && a.debt_refusals == 1);

    uint32_t old = ids[0];
    qcos::w_free(a, ids[0], 1);
    want("free junk = 0x01", a.w[ids[0]].payload[0] == QCOS_JUNK_FREE);
    uint32_t nu = qcos::w_alloc(a, 1);
    want("identity never reused", nu != old && a.w[nu].payload[0] == QCOS_JUNK_ALLOC);

    g_why = nullptr; want("double free panics", panics(dbl_free) && g_why != nullptr);
    g_why = nullptr; want("oob free panics", panics(oob_free) && g_why != nullptr);
    qcos::w_free(a, nu, 1);
    want("get on freed = nullptr", qcos::w_get(a, nu) == nullptr);

    uint64_t bits0 = a.bits_erased;
    uint32_t e0 = qcos::e_push(a, 1);
    for (int i = 0; i < 63; i++) qcos::e_push(a, 1);
    uint32_t e64 = qcos::e_push(a, 1);                       // evicts oldest (refcount 0)
    want("epi eviction FIFO", e64 != QCOS_SLOT_NONE && a.e_tail == 1
         && a.bits_erased - bits0 == 8ull * QCOS_SLOT_PAYLOAD);
    (void)e0;
    for (uint32_t i = 0; i < QCOS_EPISODIC_LIMIT; i++) if (qcos::e_get(a, i)) qcos::ref_inc(a, i);
    want("all-referenced refuse", qcos::e_push(a, 1) == QCOS_SLOT_NONE);
    for (uint32_t i = 0; i < QCOS_EPISODIC_LIMIT; i++) if (qcos::e_get(a, i)) qcos::ref_dec(a, i);

    g_why = nullptr; want("refcount underflow panics", panics(underflow) && g_why != nullptr);
    g_why = nullptr; want("double acquire panics", panics(dbl_lock) && g_why != nullptr);
    g_why = nullptr; want("non-owner release panics", panics(bad_rel) && g_why != nullptr);

    qcos::Arena b1, b2; b1.init(); b2.init();
    for (int i = 0; i < 5; i++) { qcos::w_alloc(b1, 3); qcos::w_alloc(b2, 3); }
    qcos::w_free(b1, 2, 3); qcos::w_free(b2, 2, 3);
    want("determinism (replay equal", b1.next_id == b2.next_id && b1.w_occ == b2.w_occ
         && b1.prov[0].identity == b2.prov[0].identity);
    want("prov ring ordered", a.prov[0].op == qcos::OP_ALLOC && a.prov[1].op == qcos::OP_ALLOC);

    std::printf("[test_arena] %d/%d passed\n", total - fails, total);
    return fails ? 1 : 0;
}
