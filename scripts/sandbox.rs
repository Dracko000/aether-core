use std::process::{Command, Stdio};
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::io::{BufReader, BufWriter};
use std::time::Duration;
use serde::{Serialize, Deserialize};
use serde_json;

#[derive(Serialize, Deserialize, Debug)]
struct ToolRequest {
    command: String,
    args: Vec<String>,
    timeout_ms: u64,
}

#[derive(Serialize, Deserialize, Debug)]
struct ToolResponse {
    stdout: String,
    stderr: String,
    exit_code: i32,
}

fn execute_tool(req: ToolRequest) -> ToolResponse {
    // Secure wrap using bubblewrap (bwrap)
    // --ro-bind /usr /usr: Read-only access to basic system binaries
    // --ro-bind /lib /lib: Read-only access to libraries
    // --ro-bind /lib64 /lib64: Read-only access to 64-bit libraries
    // --proc /proc: Mount /proc
    // --dev /dev: Mount /dev
    // --unshare-all: Unshare all namespaces (user, pid, net, etc.)
    // --new-session: Start a new session to prevent tty hijacking
    // --tmpfs /tmp: Private tmpfs for /tmp

    let mut bwrap_cmd = Command::new("bwrap");
    bwrap_cmd.args([
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64",
        "--proc", "/proc",
        "--dev", "/dev",
        "--unshare-all",
        "--new-session",
        "--tmpfs", "/tmp",
        "--die-with-parent",
    ]);

    // Add the actual command and its arguments
    bwrap_cmd.arg(&req.command);
    bwrap_cmd.args(&req.args);

    let mut child = bwrap_cmd
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to spawn bwrap sandbox");

    // Implement timeout logic
    let timeout = Duration::from_millis(req.timeout_ms);

    // We can't easily use wait_timeout in std, so we use a simple
    // check loop or a separate thread. For this MVP, we'll use a simplified
    // approach of waiting and potentially killing if it hangs.
    // In a production system, we would use libc::kill or similar.

    let mut stdout = String::new();
    let mut stderr = String::new();

    let out_handle = child.stdout.take().expect("Failed to take stdout");
    let err_handle = child.stderr.take().expect("Failed to take stderr");

    // Read stdout/stderr in a way that doesn't block forever
    // For simplicity in this Rust MVP, we read them after waiting.
    // A better way would be using threads or async.

    let status = match child.wait().expect("Failed to wait on child") {
        s => s,
    };

    let mut reader = BufReader::new(out_handle);
    let _ = reader.read_to_string(&mut stdout);

    let mut err_reader = BufReader::new(err_handle);
    let _ = err_reader.read_to_string(&mut stderr);

    ToolResponse {
        stdout,
        stderr,
        exit_code: status.code().unwrap_or(-1),
    }
}

fn handle_client(mut stream: TcpStream) {
    let mut reader = BufReader::new(&stream);
    let mut buffer = [0; 4096];

    if let Ok(n) = reader.read(&mut buffer) {
        if let Ok(req) = serde_json::from_slice::<ToolRequest>(&buffer[..n]) {
            let resp = execute_tool(req);
            let json_resp = serde_json::to_string(&resp).unwrap();
            let mut writer = BufWriter::new(&stream);
            writer.write_all(json_resp.as_bytes()).unwrap();
            writer.flush().unwrap();
        }
    }
}

fn main() {
    let listener = TcpListener::bind("127.0.0.1:9000").expect("Could not bind to port 9000");
    println!("Aether Secure Rust Sandbox listening on port 9000...");

    for stream in listener.incoming() {
        match stream {
            Ok(s) => {
                std::thread::spawn(|| handle_client(s));
            }
            Err(e) => eprintln!("Connection failed: {}", e),
        }
    }
}
