// SaemLabs.Qcos.Bridge — the C# layer of the C/C++/C#/Python architecture.
//
// Speaks the same line protocol as saem/core.py and saem_cli:
// one JSON request per line, one JSON answer per line.
//
// The C++ core is the single source of truth. C# is a typed client,
// never a second kernel.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

namespace SaemLabs.Qcos
{
    public sealed class SaemBridge : IDisposable
    {
        private readonly Process _proc;
        private readonly StreamWriter _in;
        private readonly StreamReader _out;
        private int _id;

        public SaemBridge(string? cliPath = null)
        {
            var resolvedCli = ResolveCliPath(cliPath);

            var psi = new ProcessStartInfo
            {
                FileName = resolvedCli,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            _proc = Process.Start(psi)
                ?? throw new InvalidOperationException($"cannot start saem_cli at {resolvedCli}");

            _in = _proc.StandardInput;
            _out = _proc.StandardOutput;
            _in.NewLine = "\n";
        }

        private static bool IsWindows()
        {
            return Path.DirectorySeparatorChar == '\\';
        }

        private static string FindRoot()
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);

            while (dir != null && !Directory.Exists(Path.Combine(dir.FullName, "core")))
            {
                dir = dir.Parent;
            }

            return dir?.FullName ?? Directory.GetCurrentDirectory();
        }

        private static string ResolveCliPath(string? cliPath)
        {
            if (!string.IsNullOrWhiteSpace(cliPath))
            {
                if (File.Exists(cliPath))
                    return cliPath;

                if (IsWindows() && File.Exists(cliPath + ".exe"))
                    return cliPath + ".exe";

                throw new FileNotFoundException($"saem_cli not found at {cliPath}");
            }

            var root = FindRoot();
            var candidates = new List<string>
            {
                Path.Combine(root, "build", "saem_cli"),
                Path.Combine(root, "build", "saem_cli.exe"),
            };

            foreach (var c in candidates)
            {
                if (File.Exists(c))
                    return c;
            }

            throw new FileNotFoundException(
                "saem_cli not found. Run: python3 tools/build.py cli"
            );
        }

        private static string FindPython()
        {
            var fromEnv = Environment.GetEnvironmentVariable("SAEM_PYTHON");
            if (!string.IsNullOrWhiteSpace(fromEnv))
                return fromEnv;

            string[] names = IsWindows()
                ? new[] { "python", "py", "python3" }
                : new[] { "python3", "python" };

            foreach (var name in names)
            {
                foreach (var dir in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator))
                {
                    if (string.IsNullOrWhiteSpace(dir))
                        continue;

                    try
                    {
                        var candidate = Path.Combine(dir, name);
                        if (File.Exists(candidate))
                            return candidate;

                        if (IsWindows())
                        {
                            var candidateExe = candidate + ".exe";
                            if (File.Exists(candidateExe))
                                return candidateExe;
                        }
                    }
                    catch
                    {
                        // Ignore malformed PATH entries.
                    }
                }
            }

            throw new FileNotFoundException("python3/python not found; set SAEM_PYTHON");
        }

        /// <summary>
        /// One door call. Throws on ok:false.
        /// </summary>
        public JsonElement Call(string method, string argsJson = "{}")
        {
            _id += 1;

            using var argsDoc = JsonDocument.Parse(argsJson);

            var request = new Dictionary<string, object>
            {
                ["id"] = _id,
                ["method"] = method,
                ["args"] = argsDoc.RootElement
            };

            var req = JsonSerializer.Serialize(request);

            _in.WriteLine(req);
            _in.Flush();

            var line = _out.ReadLine();
            if (line == null)
                throw new EndOfStreamException("core closed the door");

            using var doc = JsonDocument.Parse(line);
            var root = doc.RootElement;

            if (root.TryGetProperty("id", out var idProp))
            {
                if (idProp.GetInt32() != _id)
                    throw new InvalidOperationException("core answered a different question");
            }

            if (!root.GetProperty("ok").GetBoolean())
            {
                var err = root.TryGetProperty("error", out var e)
                    ? e.GetString() ?? "unknown error"
                    : "unknown error";

                throw new InvalidOperationException(err);
            }

            return root.GetProperty("result").Clone();
        }

        public JsonElement Boot() => Call("qcos.boot");

        public JsonElement Gate(string op, string argsJson = "{}")
        {
            using var doc = JsonDocument.Parse(argsJson);

            var args = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["op"] = op,
                ["args"] = doc.RootElement
            });

            return Call("qcos.gate", args);
        }

        public JsonElement Latch(string key, string valueJson)
        {
            using var doc = JsonDocument.Parse(valueJson);

            var args = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["key"] = key,
                ["value"] = doc.RootElement
            });

            return Call("qcos.latch", args);
        }

        public JsonElement Read(string key)
        {
            var args = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["key"] = key
            });

            return Call("qcos.read", args);
        }

        public JsonElement Lower(string intentJson)
        {
            return Call("qcos.lower", intentJson);
        }

        public JsonElement Exec(string cirJson)
        {
            using var doc = JsonDocument.Parse(cirJson);

            var args = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["cir"] = doc.RootElement
            });

            return Call("qcos.exec", args);
        }

        public JsonElement Snapshot() => Call("qcos.snapshot");

        public JsonElement Provenance() => Call("qcos.provenance");

        /// <summary>
        /// Level-0 check: the binary's body vs the tree's body.
        /// </summary>
        public static string BodyId(string? cliPath = null)
        {
            var resolved = ResolveCliPath(cliPath);

            var psi = new ProcessStartInfo
            {
                FileName = resolved,
                Arguments = "--source-id",
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var p = Process.Start(psi)
                ?? throw new InvalidOperationException($"cannot start {resolved}");

            return p.StandardOutput.ReadToEnd().Trim();
        }

        public static string TreeId()
        {
            var python = FindPython();

            var psi = new ProcessStartInfo
            {
                FileName = python,
                Arguments = "tools/build.py id",
                WorkingDirectory = FindRoot(),
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var p = Process.Start(psi)
                ?? throw new InvalidOperationException("cannot start python for tree id");

            return p.StandardOutput.ReadToEnd().Trim();
        }

        public void Dispose()
        {
            try
            {
                _in.Close();
                if (!_proc.WaitForExit(10000))
                {
                    _proc.Kill();
                }
            }
            catch
            {
                // The door is already closed.
            }

            _proc.Dispose();
        }
    }
}
