/* Does CLONE_INTO_CGROUP relax the permission rule, or share it?
 *
 * §5.7.4 concluded from a single failed migration that "the sandbox must be placed in its
 * cgroup at creation, not confined after the fact". That conclusion assumes placement at
 * creation is permitted where migration is not. clone3(CLONE_INTO_CGROUP) is the mechanism
 * that would do it, and this is the smallest program that finds out whether it helps.
 *
 * Deliberately in C: there is no clone3 in Python's standard library, and raw-cloning a
 * running interpreter to find out would test the interpreter as much as the kernel.
 *
 * Build: cc -O2 -Wall -o clone_into_cgroup clone_into_cgroup.c
 * Run:   ./clone_into_cgroup /sys/fs/cgroup/.../some-cgroup
 * Prints one line: OK <cgroup the child actually landed in>, or FAIL <stage> <errno>
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef CLONE_INTO_CGROUP
#define CLONE_INTO_CGROUP 0x200000000ULL
#endif
#ifndef SYS_clone3
#define SYS_clone3 435
#endif

/* struct clone_args as of kernel 5.7; only the first eleven fields are used here. */
struct clone_args_v2 {
    uint64_t flags, pidfd, child_tid, parent_tid, exit_signal, stack, stack_size, tls,
        set_tid, set_tid_size, cgroup;
};

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <cgroup-directory>\n", argv[0]);
        return 2;
    }

    int fd = open(argv[1], O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) {
        printf("FAIL open %s\n", strerror(errno));
        return 1;
    }

    struct clone_args_v2 args;
    memset(&args, 0, sizeof args);
    args.flags = CLONE_INTO_CGROUP;
    args.exit_signal = SIGCHLD;
    args.cgroup = (uint64_t)fd;

    long pid = syscall(SYS_clone3, &args, sizeof args);
    if (pid < 0) {
        /* The interesting failure. EACCES/EPERM here means placement at creation is
         * governed by the same rule as migration, which is what §5.7.4 assumed it was not. */
        printf("FAIL clone3 %s\n", strerror(errno));
        return 1;
    }
    if (pid == 0) {
        /* Child: live long enough for the parent to read /proc/<pid>/cgroup, then leave
         * without touching any libc state that the clone did not duplicate cleanly. */
        struct timespec ts = {0, 300 * 1000 * 1000};
        nanosleep(&ts, NULL);
        _exit(0);
    }

    char path[64], buf[256];
    snprintf(path, sizeof path, "/proc/%ld/cgroup", pid);
    int cf = open(path, O_RDONLY | O_CLOEXEC);
    ssize_t n = cf < 0 ? -1 : read(cf, buf, sizeof buf - 1);
    if (n > 0) {
        buf[n] = '\0';
        for (char *p = buf; *p; p++)
            if (*p == '\n') *p = '\0';
        printf("OK %s\n", strncmp(buf, "0::", 3) == 0 ? buf + 3 : buf);
    } else {
        printf("OK <child cgroup unreadable>\n");
    }
    if (cf >= 0) close(cf);
    waitpid((pid_t)pid, NULL, 0);
    return 0;
}
