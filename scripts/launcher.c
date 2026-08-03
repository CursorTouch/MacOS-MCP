/*
 * Launcher for MacOS-MCP.app.
 *
 * The bundle exists to give macOS one named identity to attribute privacy
 * grants to, instead of the bare `uv` / `python3` rows users see today.
 *
 * It has to be a compiled binary rather than a shell script. A script's
 * running process is /bin/bash, and a script that exec's is replaced by its
 * target entirely -- either way the process macOS sees is not this bundle, and
 * the identity is lost. So this forks, leaves the child to become the
 * interpreter, and stays alive as the signed parent.
 *
 * stdin/stdout are inherited untouched, because MCP speaks JSON-RPC over
 * stdio: anything written to stdout that is not a protocol message corrupts
 * the stream.
 */

#include <errno.h>
#include <libgen.h>
#include <mach-o/dyld.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static pid_t child_pid = 0;

/* Forward termination to the interpreter so the server shuts down cleanly
 * rather than being orphaned when the host quits. */
static void forward_signal(int sig) {
    if (child_pid > 0) kill(child_pid, sig);
}

int main(int argc, char *argv[]) {
    char exec_path[4096];
    uint32_t size = sizeof(exec_path);
    if (_NSGetExecutablePath(exec_path, &size) != 0) {
        fprintf(stderr, "macos-mcp: cannot resolve own path\n");
        return 1;
    }

    /* .../Contents/MacOS/macos-mcp -> .../Contents/Resources/payload */
    char payload[4096];
    char *macos_dir = dirname(exec_path);
    char contents[4096];
    snprintf(contents, sizeof(contents), "%s", dirname(macos_dir));
    snprintf(payload, sizeof(payload), "%s/Resources/payload", contents);

    signal(SIGTERM, forward_signal);
    signal(SIGINT, forward_signal);
    signal(SIGHUP, forward_signal);

    child_pid = fork();
    if (child_pid < 0) {
        fprintf(stderr, "macos-mcp: fork failed: %s\n", strerror(errno));
        return 1;
    }

    if (child_pid == 0) {
        setenv("MACOS_MCP_BUNDLED", "1", 1);

        /* argv: uv --directory <payload> run macos-mcp [args...] */
        char **args = calloc(argc + 7, sizeof(char *));
        int i = 0;
        args[i++] = "uv";
        args[i++] = "--directory";
        args[i++] = payload;
        args[i++] = "run";
        args[i++] = "macos-mcp";
        for (int a = 1; a < argc; a++) args[i++] = argv[a];
        args[i] = NULL;

        execvp("uv", args);
        fprintf(stderr, "macos-mcp: could not start uv: %s\n", strerror(errno));
        _exit(127);
    }

    int status = 0;
    while (waitpid(child_pid, &status, 0) < 0 && errno == EINTR) continue;
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
    return WEXITSTATUS(status);
}
