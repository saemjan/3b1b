# Third-party notice: Open Math Harness

Parts of `core/src/nx/`, `core/include/` and `interop/` are adapted from Open Math Harness
(https://github.com/openmathmodel/open-math-harness), licensed under the Apache License, Version 2.0.
The full licence text is in `third_party/open-math-harness-src/LICENSE`.

What changed: the ideas, mechanisms and test cases were rewritten from Rust into C++17 (plus C and C# boundary code),
simplified to fit a deterministic, dependency-free core with no global state. Anything that depends on a language model,
a network, Linux sandboxing or a model provider was left out. Each adapted file names the original files it came from.
