// SaemLabs.Qcos.Bridge — the C# layer of the c/c++/c#/python architecture.
// Corrected: full JsonDocument disposal, read timeout, robust process handling.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace SaemLabs.Qcos
{
    public sealed class SaemBridge : IDisposable
    {
        private readonly Process _proc;
        private readonly StreamWriter _in;
        private readonly StreamReader _out;
        private int _id;
        private readonly object _gate = new object();
        private bool _disposed;

        // Default timeout for a single call (ms). Increase for heavy quantum / grow ops.
        public int CallTimeoutMs { get; set; } = 30_000;

        public SaemBridge(string cliPath = null)
        {
            cliPath ??= Path.Combine(FindRoot(), "build", "saem_cli");
            if (!File.Exists(cliPath) && !cliPath.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
            {
                // Windows convenience
                var exe = cliPath + ".exe";
                if (File.Exists(exe)) cliPath = exe;
            }

            var psi = new ProcessStartInfo
            {
                FileName = cliPath,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                StandardOutputEncoding = System.Text.Encoding.UTF8,
                StandardInputEncoding = System.Text.Encoding.UTF8
            };

            _proc = Process.Start(psi)
                ?? throw new InvalidOperationException($"cannot start saem_cli at '{cliPath}'");

            _in  = _proc.StandardInput;
            _out = _proc.StandardOutput;
        }

        private static string FindRoot()
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir != null)
            {
                if (Directory.Exists(Path.Combine(dir.FullName, "core")))
                    return dir.FullName;
                dir = dir.Parent;
            }
            return Directory.GetCurrentDirectory();
        }

        /// **Summary:**
One door call. Throws on ok:false or timeout.
        public JsonElement Call(string method, string argsJson = "{}")
        {
            if (_disposed) throw new ObjectDisposedException(nameof(SaemBridge));

            lock (_gate)
            {
                _id += 1;
                int thisId = _id;

                // Properly dispose the temporary document
                JsonElement argsElement;
                using (var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(argsJson) ? "{}" : argsJson))
                {
                    argsElement = doc.RootElement.Clone();
                }

                var req = JsonSerializer.Serialize(new Dictionary<string, object>
                {
                    ["id"]     = thisId,
                    ["method"] = method,
                    ["args"]   = argsElement
                });

                _in.WriteLine(req);
                _in.Flush();

                // Read with timeout so the bridge never hangs forever
                string line = null;
                var readTask = Task.Run(() => _out.ReadLine());
                if (readTask.Wait(CallTimeoutMs))
                    line = readTask.Result;
                else
                    throw new TimeoutException($"saem_cli did not answer within {CallTimeoutMs} ms (method={method})");

                if (line == null)
                    throw new EndOfStreamException("core closed the door");

                using var resDoc = JsonDocument.Parse(line);
                var root = resDoc.RootElement;

                if (!root.TryGetProperty("id", out var idProp) || idProp.GetInt32() != thisId)
                    throw new InvalidOperationException("core answered a different question");

                if (!root.TryGetProperty("ok", out var okProp) || !okProp.GetBoolean())
                {
                    string err = root.TryGetProperty("error", out var e) ? e.GetString() : "unknown error";
                    throw new InvalidOperationException(err ?? "ok:false");
                }

                return root.GetProperty("result").Clone();
            }
        }

        public JsonElement Boot() => Call("qcos.boot");

        public JsonElement Gate(string op, string argsJson = "{}")
        {
            using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(argsJson) ? "{}" : argsJson);
            var argsObj = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["op"]   = op,
                ["args"] = doc.RootElement.Clone()
            });
            return Call("qcos.gate", argsObj);
        }

        public JsonElement Latch(string key, string valueJson)
        {
            using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(valueJson) ? "null" : valueJson);
            var argsObj = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["key"]   = key,
                ["value"] = doc.RootElement.Clone()
            });
            return Call("qcos.latch", argsObj);
        }

        public JsonElement Read(string key) =>
            Call("qcos.read", JsonSerializer.Serialize(
                new Dictionary<string, object> { ["key"] = key }));

        public JsonElement Lower(string intentJson) => Call("qcos.lower", intentJson);

        public JsonElement Exec(string cirJson)
        {
            using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(cirJson) ? "{}" : cirJson);
            var argsObj = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["cir"] = doc.RootElement.Clone()
            });
            return Call("qcos.exec", argsObj);
        }

        public JsonElement Snapshot()    => Call("qcos.snapshot");
        public JsonElement Provenance()  => Call("qcos.provenance");

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;
            try
            {
                _in?.Close();
                if (!_proc.HasExited)
                {
                    if (!_proc.WaitForExit(5_000))
                        _proc.Kill(entireProcessTree: true);
                }
            }
            catch
            {
                /* the door is already closed */
            }
            finally
            {
                _proc?.Dispose();
            }
        }
    }
}
