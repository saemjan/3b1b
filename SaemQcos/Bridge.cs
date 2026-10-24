// SaemLabs.Qcos.Bridge — the C# layer of the c/c++/c#/python architecture.
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

        public SaemBridge(string cliPath = null)
        {
            cliPath ??= Path.Combine(FindRoot(), "build", "saem_cli");
            var psi = new ProcessStartInfo
            {
                FileName = cliPath,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            _proc = Process.Start(psi)
                ?? throw new InvalidOperationException("cannot start saem_cli");
            _in = _proc.StandardInput;
            _out = _proc.StandardOutput;
        }

        private static string FindRoot()
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir != null && !Directory.Exists(Path.Combine(dir.FullName, "core")))
                dir = dir.Parent;
            return dir?.FullName ?? Directory.GetCurrentDirectory();
        }

        /// <summary>One door call. Throws on ok:false.</summary>
        public JsonElement Call(string method, string argsJson = "{}")
        {
            _id += 1;
            
            // FIXED: Properly dispose of the JsonDocument to prevent memory leaks in the factory
            JsonElement argsElement;
            using (var doc = JsonDocument.Parse(argsJson))
            {
                argsElement = doc.RootElement.Clone();
            }

            var req = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["id"] = _id,
                ["method"] = method,
                ["args"] = argsElement
            });
            
            _in.WriteLine(req);
            _in.Flush();
            
            var line = _out.ReadLine();
            if (line == null) throw new EndOfStreamException("core closed the door");
            
            using var resDoc = JsonDocument.Parse(line);
            var root = resDoc.RootElement;
            
            if (root.GetProperty("id").GetInt32() != _id)
                throw new InvalidOperationException("core answered a different question");
            if (!root.GetProperty("ok").GetBoolean())
                throw new InvalidOperationException(root.GetProperty("error").GetString());
                
            return root.GetProperty("result").Clone();
        }

        public JsonElement Boot() => Call("qcos.boot");
        
        public JsonElement Gate(string op, string argsJson = "{}")
        {
            var argsObj = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["op"] = op,
                ["args"] = JsonDocument.Parse(argsJson).RootElement.Clone()
            });
            return Call("qcos.gate", argsObj);
        }

        public JsonElement Latch(string key, string valueJson)
        {
            var argsObj = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["key"] = key,
                ["value"] = JsonDocument.Parse(valueJson).RootElement.Clone()
            });
            return Call("qcos.latch", argsObj);
        }

        public JsonElement Read(string key) =>
            Call("qcos.read", JsonSerializer.Serialize(
                new Dictionary<string, object> { ["key"] = key }));
                
        public JsonElement Lower(string intentJson) => Call("qcos.lower", intentJson);
        
        public JsonElement Exec(string cirJson)
        {
            var argsObj = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["cir"] = JsonDocument.Parse(cirJson).RootElement.Clone()
            });
            return Call("qcos.exec", argsObj);
        }

        public JsonElement Snapshot() => Call("qcos.snapshot");
        public JsonElement Provenance() => Call("qcos.provenance");

        public void Dispose()
        {
            try
            {
                _in.Close();
                if (!_proc.WaitForExit(10000)) _proc.Kill();
            }
            catch { /* the door is already closed */ }
            _proc.Dispose();
        }
    }
}
