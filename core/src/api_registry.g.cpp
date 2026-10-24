const Registrar R_gen_questionWith("gen.questionWith", [](const Json& a) -> Json {
  require_str(a, "id");
  require_obj(a, "params");
  const uint64_t seed = seed_of(a, 1);   // canon default
  return gen::question_json(gen::question_with(a["id"].asStr(), seed, a["params"]));
});
