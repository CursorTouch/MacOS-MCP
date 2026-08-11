//
// MCPStdioBridge.swift — zero-dependency stdio-to-HTTP bridge for MCP servers.
//
// Build:   swiftc -O -o mcp-stdio-bridge MCPStdioBridge.swift
//
// Design baseline: mootx01-ce apps/mootx01/rust/src/commands/proxy.rs

import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

// MARK: - Configuration

let defaultURL = "http://127.0.0.1:8765/mcp"
let defaultTimeout: TimeInterval = 3600
let defaultMaxConcurrent = 16
let maxLineBytes = 4 * 1024 * 1024

struct Config {
    var url: String
    var timeout: TimeInterval
    var maxConcurrent: Int
    var logFile: String?
}

func parseArgs() -> Config {
    var config = Config(url: defaultURL, timeout: defaultTimeout,
                        maxConcurrent: defaultMaxConcurrent, logFile: nil)
    let args = Array(CommandLine.arguments.dropFirst())
    var i = 0
    while i < args.count {
        switch args[i] {
        case "--url" where i + 1 < args.count:
            config.url = args[i + 1]; i += 2
        case "--timeout" where i + 1 < args.count:
            config.timeout = TimeInterval(args[i + 1]) ?? defaultTimeout; i += 2
        case "--max-concurrent" where i + 1 < args.count:
            config.maxConcurrent = Int(args[i + 1]) ?? defaultMaxConcurrent; i += 2
        case "--log-file" where i + 1 < args.count:
            config.logFile = args[i + 1]; i += 2
        case "-h", "--help":
            log("Usage: mcp-stdio-bridge [--url URL] [--timeout SECS] [--max-concurrent N] [--log-file PATH]")
            exit(0)
        default:
            log("unknown option: \(args[i])"); exit(1)
        }
    }
    return config
}

// MARK: - Logging (stderr + optional file, never stdout)

var logFileHandle: FileHandle?
let logLock = NSLock()

func setupLogFile(_ path: String) {
    FileManager.default.createFile(atPath: path, contents: nil)
    logFileHandle = FileHandle(forWritingAtPath: path)
    logFileHandle?.seekToEndOfFile()
}

func log(_ msg: String) {
    let ts = ISO8601DateFormatter().string(from: Date())
    let line = "[\(ts)] mcp-stdio-bridge[\(ProcessInfo.processInfo.processIdentifier)]: \(msg)\n"
    let data = Data(line.utf8)
    FileHandle.standardError.write(data)
    logLock.lock()
    logFileHandle?.write(data)
    logLock.unlock()
}

// MARK: - Session state (thread-safe)

let sessionLock = NSLock()
var sessionID: String?

func getSessionID() -> String? {
    sessionLock.lock(); defer { sessionLock.unlock() }
    return sessionID
}

func setSessionID(_ sid: String) {
    sessionLock.lock(); defer { sessionLock.unlock() }
    let old = sessionID
    sessionID = sid
    if old != sid {
        log("session: \(old ?? "nil") -> \(sid)")
    }
}

// MARK: - Stdout serialization

let stdoutLock = NSLock()

func writeFrame(_ data: Data) {
    stdoutLock.lock(); defer { stdoutLock.unlock() }
    var out = data
    out.append(0x0A)
    FileHandle.standardOutput.write(out)
}

// MARK: - SSE parsing

func extractSSEData(_ body: Data) -> [Data] {
    guard let text = String(data: body, encoding: .utf8) else { return [body] }
    var frames: [Data] = []
    for line in text.components(separatedBy: "\n") {
        let trimmed = line.trimmingCharacters(in: .whitespaces)
        if trimmed.hasPrefix("data: ") {
            let payload = String(trimmed.dropFirst(6))
            if !payload.isEmpty, let d = payload.data(using: .utf8) {
                frames.append(d)
            }
        }
    }
    return frames.isEmpty ? [body] : frames
}

// MARK: - JSON-RPC id and method extraction

func requestID(_ line: String) -> String? {
    guard let data = line.data(using: .utf8),
          let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let rawID = obj["id"] else { return nil }
    if rawID is NSNull { return nil }
    if let s = rawID as? String {
        if let encoded = try? JSONSerialization.data(withJSONObject: s) {
            return String(data: encoded, encoding: .utf8)
        }
        return nil
    }
    if let n = rawID as? NSNumber { return n.stringValue }
    return nil
}

func requestMethod(_ line: String) -> String? {
    guard let data = line.data(using: .utf8),
          let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let method = obj["method"] as? String else { return nil }
    return method
}

// MARK: - Frame forwarding

func forwardFrame(url: URL, timeout: TimeInterval, line: String,
                  session: URLSession) {
    guard let body = line.data(using: .utf8) else { return }

    let method = requestMethod(line) ?? "unknown"
    let rid = requestID(line) ?? "notification"
    log("-> \(method) id=\(rid)")

    var req = URLRequest(url: url)
    req.httpMethod = "POST"
    req.httpBody = body
    req.setValue("application/json", forHTTPHeaderField: "Content-Type")
    req.setValue("application/json, text/event-stream", forHTTPHeaderField: "Accept")
    req.timeoutInterval = timeout

    if let sid = getSessionID() {
        req.setValue(sid, forHTTPHeaderField: "Mcp-Session-Id")
    }

    let sem = DispatchSemaphore(value: 0)
    let start = Date()

    let task = session.dataTask(with: req) { data, response, error in
        defer { sem.signal() }
        let elapsed = Date().timeIntervalSince(start)

        if let error = error {
            log("<- \(method) id=\(rid) ERROR [\(String(format: "%.3f", elapsed))s]: \(error.localizedDescription)")
            if let rid = requestID(line) {
                let msg = error.localizedDescription
                    .replacingOccurrences(of: "\\", with: "\\\\")
                    .replacingOccurrences(of: "\"", with: "'")
                let errFrame = Data(
                    "{\"jsonrpc\":\"2.0\",\"id\":\(rid),\"error\":{\"code\":-32603,\"message\":\"bridge: \(msg)\"}}".utf8
                )
                writeFrame(errFrame)
            }
            return
        }

        let httpResp = response as? HTTPURLResponse
        let status = httpResp?.statusCode ?? 0

        if let newSID = httpResp?.value(forHTTPHeaderField: "Mcp-Session-Id") {
            setSessionID(newSID)
        }

        guard let data = data, !data.isEmpty, status != 202 else {
            log("<- \(method) id=\(rid) \(status) empty [\(String(format: "%.3f", elapsed))s]")
            return
        }

        let contentType = httpResp?.value(forHTTPHeaderField: "Content-Type") ?? ""
        log("<- \(method) id=\(rid) \(status) \(data.count)B \(contentType.prefix(30)) [\(String(format: "%.3f", elapsed))s]")

        if contentType.contains("text/event-stream") {
            for frame in extractSSEData(data) {
                if !frame.isEmpty { writeFrame(frame) }
            }
        } else {
            writeFrame(data)
        }
    }
    task.resume()
    sem.wait()
}

// MARK: - Startup health check

func waitForServer(url: URL, maxWait: TimeInterval = 30) -> Bool {
    let ping = Data(#"{"jsonrpc":"2.0","id":"ping","method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1"}}}"#.utf8)
    let deadline = Date().addingTimeInterval(maxWait)
    var attempt = 0
    while Date() < deadline {
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.httpBody = ping
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("application/json, text/event-stream", forHTTPHeaderField: "Accept")
        req.timeoutInterval = 2
        let sem = DispatchSemaphore(value: 0)
        var ok = false
        let task = URLSession.shared.dataTask(with: req) { _, resp, _ in
            if let http = resp as? HTTPURLResponse, http.statusCode > 0 {
                ok = true
                if let sid = http.value(forHTTPHeaderField: "Mcp-Session-Id") {
                    setSessionID(sid)
                }
            }
            sem.signal()
        }
        task.resume()
        sem.wait()
        if ok { return true }
        attempt += 1
        if attempt == 5 { log("server not up yet at \(url.absoluteString), waiting...") }
        Thread.sleep(forTimeInterval: 0.5)
    }
    return false
}

// MARK: - Main

let config = parseArgs()

if let logPath = config.logFile {
    setupLogFile(logPath)
}

log("starting pid=\(ProcessInfo.processInfo.processIdentifier)")

guard let endpointURL = URL(string: config.url) else {
    log("invalid URL: \(config.url)"); exit(1)
}

guard waitForServer(url: endpointURL) else {
    log("no server answering at \(config.url) after 30s"); exit(1)
}

log("bridging stdio -> \(config.url)")

let sessionConfig = URLSessionConfiguration.default
sessionConfig.httpMaximumConnectionsPerHost = config.maxConcurrent
let urlSession = URLSession(configuration: sessionConfig)

let workerQueue = DispatchQueue(label: "bridge.workers", attributes: .concurrent)
let concurrencyCap = DispatchSemaphore(value: config.maxConcurrent)
let inflightGroup = DispatchGroup()

var buffer = Data()
while true {
    let chunk = FileHandle.standardInput.availableData
    if chunk.isEmpty {
        log("stdin EOF")
        break
    }
    buffer.append(chunk)

    while let nlIndex = buffer.firstIndex(of: 0x0A) {
        let lineData = buffer[buffer.startIndex..<nlIndex]
        buffer.removeSubrange(buffer.startIndex...nlIndex)
        if lineData.isEmpty { continue }
        if lineData.count > maxLineBytes {
            log("frame exceeds \(maxLineBytes) bytes, dropped"); continue
        }
        guard let line = String(data: lineData, encoding: .utf8) else { continue }

        concurrencyCap.wait()
        inflightGroup.enter()
        workerQueue.async {
            forwardFrame(url: endpointURL, timeout: config.timeout,
                         line: line, session: urlSession)
            concurrencyCap.signal()
            inflightGroup.leave()
        }
    }
}

if !buffer.isEmpty, buffer.count <= maxLineBytes,
   let line = String(data: buffer, encoding: .utf8), !line.isEmpty {
    forwardFrame(url: endpointURL, timeout: config.timeout,
                 line: line, session: urlSession)
}

inflightGroup.wait()
log("exiting")
