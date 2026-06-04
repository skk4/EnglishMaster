"""macOS system metrics collector (CPU / memory / disk / network) via psutil.

Metrics are registered as Prometheus Gauges and updated on every /metrics scrape.
No background thread — values are collected lazily when Prometheus scrapes.
"""
import os

import psutil
from prometheus_client import Gauge

# ── CPU ─────────────────────────────────────────────────────────────

cpu_percent = Gauge(
    "system_cpu_percent",
    "CPU usage percentage (0-100)",
    ["cpu"],
)

cpu_freq_mhz = Gauge(
    "system_cpu_freq_mhz",
    "CPU frequency in MHz",
    ["cpu"],
)

# ── Memory ──────────────────────────────────────────────────────────

memory_bytes = Gauge(
    "system_memory_bytes",
    "Memory in bytes",
    ["type"],  # total, available, used, free
)

memory_percent = Gauge(
    "system_memory_percent",
    "Memory usage percentage (0-100)",
)

# ── Disk ────────────────────────────────────────────────────────────

disk_bytes = Gauge(
    "system_disk_bytes",
    "Disk space in bytes",
    ["mountpoint", "type"],  # total, used, free
)

disk_percent = Gauge(
    "system_disk_percent",
    "Disk usage percentage (0-100)",
    ["mountpoint"],
)

# ── Network ─────────────────────────────────────────────────────────

net_bytes_total = Gauge(
    "system_net_bytes_total",
    "Network bytes transferred (cumulative, since boot)",
    ["iface", "direction"],  # sent, recv
)

net_packets_total = Gauge(
    "system_net_packets_total",
    "Network packets transferred (cumulative, since boot)",
    ["iface", "direction"],
)

# ── System ──────────────────────────────────────────────────────────

load_average = Gauge(
    "system_load_average",
    "System load average",
    ["period"],  # 1m, 5m, 15m
)

boot_time_seconds = Gauge(
    "system_boot_time_seconds",
    "Unix timestamp of last boot",
)

# ── Process (EnglishMaster backend itself) ──────────────────────────

process_open_fds = Gauge(
    "process_open_fds",
    "Number of open file descriptors by the backend process",
)

process_threads = Gauge(
    "process_threads",
    "Number of threads in the backend process",
)

process_memory_rss = Gauge(
    "process_memory_rss_bytes",
    "Resident set size (RSS) of the backend process in bytes",
)

process_cpu_percent = Gauge(
    "process_cpu_percent",
    "CPU usage of the backend process (0-100 × core_count)",
)


def collect() -> None:
    """Gather current system metrics and update all Gauges. Called on each scrape."""
    try:
        _collect_cpu()
        _collect_memory()
        _collect_disk()
        _collect_network()
        _collect_load()
        _collect_process()
    except Exception:
        pass  # never let metrics collection break the /metrics endpoint


def _collect_cpu() -> None:
    # Per-core usage
    for i, pct in enumerate(psutil.cpu_percent(percpu=True)):
        cpu_percent.labels(cpu=str(i)).set(pct)
    # Overall (average)
    cpu_percent.labels(cpu="total").set(psutil.cpu_percent())

    # Frequency
    freq = psutil.cpu_freq()
    if freq:
        for i, f in enumerate([freq.current, freq.min, freq.max]):
            cpu_freq_mhz.labels(cpu=["current", "min", "max"][i]).set(f if f else 0)


def _collect_memory() -> None:
    mem = psutil.virtual_memory()
    memory_bytes.labels(type="total").set(mem.total)
    memory_bytes.labels(type="available").set(mem.available)
    memory_bytes.labels(type="used").set(mem.used)
    memory_bytes.labels(type="free").set(mem.free)
    memory_percent.set(mem.percent)


def _collect_disk() -> None:
    for part in psutil.disk_partitions():
        if "rw" not in part.opts and "read" not in part.opts.split(",")[0]:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        mp = part.mountpoint
        disk_bytes.labels(mountpoint=mp, type="total").set(usage.total)
        disk_bytes.labels(mountpoint=mp, type="used").set(usage.used)
        disk_bytes.labels(mountpoint=mp, type="free").set(usage.free)
        disk_percent.labels(mountpoint=mp).set(usage.percent)


def _collect_network() -> None:
    counters = psutil.net_io_counters(pernic=True)
    if not counters:
        return
    for iface, stats in counters.items():
        # Only report interfaces with actual traffic
        if stats.bytes_sent == 0 and stats.bytes_recv == 0:
            continue
        net_bytes_total.labels(iface=iface, direction="sent").set(stats.bytes_sent)
        net_bytes_total.labels(iface=iface, direction="recv").set(stats.bytes_recv)
        net_packets_total.labels(iface=iface, direction="sent").set(stats.packets_sent)
        net_packets_total.labels(iface=iface, direction="recv").set(stats.packets_recv)


def _collect_load() -> None:
    if hasattr(os, "getloadavg"):
        la = os.getloadavg()
        load_average.labels(period="1m").set(la[0])
        load_average.labels(period="5m").set(la[1])
        load_average.labels(period="15m").set(la[2])

    boot_time_seconds.set(psutil.boot_time())


def _collect_process() -> None:
    p = psutil.Process()
    try:
        process_open_fds.set(p.num_fds())
    except (psutil.AccessDenied, AttributeError):
        pass
    process_threads.set(p.num_threads())
    process_memory_rss.set(p.memory_info().rss if p.memory_info() else 0)
    process_cpu_percent.set(p.cpu_percent())
