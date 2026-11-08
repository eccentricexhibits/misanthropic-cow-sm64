// Test-only LD_PRELOAD shim: lets a program that uses IPv6 UDP sockets run in a
// container without IPv6 by opening IPv4 sockets and translating addresses.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

static void to4(const struct sockaddr *a, struct sockaddr_in *o) {
    const struct sockaddr_in6 *s = (const struct sockaddr_in6 *)a;
    memset(o, 0, sizeof *o); o->sin_family = AF_INET; o->sin_port = s->sin6_port;
    if (IN6_IS_ADDR_V4MAPPED(&s->sin6_addr)) memcpy(&o->sin_addr, &s->sin6_addr.s6_addr[12], 4);
    else if (IN6_IS_ADDR_LOOPBACK(&s->sin6_addr)) o->sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    else o->sin_addr.s_addr = htonl(INADDR_ANY);
}
static void to6(const struct sockaddr_in *i, struct sockaddr *a, socklen_t *len) {
    struct sockaddr_in6 o; memset(&o, 0, sizeof o); o.sin6_family = AF_INET6; o.sin6_port = i->sin_port;
    o.sin6_addr.s6_addr[10] = 0xff; o.sin6_addr.s6_addr[11] = 0xff; memcpy(&o.sin6_addr.s6_addr[12], &i->sin_addr, 4);
    if (len && *len >= sizeof o) { memcpy(a, &o, sizeof o); *len = sizeof o; }
}
int socket(int d, int t, int p) {
    static int (*r)(int, int, int); if (!r) r = dlsym(RTLD_NEXT, "socket");
    return r(d == AF_INET6 ? AF_INET : d, t, p);
}
int setsockopt(int fd, int lvl, int opt, const void *v, socklen_t l) {
    static int (*r)(int, int, int, const void *, socklen_t); if (!r) r = dlsym(RTLD_NEXT, "setsockopt");
    if (lvl == IPPROTO_IPV6) return 0;
    return r(fd, lvl, opt, v, l);
}
int bind(int fd, const struct sockaddr *a, socklen_t l) {
    static int (*r)(int, const struct sockaddr *, socklen_t); if (!r) r = dlsym(RTLD_NEXT, "bind");
    if (a && a->sa_family == AF_INET6) { struct sockaddr_in o; to4(a, &o); return r(fd, (struct sockaddr *)&o, sizeof o); }
    return r(fd, a, l);
}
ssize_t sendto(int fd, const void *b, size_t n, int f, const struct sockaddr *a, socklen_t l) {
    static ssize_t (*r)(int, const void *, size_t, int, const struct sockaddr *, socklen_t); if (!r) r = dlsym(RTLD_NEXT, "sendto");
    if (a && a->sa_family == AF_INET6) { struct sockaddr_in o; to4(a, &o); return r(fd, b, n, f, (struct sockaddr *)&o, sizeof o); }
    return r(fd, b, n, f, a, l);
}
ssize_t recvfrom(int fd, void *b, size_t n, int f, struct sockaddr *a, socklen_t *l) {
    static ssize_t (*r)(int, void *, size_t, int, struct sockaddr *, socklen_t *); if (!r) r = dlsym(RTLD_NEXT, "recvfrom");
    struct sockaddr_in i; socklen_t il = sizeof i;
    ssize_t k = r(fd, b, n, f, (struct sockaddr *)&i, &il);
    if (k >= 0 && a && l && il == sizeof i && i.sin_family == AF_INET) to6(&i, a, l);
    return k;
}
