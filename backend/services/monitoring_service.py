import psutil


def sample_processes(processes):
    cpu = 0.0
    memory = 0
    live = []
    for process in processes:
        try:
            if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                cpu += process.cpu_percent(None)
                memory += process.memory_info().rss
                live.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # Match Task Manager's whole-machine percentage (all logical cores).
    return round(cpu / (psutil.cpu_count() or 1), 2), round(memory / 1024 / 1024, 2), live
